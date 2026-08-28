"""Reusable create-or-update report deployment service (Stage 12B).

Replaces the legacy delete-then-create pattern with persistent report identity:

    if a report with the logical name exists -> update its definition in place
    else                                     -> create it

The normal update path preserves report ID, URL, workspace and semantic-model
binding, and never deletes by default. All report generation should call this
rather than embedding delete/create logic in per-dashboard scripts.

Live Fabric calls are injected via a ``session`` object (defaults to
``requests``) and a ``fabric_api_base`` so the decision logic is unit-testable
with a mocked session — no live workspace required for logic tests.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import requests as _requests


FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
PBI_API_BASE = "https://api.powerbi.com/v1.0/myorg"


class DeploymentAction(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"


class DeploymentError(Exception):
    """Raised when a deployment cannot be completed."""


@dataclass
class DeploymentResult:
    """Explicit outcome of a create-or-update deployment."""

    report_id: str
    report_url: str
    action: DeploymentAction
    previous_report_id: Optional[str] = None
    definition_hash: str = ""
    elapsed_seconds: float = 0.0
    render_verified: bool = False
    page_names: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors and bool(self.report_id)

    @property
    def id_preserved(self) -> bool:
        """True when an update kept the same report ID as before."""
        return (
            self.action == DeploymentAction.UPDATED
            and self.previous_report_id is not None
            and self.previous_report_id == self.report_id
        )


def definition_hash(parts: list[dict]) -> str:
    """Deterministic hash of a PBIR parts list (path + payload)."""
    h = hashlib.sha256()
    for p in sorted(parts, key=lambda x: x["path"]):
        h.update(p["path"].encode("utf-8"))
        h.update(b"\0")
        h.update(p.get("payload", "").encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


class DeploymentService:
    """Create-or-update deployment against the Fabric REST API.

    Parameters
    ----------
    workspace_id: target workspace.
    headers: auth headers (Authorization bearer + Content-Type).
    session: HTTP session (defaults to the ``requests`` module) — inject a mock
             for unit tests.
    fabric_api_base / pbi_api_base: overridable API roots.
    """

    def __init__(
        self,
        workspace_id: str,
        headers: dict,
        *,
        session: Any = None,
        fabric_api_base: str = FABRIC_API_BASE,
        pbi_api_base: str = PBI_API_BASE,
        poll_interval: float = 2.0,
        poll_attempts: int = 30,
    ) -> None:
        self.workspace_id = workspace_id
        self.headers = headers
        self.session = session or _requests
        self.fabric_api_base = fabric_api_base.rstrip("/")
        self.pbi_api_base = pbi_api_base.rstrip("/")
        self.poll_interval = poll_interval
        self.poll_attempts = poll_attempts

    # ── stable logical lookup ────────────────────────────────────────────────

    def find_report_id(self, logical_name: str) -> Optional[str]:
        """Deterministic logical-name -> report ID lookup.

        Returns the report ID whose displayName matches ``logical_name``
        (case-insensitive). If duplicates exist, the lexicographically smallest
        ID is chosen so the result is deterministic.
        """
        r = self.session.get(
            f"{self.fabric_api_base}/workspaces/{self.workspace_id}/items?type=Report",
            headers=self.headers, timeout=30,
        )
        matches: list[str] = []
        if r.status_code == 200:
            for item in r.json().get("value", []):
                if item.get("displayName", "").lower() == logical_name.lower():
                    matches.append(item["id"])
        if not matches:
            return None
        return sorted(matches)[0]

    def get_report_url(self, report_id: str) -> str:
        """Stable viewer/web URL for a report (webUrl, fallback to a
        canonical group/reports URL)."""
        r = self.session.get(
            f"{self.pbi_api_base}/groups/{self.workspace_id}/reports/{report_id}",
            headers=self.headers, timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("webUrl") or (
                f"{self.pbi_api_base}/groups/{self.workspace_id}/reports/{report_id}"
            )
        return f"{self.pbi_api_base}/groups/{self.workspace_id}/reports/{report_id}"

    # ── long-running operation polling ────────────────────────────────────────

    def _wait(self, response) -> None:
        if response.status_code not in (201, 202):
            return
        location = response.headers.get("Location", "")
        if not location:
            return
        for _ in range(self.poll_attempts):
            time.sleep(self.poll_interval)
            poll = self.session.get(location, headers=self.headers, timeout=30)
            if poll.status_code != 200:
                continue
            status = poll.json().get("status", "")
            if status == "Succeeded":
                return
            if status == "Failed":
                err = poll.json().get("error", {})
                raise DeploymentError(
                    f"Operation failed: {err.get('message', str(err))[:400]}"
                )
        raise DeploymentError("Operation timed out")

    # ── core create-or-update ─────────────────────────────────────────────────

    def deploy(
        self,
        logical_name: str,
        parts: list[dict],
        *,
        page_names: Optional[list[str]] = None,
    ) -> DeploymentResult:
        """Create the report if absent, else update its definition in place.

        Never deletes. Preserves report ID/URL on the update path.
        """
        start = time.time()
        def_hash = definition_hash(parts)
        existing_id = self.find_report_id(logical_name)

        if existing_id:
            # ── UPDATE in place (preserves ID + URL) ──
            url = (
                f"{self.fabric_api_base}/workspaces/{self.workspace_id}"
                f"/items/{existing_id}/updateDefinition"
            )
            r = self.session.post(
                url, headers=self.headers,
                json={"definition": {"parts": parts}}, timeout=90,
            )
            if r.status_code not in (200, 201, 202):
                raise DeploymentError(
                    f"updateDefinition failed: {r.status_code} {getattr(r, 'text', '')[:300]}"
                )
            self._wait(r)
            report_id = existing_id
            action = DeploymentAction.UPDATED
            previous_id = existing_id
        else:
            # ── CREATE new ──
            url = f"{self.fabric_api_base}/workspaces/{self.workspace_id}/items"
            r = self.session.post(
                url, headers=self.headers,
                json={
                    "displayName": logical_name,
                    "type": "Report",
                    "definition": {"parts": parts},
                },
                timeout=90,
            )
            if r.status_code not in (200, 201, 202):
                raise DeploymentError(
                    f"create failed: {r.status_code} {getattr(r, 'text', '')[:300]}"
                )
            self._wait(r)
            report_id = ""
            if r.status_code == 201:
                try:
                    report_id = r.json().get("id", "") or ""
                except Exception:
                    report_id = ""
            if not report_id:
                report_id = self.find_report_id(logical_name) or ""
            if not report_id:
                raise DeploymentError("Report not found after creation")
            action = DeploymentAction.CREATED
            previous_id = None

        report_url = self.get_report_url(report_id)
        return DeploymentResult(
            report_id=report_id,
            report_url=report_url,
            action=action,
            previous_report_id=previous_id,
            definition_hash=def_hash,
            elapsed_seconds=round(time.time() - start, 2),
            render_verified=False,
            page_names=page_names or [],
        )
