"""Conversational design session + design spec + approval gate (Stage 13).

`DashboardDesignSession` holds the full back-and-forth state and supports
incremental amendment (a revision preserves prior decisions unless changed).
On explicit approval it freezes the current revision and produces a structured
`DashboardDesignSpec` that the Power BI build handoff consumes.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .data_context import DataContext
from .feasibility import (
    CustomVisualRequirement,
    ImplementationClass,
    VisualClassification,
    build_custom_visual_requirement,
    classify_visual,
)
from .mockup_service import MockupRevision


# ─────────────────────────────────────────────────────────────────────────────
# Proposed visual (design-time element, pre-build)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ProposedVisual:
    """A visual in the evolving design, with its feasibility classification."""

    intent: str
    visual: str                      # mockup visual family, e.g. "line chart"
    title: str = ""
    region: str = "body"             # kpi_row | hero | companion | bottom | body
    classification: Optional[VisualClassification] = None
    user_forced_deviation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "visual": self.visual,
            "title": self.title,
            "region": self.region,
            "classification": self.classification.to_dict() if self.classification else None,
            "user_forced_deviation": self.user_forced_deviation,
        }


class ApprovalState(str, Enum):
    DESIGNING = "DESIGNING"
    APPROVED = "APPROVED"
    BUILT = "BUILT"


_APPROVAL_PATTERNS = [
    r"\bapproved?\b", r"\bbuild it\b", r"\bcreate the power ?bi\b",
    r"\bgo ahead\b", r"\bship it\b", r"\bmake it real\b", r"\blet'?s build\b",
    r"\bdeploy( it)?\b",
]


def is_approval_intent(message: str) -> bool:
    m = message.lower()
    return any(re.search(p, m) for p in _APPROVAL_PATTERNS)


# ─────────────────────────────────────────────────────────────────────────────
# Design spec (approved, structured, buildable)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DashboardDesignSpec:
    """Structured approved design. The renderer consumes this, not the image."""

    spec_id: str
    page_title: str
    page_subtitle: str
    audience: str
    resolution: tuple[int, int]
    navigation: list[str]                       # nav labels
    slicers: list[str]                          # filter field names
    kpis: list[str]                             # KPI metric intents
    visuals: list[ProposedVisual]
    palette: dict[str, str]
    typography: str
    assumptions: list[str]
    feasibility_gaps: list[str]                 # NEEDS_REDESIGN summaries
    custom_visual_requirements: list[CustomVisualRequirement]
    mockup_revision_id: str
    data_context_id: str

    def implementation_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self.visuals:
            if v.classification:
                k = v.classification.implementation_class.value
                counts[k] = counts.get(k, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "page_title": self.page_title,
            "page_subtitle": self.page_subtitle,
            "audience": self.audience,
            "resolution": list(self.resolution),
            "navigation": self.navigation,
            "slicers": self.slicers,
            "kpis": self.kpis,
            "visuals": [v.to_dict() for v in self.visuals],
            "palette": self.palette,
            "typography": self.typography,
            "assumptions": self.assumptions,
            "feasibility_gaps": self.feasibility_gaps,
            "custom_visual_requirements": [c.to_dict() for c in self.custom_visual_requirements],
            "implementation_summary": self.implementation_summary(),
            "mockup_revision_id": self.mockup_revision_id,
            "data_context_id": self.data_context_id,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Session
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DashboardDesignSession:
    """Full conversational design state; supports incremental amendment."""

    original_request: str
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:10]}")
    audience: str = ""
    conversation: list[dict[str, str]] = field(default_factory=list)  # {role, text}
    data_context: Optional[DataContext] = None
    inferred_kpis: list[str] = field(default_factory=list)
    design_preferences: dict[str, str] = field(default_factory=dict)
    proposed_visuals: list[ProposedVisual] = field(default_factory=list)
    revisions: list[MockupRevision] = field(default_factory=list)
    approval_state: ApprovalState = ApprovalState.DESIGNING
    design_confidence: float = 0.0
    feasibility_confidence: float = 0.0
    custom_visual_requirements: list[CustomVisualRequirement] = field(default_factory=list)
    design_spec: Optional[DashboardDesignSpec] = None
    palette: dict[str, str] = field(default_factory=lambda: {
        "canvas": "#0f1623", "surface": "#151d2e", "accent": "#3898ff",
        "accent2": "#a78bfa", "positive": "#34d399", "negative": "#f87171",
    })

    # ── conversation helpers ─────────────────────────────────────────────────

    @property
    def current_revision(self) -> Optional[MockupRevision]:
        return self.revisions[-1] if self.revisions else None

    def log(self, role: str, text: str) -> None:
        self.conversation.append({"role": role, "text": text})

    def add_revision(self, rev: MockupRevision) -> None:
        self.revisions.append(rev)

    # ── incremental design mutation ──────────────────────────────────────────

    def set_visuals(self, visuals: list[ProposedVisual]) -> None:
        """Set the initial proposed visuals and classify each."""
        for v in visuals:
            v.classification = classify_visual(
                v.intent, v.visual, user_forced_deviation=v.user_forced_deviation
            )
            self._maybe_add_requirement(v)
        self.proposed_visuals = visuals
        self._recompute_confidence()

    def apply_revision_delta(self, delta: "RevisionDelta") -> None:
        """Apply a parsed revision delta, preserving unchanged elements.

        Only the affected elements are re-classified — no full redesign.
        """
        if delta.palette_changes:
            self.palette.update(delta.palette_changes)
        if delta.preference_changes:
            self.design_preferences.update(delta.preference_changes)

        # Change one visual type in place (preserve everything else).
        for change in delta.visual_changes:
            target = self._find_visual(change.get("match_title") or change.get("match_intent"))
            if target is not None:
                if "new_visual" in change:
                    target.visual = change["new_visual"]
                if "new_intent" in change:
                    target.intent = change["new_intent"]
                if change.get("user_forced_deviation"):
                    target.user_forced_deviation = True
                target.classification = classify_visual(
                    target.intent, target.visual,
                    user_forced_deviation=target.user_forced_deviation,
                )
                self._maybe_add_requirement(target)
            elif change.get("user_forced_deviation"):
                # No existing visual matched, but the user asked for a bespoke
                # treatment — never lose that intent: add it as a new visual.
                nv = ProposedVisual(
                    intent=change.get("new_intent", "bespoke"),
                    visual=change.get("new_visual", "bespoke visual"),
                    title=(change.get("match_title") or "Bespoke").title(),
                    region="bottom", user_forced_deviation=True,
                )
                nv.classification = classify_visual(nv.intent, nv.visual, user_forced_deviation=True)
                self._maybe_add_requirement(nv)
                self.proposed_visuals.append(nv)

        # Add new visuals (e.g. "add a regional filter" handled via slicers).
        for add in delta.added_visuals:
            add.classification = classify_visual(
                add.intent, add.visual, user_forced_deviation=add.user_forced_deviation
            )
            self._maybe_add_requirement(add)
            self.proposed_visuals.append(add)

        for slicer in delta.added_slicers:
            self.design_preferences.setdefault("slicers", "")
            existing = [s for s in self.design_preferences["slicers"].split(",") if s]
            if slicer not in existing:
                existing.append(slicer)
            self.design_preferences["slicers"] = ",".join(existing)

        self._recompute_confidence()

    def _find_visual(self, key: Optional[str]) -> Optional[ProposedVisual]:
        if not key:
            return None
        k = key.lower()
        for v in self.proposed_visuals:
            if k in v.title.lower() or k in v.intent.lower() or k in v.visual.lower():
                return v
        return None

    def _maybe_add_requirement(self, v: ProposedVisual) -> None:
        c = v.classification
        if c and c.implementation_class == ImplementationClass.CUSTOM_VISUAL_REQUIRED:
            if c.custom_visual_requirement_id and any(
                r.requirement_id == c.custom_visual_requirement_id
                for r in self.custom_visual_requirements
            ):
                return
            req = build_custom_visual_requirement(
                c, mockup_reference=self.current_revision.revision_id if self.current_revision else "",
            )
            self.custom_visual_requirements.append(req)

    def _recompute_confidence(self) -> None:
        self.design_confidence = self.data_context.confidence if self.data_context else 0.4
        classes = [v.classification.confidence for v in self.proposed_visuals if v.classification]
        self.feasibility_confidence = round(sum(classes) / len(classes), 2) if classes else 0.0

    # ── approval → spec ──────────────────────────────────────────────────────

    def approve_and_build_spec(self, *, page_title: str, page_subtitle: str,
                               navigation: Optional[list[str]] = None) -> DashboardDesignSpec:
        """Freeze the current revision and produce a structured DashboardDesignSpec."""
        self.approval_state = ApprovalState.APPROVED
        slicers = [s for s in self.design_preferences.get("slicers", "").split(",") if s]
        gaps = [
            f"{v.title or v.intent}: {v.classification.rationale}"
            for v in self.proposed_visuals
            if v.classification and v.classification.implementation_class == ImplementationClass.NEEDS_REDESIGN
        ]
        spec = DashboardDesignSpec(
            spec_id=f"spec_{uuid.uuid4().hex[:10]}",
            page_title=page_title,
            page_subtitle=page_subtitle,
            audience=self.audience,
            resolution=(1280, 720),
            navigation=navigation or ["Overview", "Financial", "Customers", "Products"],
            slicers=slicers,
            kpis=list(self.inferred_kpis),
            visuals=list(self.proposed_visuals),
            palette=dict(self.palette),
            typography="Segoe UI",
            assumptions=list(self.data_context.assumptions) if self.data_context else [],
            feasibility_gaps=gaps,
            custom_visual_requirements=list(self.custom_visual_requirements),
            mockup_revision_id=self.current_revision.revision_id if self.current_revision else "",
            data_context_id=self.data_context.context_id if self.data_context else "",
        )
        self.design_spec = spec
        return spec

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "original_request": self.original_request,
            "audience": self.audience,
            "turns": len(self.conversation),
            "data_context": self.data_context.to_dict() if self.data_context else None,
            "inferred_kpis": self.inferred_kpis,
            "design_preferences": self.design_preferences,
            "proposed_visuals": [v.to_dict() for v in self.proposed_visuals],
            "revisions": [r.to_dict() for r in self.revisions],
            "approval_state": self.approval_state.value,
            "design_confidence": self.design_confidence,
            "feasibility_confidence": self.feasibility_confidence,
            "custom_visual_requirements": [c.to_dict() for c in self.custom_visual_requirements],
            "design_spec": self.design_spec.to_dict() if self.design_spec else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Revision delta (parsed change)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RevisionDelta:
    """A parsed, structured description of what a user revision changes."""

    visual_changes: list[dict[str, Any]] = field(default_factory=list)
    added_visuals: list[ProposedVisual] = field(default_factory=list)
    added_slicers: list[str] = field(default_factory=list)
    palette_changes: dict[str, str] = field(default_factory=dict)
    preference_changes: dict[str, str] = field(default_factory=dict)
