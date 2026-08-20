"""Formatting compatibility harness — deploy diagnostic reports with isolated formatting properties.

Deploys a minimal report with representative visuals and tests one formatting
capability at a time by capturing headless screenshots.
"""

import json
import base64
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.critic.screenshot import capture_report_page


@dataclass
class CapabilityTest:
    """A single formatting capability test."""
    id: str
    visual_family: str  # card, chart, table, slicer, page
    mechanism: str  # pbir_objects, theme_json, tmdl_format
    property_path: str  # e.g. "labels.fontSize"
    value: Any
    description: str
    status: str = "unknown"  # safe, safe_with_constraints, ineffective, unsafe
    notes: str = ""
    screenshot_path: Optional[str] = None


@dataclass
class CompatibilityHarness:
    """Harness for testing PBIR formatting capabilities."""
    workspace_id: str
    workspace_name: str
    semantic_model_id: str
    report_id: Optional[str] = None
    _headers: dict = field(default_factory=dict, repr=False)

    @classmethod
    def create(cls) -> "CompatibilityHarness":
        config = load_config()
        workspace_id = config["workspace_id"]
        workspace_name = config.get("workspace_name", "pbi")
        credential = get_credential(config)
        token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Find or use existing BareMinimal semantic model
        r = requests.get(
            f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=SemanticModel",
            headers=headers, timeout=30,
        )
        sm_id = None
        for item in r.json().get("value", []):
            if item["displayName"] == "BareMinimal":
                sm_id = item["id"]
                break

        if not sm_id:
            raise RuntimeError("BareMinimal semantic model not found. Deploy it first.")

        harness = cls(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            semantic_model_id=sm_id,
        )
        harness._headers = headers
        return harness

    def deploy_diagnostic(
        self,
        name: str,
        visuals: list[dict],
        *,
        theme: Optional[dict] = None,
        page_objects: Optional[dict] = None,
    ) -> str:
        """Deploy a diagnostic report with specific visuals and formatting.

        Args:
            name: Report display name.
            visuals: List of visual.json dicts.
            theme: Optional custom theme.json content.
            page_objects: Optional page-level objects.

        Returns:
            Report ID.
        """
        page_name = "diag01"
        parts = []

        # .platform
        platform = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": name},
            "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
        }
        parts.append(self._part(".platform", platform))

        # definition.pbir
        pbir = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {
                "byConnection": {
                    "connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{self.workspace_name};initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={self.semantic_model_id}"
                }
            },
        }
        parts.append(self._part("definition.pbir", pbir))

        # version.json
        parts.append(self._part("definition/version.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        }))

        # report.json
        report = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
            "themeCollection": {
                "baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"},
            },
            "layoutOptimization": "None",
            "resourcePackages": [
                {"name": "SharedResources", "type": "SharedResources", "items": [
                    {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
                ]},
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "defaultFilterActionIsDataFilter": True,
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "allowInlineExploration": True,
                "useEnhancedTooltips": True,
            },
        }
        if theme:
            report["themeCollection"]["customTheme"] = {
                "name": "DiagTheme.json",
                "reportVersionAtImport": "5.61",
                "type": "RegisteredResources",
            }
            report["resourcePackages"].append({
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": [{"name": "DiagTheme.json", "type": "CustomTheme", "path": "DiagTheme.json"}],
            })
            parts.append(self._part("StaticResources/RegisteredResources/DiagTheme.json", theme))

        parts.append(self._part("definition/report.json", report))

        # pages.json
        parts.append(self._part("definition/pages/pages.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [page_name],
            "activePageName": page_name,
        }))

        # page.json
        page = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
            "name": page_name,
            "displayName": "Diagnostic",
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        }
        if page_objects:
            page["objects"] = page_objects
        parts.append(self._part(f"definition/pages/{page_name}/page.json", page))

        # Visuals
        for v in visuals:
            v_name = v["name"]
            parts.append(self._part(
                f"definition/pages/{page_name}/visuals/{v_name}/visual.json", v
            ))

        # Deploy
        # Check if exists
        existing_id = None
        r = requests.get(
            f"{FABRIC_API_BASE}/workspaces/{self.workspace_id}/items?type=Report",
            headers=self._headers, timeout=30,
        )
        for item in r.json().get("value", []):
            if item["displayName"] == name:
                existing_id = item["id"]
                break

        if existing_id:
            url = f"{FABRIC_API_BASE}/workspaces/{self.workspace_id}/items/{existing_id}/updateDefinition"
            r = requests.post(url, headers=self._headers, json={"definition": {"parts": parts}}, timeout=60)
        else:
            url = f"{FABRIC_API_BASE}/workspaces/{self.workspace_id}/items"
            r = requests.post(url, headers=self._headers, json={
                "displayName": name, "type": "Report", "definition": {"parts": parts}
            }, timeout=60)

        if r.status_code == 202:
            op_id = r.headers.get("x-ms-operation-id", "")
            location = r.headers.get("Location", "")
            self._wait_op(op_id, location)
        elif r.status_code not in (200, 201):
            raise RuntimeError(f"Deploy failed: {r.status_code} {r.text[:300]}")

        # Get report ID
        if existing_id:
            self.report_id = existing_id
        else:
            r = requests.get(
                f"{FABRIC_API_BASE}/workspaces/{self.workspace_id}/items?type=Report",
                headers=self._headers, timeout=30,
            )
            for item in r.json().get("value", []):
                if item["displayName"] == name:
                    self.report_id = item["id"]
                    break

        return self.report_id or ""

    def capture(self, output_path: Path, page_name: str = "Diagnostic") -> bool:
        """Capture a screenshot of the diagnostic report."""
        if not self.report_id:
            return False
        result = capture_report_page(
            self.report_id, page_name, output_path,
            workspace_id=self.workspace_id,
        )
        return result.outcome.value == "success"

    def _part(self, path: str, obj: dict) -> dict:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        return {"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"}

    def _wait_op(self, op_id: str, location: str, timeout: int = 60):
        url = location or f"{FABRIC_API_BASE}/operations/{op_id}"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(3)
            r = requests.get(url, headers=self._headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "Succeeded":
                    return
                if data.get("status") == "Failed":
                    raise RuntimeError(f"Operation failed: {data.get('error', {})}")


def make_card_visual(name: str = "card1", title: str = "Total", objects: Optional[dict] = None) -> dict:
    """Create a card visual definition for testing."""
    v = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": name,
        "position": {"x": 32, "y": 32, "z": 1000, "height": 200, "width": 300, "tabOrder": 1000},
        "visual": {
            "visualType": "card",
            "query": {
                "queryState": {
                    "Values": {"projections": [{
                        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                        "queryRef": "Fact.Total",
                        "active": True,
                    }]}
                }
            },
            "objects": objects or {},
            "drillFilterOtherVisuals": True,
        },
    }
    return v


def make_bar_visual(name: str = "bar1", title: str = "By Category", objects: Optional[dict] = None) -> dict:
    """Create a bar chart visual for testing."""
    v = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": name,
        "position": {"x": 360, "y": 32, "z": 1001, "height": 300, "width": 400, "tabOrder": 1001},
        "visual": {
            "visualType": "clusteredBarChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [{
                        "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "ID"}},
                        "queryRef": "Fact.ID",
                        "active": True,
                    }]},
                    "Y": {"projections": [{
                        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                        "queryRef": "Fact.Total",
                    }]},
                }
            },
            "objects": objects or {},
            "drillFilterOtherVisuals": True,
        },
    }
    return v


def _lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def _str_lit(s: str) -> dict:
    return _lit(f"'{s}'")


def _num_lit(n) -> dict:
    return _lit(f"{n}D")


def _bool_lit(b: bool) -> dict:
    return _lit("true" if b else "false")


def _color_lit(hex_color: str) -> dict:
    return {"solid": {"color": _lit(f"'{hex_color}'")}}
