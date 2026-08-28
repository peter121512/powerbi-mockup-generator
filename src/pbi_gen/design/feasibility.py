"""Power BI feasibility classification + custom-visual requirement handoff (Stage 13).

Every proposed visual is classified against what the project can realistically
build, grounded in `docs/TEMPLATE_INVENTORY.md`:

- EXISTING_TEMPLATE     — reproducible with a current project template
- NATIVE_POWERBI        — achievable with native Power BI config (no template yet)
- CUSTOM_VISUAL_REQUIRED— Power BI-realistic but needs a new/enhanced custom visual
- NEEDS_REDESIGN        — not credibly reproducible in Power BI as specified

Feasibility confidence is tracked separately from data/design confidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ImplementationClass(str, Enum):
    EXISTING_TEMPLATE = "EXISTING_TEMPLATE"
    NATIVE_POWERBI = "NATIVE_POWERBI"
    CUSTOM_VISUAL_REQUIRED = "CUSTOM_VISUAL_REQUIRED"
    NEEDS_REDESIGN = "NEEDS_REDESIGN"


# ── Existing project templates (from docs/TEMPLATE_INVENTORY.md) ──────────────
EXISTING_TEMPLATES: dict[str, dict[str, Any]] = {
    "premium_kpi": {"intents": ["headline_metric", "kpi"], "families": ["kpi", "card"]},
    "premium_trend": {"intents": ["time_trend", "trend"], "families": ["line", "area", "trend"]},
    "premium_bar": {"intents": ["ranking", "categorical_comparison"], "families": ["bar"]},
    "premium_column": {"intents": ["distribution", "categorical_comparison", "time_trend"], "families": ["column"]},
    "premium_donut": {"intents": ["composition_share"], "families": ["donut", "pie"]},
    "premium_table": {"intents": ["detail_table"], "families": ["table", "matrix"]},
    "premium_waterfall": {"intents": ["bridge_waterfall"], "families": ["waterfall", "bridge"]},
    "premium_gauge": {"intents": ["progress_gauge"], "families": ["gauge", "radial"]},
    "premium_insights": {"intents": ["narrative_insight"], "families": ["insights", "narrative"]},
    "donut_center_kpi": {"intents": ["center_overlay"], "families": ["overlay"]},
}

# Native PBI visual families that exist without a project template yet.
NATIVE_FAMILIES = {
    "scatter", "bubble", "map", "filledmap", "matrix", "treemap", "funnel",
    "ribbon", "areastacked", "stackedbar", "stackedcolumn", "linecolumn",
    "kpi", "slicer", "card", "multirow",
}

# Design/behaviour signals that Power BI cannot credibly reproduce as specified.
_INFEASIBLE_SIGNALS = [
    "3d", "three-dimensional", "rotating", "spinning", "video", "animated flythrough",
    "particle", "real-time physics", "free-form animation", "morphing",
    "hand-drawn animation", "live camera", "augmented reality", "virtual reality",
    "parallax scroll", "infinite canvas", "voice control", "gesture control",
]

# Signals that a request is a bespoke visual treatment beyond current templates.
_BESPOKE_SIGNALS = [
    "bespoke", "custom", "unique", "completely different", "radial bar",
    "variance bridge", "embedded target", "outer target ring", "sparkline grid",
    "hexbin", "sankey", "chord", "network", "custom hover", "bullet chart",
    "waffle", "calendar heatmap", "arc diagram", "beeswarm",
]


@dataclass
class VisualClassification:
    """Feasibility classification for one proposed visual/element."""

    intent: str
    mockup_visual: str
    implementation_class: ImplementationClass
    candidate_template: Optional[str] = None
    confidence: float = 0.0
    custom_visual_requirement_id: Optional[str] = None
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "mockup_visual": self.mockup_visual,
            "implementation_class": self.implementation_class.value,
            "candidate_template": self.candidate_template,
            "confidence": self.confidence,
            "custom_visual_requirement_id": self.custom_visual_requirement_id,
            "rationale": self.rationale,
        }


@dataclass
class CustomVisualRequirement:
    """Structured handoff for a design deviation needing a new/enhanced visual.

    Preserves enough for a later custom-visual stage to build it without
    reinterpreting the user's design from scratch.
    """

    requirement_id: str
    intent: str
    mockup_visual: str
    data_roles: list[str] = field(default_factory=list)
    interactions: list[str] = field(default_factory=list)
    formatting_controls: list[str] = field(default_factory=list)
    responsive_behaviour: str = ""
    accessibility: str = ""
    tooltip_selection_filter: str = ""
    visual_states: list[str] = field(default_factory=list)
    approx_geometry: Optional[tuple[int, int, int, int]] = None
    design_tokens: dict[str, str] = field(default_factory=dict)
    closest_existing_template: Optional[str] = None
    reason_templates_insufficient: str = ""
    mockup_reference: str = ""  # crop/revision reference

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "intent": self.intent,
            "mockup_visual": self.mockup_visual,
            "data_roles": self.data_roles,
            "interactions": self.interactions,
            "formatting_controls": self.formatting_controls,
            "responsive_behaviour": self.responsive_behaviour,
            "accessibility": self.accessibility,
            "tooltip_selection_filter": self.tooltip_selection_filter,
            "visual_states": self.visual_states,
            "approx_geometry": list(self.approx_geometry) if self.approx_geometry else None,
            "design_tokens": self.design_tokens,
            "closest_existing_template": self.closest_existing_template,
            "reason_templates_insufficient": self.reason_templates_insufficient,
            "mockup_reference": self.mockup_reference,
        }


def _match_existing_template(intent: str, visual: str) -> Optional[str]:
    key = f"{intent} {visual}".lower()
    for tid, meta in EXISTING_TEMPLATES.items():
        if intent in meta["intents"]:
            return tid
        if any(fam in key for fam in meta["families"]):
            return tid
    return None


def _closest_template(visual: str) -> Optional[str]:
    v = visual.lower()
    for tid, meta in EXISTING_TEMPLATES.items():
        if any(fam in v for fam in meta["families"]):
            return tid
    return None


def classify_visual(
    intent: str,
    mockup_visual: str,
    *,
    user_forced_deviation: bool = False,
) -> VisualClassification:
    """Classify a single visual's Power BI implementation feasibility.

    `user_forced_deviation` = the user explicitly asked for something beyond the
    standard library; this must NOT be silently downgraded to a template.
    """
    text = f"{intent} {mockup_visual}".lower()

    # 1) Genuinely infeasible behaviours.
    if any(sig in text for sig in _INFEASIBLE_SIGNALS):
        return VisualClassification(
            intent=intent, mockup_visual=mockup_visual,
            implementation_class=ImplementationClass.NEEDS_REDESIGN,
            confidence=0.9,
            rationale="Requested behaviour/appearance cannot be credibly reproduced "
                      "in Power BI as specified; needs redesign or a realistic equivalent.",
        )

    bespoke = user_forced_deviation or any(sig in text for sig in _BESPOKE_SIGNALS)

    # 2) Existing template fit (only if not an explicit bespoke deviation).
    if not bespoke:
        tid = _match_existing_template(intent, mockup_visual)
        if tid:
            return VisualClassification(
                intent=intent, mockup_visual=mockup_visual,
                implementation_class=ImplementationClass.EXISTING_TEMPLATE,
                candidate_template=tid, confidence=0.95,
                rationale=f"Reproducible with existing template '{tid}'.",
            )

    # 3) Native Power BI capability (no template yet).
    if not bespoke and any(fam in text for fam in NATIVE_FAMILIES):
        return VisualClassification(
            intent=intent, mockup_visual=mockup_visual,
            implementation_class=ImplementationClass.NATIVE_POWERBI,
            confidence=0.8,
            rationale="Achievable with native Power BI configuration; no project template yet.",
        )

    # 4) Bespoke / deviation → custom visual requirement.
    if bespoke:
        return VisualClassification(
            intent=intent, mockup_visual=mockup_visual,
            implementation_class=ImplementationClass.CUSTOM_VISUAL_REQUIRED,
            candidate_template=_closest_template(mockup_visual),
            confidence=0.85,
            rationale="User-requested bespoke treatment beyond the current template "
                      "library; Power BI-realistic but needs a new/enhanced custom visual.",
        )

    # 5) Fallback: unknown but likely native.
    return VisualClassification(
        intent=intent, mockup_visual=mockup_visual,
        implementation_class=ImplementationClass.NATIVE_POWERBI,
        confidence=0.55,
        rationale="No exact template match; assumed achievable via native Power BI "
                  "configuration pending confirmation.",
    )


def build_custom_visual_requirement(
    classification: VisualClassification,
    *,
    data_roles: Optional[list[str]] = None,
    interactions: Optional[list[str]] = None,
    formatting_controls: Optional[list[str]] = None,
    approx_geometry: Optional[tuple[int, int, int, int]] = None,
    design_tokens: Optional[dict[str, str]] = None,
    mockup_reference: str = "",
) -> CustomVisualRequirement:
    """Produce a structured CustomVisualRequirement from a classification."""
    rid = f"cvr_{uuid.uuid4().hex[:8]}"
    classification.custom_visual_requirement_id = rid
    return CustomVisualRequirement(
        requirement_id=rid,
        intent=classification.intent,
        mockup_visual=classification.mockup_visual,
        data_roles=data_roles or ["category", "measure"],
        interactions=interactions or ["cross-filter", "tooltip"],
        formatting_controls=formatting_controls or ["colours", "title", "data labels"],
        responsive_behaviour="Scale to container; maintain readable labels at supported sizes.",
        accessibility="Sufficient contrast; keyboard focus; screen-reader labels.",
        tooltip_selection_filter="Standard tooltip on hover; participates in cross-filter/selection.",
        visual_states=["default", "hover", "selected", "no-data"],
        approx_geometry=approx_geometry,
        design_tokens=design_tokens or {},
        closest_existing_template=classification.candidate_template,
        reason_templates_insufficient=classification.rationale,
        mockup_reference=mockup_reference,
    )
