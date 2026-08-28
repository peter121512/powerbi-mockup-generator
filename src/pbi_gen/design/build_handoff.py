"""Approved DashboardDesignSpec -> real Power BI report handoff (Stage 13).

Converts an approved `DashboardDesignSpec` into a Stage 12B `ReportSpec` and
deploys it via the persistent `DeploymentService` (create-or-update, stable
report ID/URL). Mapping rules:

- EXISTING_TEMPLATE      -> the mapped reusable template
- NATIVE_POWERBI         -> nearest supported native/template config
- CUSTOM_VISUAL_REQUIRED -> recorded as a build dependency; a closest-template
                            placeholder is used so the report still builds for
                            supported elements (NOT a silent substitution — it is
                            reported as a pending custom-visual dependency)
- NEEDS_REDESIGN         -> surfaced as a gap; omitted from the build

Geometry comes from the standard 1280x720 grid (matching TEMPLATE_INVENTORY).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..renderer.templates.navigation import NAV_TOKENS, default_nav_items
from ..renderer.templates.registry import (
    DesignTokens,
    FieldRef,
    PageShell,
    TemplateRegistry,
    VisualBinding,
)
from ..renderer.templates.report_builder import ReportPage, ReportSpec
from .feasibility import ImplementationClass
from .session import DashboardDesignSpec, ProposedVisual

# Shared demo semantic model (same one the canonical report binds to).
SEMANTIC_MODEL_ID = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
SEMANTIC_MODEL_NAME = "ExecutiveRetailPerformanceDashboard"

# Real measures/dims available on that model (used to bind generated visuals so
# they actually render with data).
_MEASURES = ["TotalRevenue", "GrossProfit", "TotalCost", "GrossMarginPct"]
_CATEGORY = FieldRef(entity="Product", property="CategoryName")
_REGION = FieldRef(entity="Region", property="RegionName")
_YEAR = FieldRef(entity="Date", property="Year")
_MONTH = FieldRef(entity="Date", property="Month")

# intent/class -> concrete template id
_TEMPLATE_FOR_INTENT = {
    "headline_metric": "premium_kpi",
    "time_trend": "premium_trend",
    "categorical_comparison": "premium_column",
    "ranking": "premium_bar",
    "composition_share": "premium_donut",
    "distribution": "premium_column",
    "bridge_waterfall": "premium_waterfall",
    "progress_gauge": "premium_gauge",
    "detail_table": "premium_table",
    "narrative_insight": "premium_insights",
}

# Standard grid regions.
_CX = 155
_CW = 1115
_GUT = 10


@dataclass
class BuildResult:
    report_id: str
    report_url: str
    action: str
    page_name: str
    built_visuals: list[str] = field(default_factory=list)
    pending_custom_visuals: list[str] = field(default_factory=list)
    redesign_gaps: list[str] = field(default_factory=list)
    screenshot_path: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "report_url": self.report_url,
            "action": self.action,
            "page_name": self.page_name,
            "built_visuals": self.built_visuals,
            "pending_custom_visuals": self.pending_custom_visuals,
            "redesign_gaps": self.redesign_gaps,
            "screenshot_path": self.screenshot_path,
            "errors": self.errors,
        }


def _template_for(v: ProposedVisual) -> Optional[str]:
    """Choose a concrete builder template for a proposed visual, honouring its
    implementation class. Returns None to omit (NEEDS_REDESIGN)."""
    c = v.classification
    if c and c.implementation_class == ImplementationClass.NEEDS_REDESIGN:
        return None
    if c and c.implementation_class == ImplementationClass.EXISTING_TEMPLATE and c.candidate_template:
        return c.candidate_template
    if c and c.implementation_class == ImplementationClass.CUSTOM_VISUAL_REQUIRED:
        # Use the closest existing template as a visible placeholder (reported).
        return c.candidate_template or _TEMPLATE_FOR_INTENT.get(_base_intent(v.intent), "premium_column")
    return _TEMPLATE_FOR_INTENT.get(_base_intent(v.intent), "premium_column")


def _base_intent(intent: str) -> str:
    for k in _TEMPLATE_FOR_INTENT:
        if k in intent:
            return k
    return intent


def _bindings_for(template_id: str, title: str, measure_idx: int) -> VisualBinding:
    """Build a data binding for a template against the shared model."""
    measure = FieldRef(entity="Sales", property=_MEASURES[measure_idx % len(_MEASURES)], is_measure=True)
    if template_id == "premium_kpi":
        return VisualBinding(template_id=template_id, title="",
                             data_bindings={"measure": [measure]}, position=(0, 0, 0, 0))
    if template_id == "premium_trend":
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"category": [_YEAR, _MONTH],
                                            "values": [FieldRef(entity="Sales", property="TotalRevenue", is_measure=True),
                                                       FieldRef(entity="Sales", property="GrossProfit", is_measure=True)]},
                             position=(0, 0, 0, 0))
    if template_id == "premium_donut":
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"category": [_REGION], "values": [measure]},
                             position=(0, 0, 0, 0),
                             config_overrides={"center_value": title.split()[0][:6] or "Mix", "center_label": "Total"})
    if template_id == "premium_insights":
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"measure": [measure]}, position=(0, 0, 0, 0))
    if template_id in ("premium_bar", "premium_column"):
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"category": [_CATEGORY], "values": [measure]},
                             position=(0, 0, 0, 0))
    if template_id == "premium_gauge":
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"measure": [measure]}, position=(0, 0, 0, 0))
    if template_id == "premium_waterfall":
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"category": [_REGION], "values": [measure]},
                             position=(0, 0, 0, 0))
    if template_id == "premium_table":
        return VisualBinding(template_id=template_id, title=title,
                             data_bindings={"category": [_CATEGORY], "values": [measure]},
                             position=(0, 0, 0, 0))
    return VisualBinding(template_id="premium_column", title=title,
                         data_bindings={"category": [_CATEGORY], "values": [measure]}, position=(0, 0, 0, 0))


def spec_to_report_spec(spec: DashboardDesignSpec, *, page_name: str = "designed_dashboard") -> tuple[ReportSpec, BuildResult]:
    """Map an approved DashboardDesignSpec to a single-page 12B ReportSpec.

    Also returns a BuildResult skeleton recording built visuals, pending custom
    visuals and redesign gaps (report populated by the caller after deploy).
    """
    built: list[str] = []
    pending: list[str] = []
    gaps: list[str] = []
    bindings: list[VisualBinding] = []

    kpis = [v for v in spec.visuals if _base_intent(v.intent) == "headline_metric"]
    body = [v for v in spec.visuals if _base_intent(v.intent) != "headline_metric"]

    # KPI row (up to 4)
    kpi_w = (_CW - 3 * _GUT) // 4
    for i, v in enumerate(kpis[:4]):
        b = _bindings_for("premium_kpi", v.title, i)
        b.position = (_CX + i * (kpi_w + _GUT), 90, kpi_w, 75)
        bindings.append(b)
        built.append(f"KPI:{v.title}")
        _track(v, pending, gaps)

    # Hero row: first non-kpi wide + companion
    y_hero = 175
    if body:
        hero = body[0]
        tid = _template_for(hero)
        if tid:
            b = _bindings_for(tid, hero.title, 0)
            b.position = (_CX, y_hero, 635, 240)
            bindings.append(b)
            built.append(f"{tid}:{hero.title}")
        _track(hero, pending, gaps)
    if len(body) > 1:
        comp = body[1]
        tid = _template_for(comp)
        if tid:
            b = _bindings_for(tid, comp.title, 1)
            b.position = (_CX + 635 + _GUT, y_hero, 470, 240)
            bindings.append(b)
            built.append(f"{tid}:{comp.title}")
        _track(comp, pending, gaps)

    # Bottom row: up to 3
    y_bot = 425
    col_w = (_CW - 2 * _GUT) // 3
    for i, v in enumerate(body[2:5]):
        tid = _template_for(v)
        if tid:
            b = _bindings_for(tid, v.title, i + 2)
            b.position = (_CX + i * (col_w + _GUT), y_bot, col_w, 240)
            bindings.append(b)
            built.append(f"{tid}:{v.title}")
        _track(v, pending, gaps)

    shell = PageShell(
        page_name=page_name,
        display_name=spec.page_title,
        title=spec.page_title,
        subtitle=spec.page_subtitle or spec.audience,
        nav_items=[(n, n.lower().replace(" ", "_")) for n in spec.navigation],
        active_nav=page_name,
        slicers=[_YEAR] + ([_CATEGORY] if spec.slicers else []),
        width=1280, height=720,
    )
    from .feasibility import ImplementationClass as _IC  # local import to avoid cycle noise
    from ..renderer.templates.navigation import NavItem

    # Nav for a standalone designed dashboard: a single functional entry that
    # targets this page (deterministic target = page_name).
    nav_items = [NavItem("Overview", page_name, "overview")]

    report_spec = ReportSpec(
        report_name=spec.page_title.replace(" ", "") or "DesignedDashboard",
        semantic_model_id=SEMANTIC_MODEL_ID,
        semantic_model_name=SEMANTIC_MODEL_NAME,
        pages=[ReportPage(shell=shell, bindings=bindings)],
        default_page=page_name,
        nav_items=nav_items,
        tokens=DesignTokens(),
        nav_tokens=NAV_TOKENS,
    )
    result = BuildResult(
        report_id="", report_url="", action="", page_name=page_name,
        built_visuals=built, pending_custom_visuals=pending, redesign_gaps=gaps,
    )
    # Ensure EVERY approved visual's feasibility is reflected in the result, even
    # if it wasn't placed on the standard grid (e.g. extra bespoke/redesign items).
    for v in spec.visuals:
        _track(v, pending, gaps)
    # Also fold in explicit custom-visual requirements + spec gaps.
    for cvr in spec.custom_visual_requirements:
        entry = f"{cvr.intent} (req {cvr.requirement_id})"
        if not any(cvr.requirement_id in p for p in pending):
            pending.append(entry + ": pending custom visual")
    for g in spec.feasibility_gaps:
        if g not in gaps:
            gaps.append(g)
    return report_spec, result


def _track(v: ProposedVisual, pending: list[str], gaps: list[str]) -> None:
    c = v.classification
    if not c:
        return
    if c.implementation_class == ImplementationClass.CUSTOM_VISUAL_REQUIRED:
        entry = (f"{v.title or v.intent} (req {c.custom_visual_requirement_id}): "
                 f"placeholder used pending custom visual")
        if entry not in pending:
            pending.append(entry)
    elif c.implementation_class == ImplementationClass.NEEDS_REDESIGN:
        entry = f"{v.title or v.intent}: {c.rationale}"
        if entry not in gaps:
            gaps.append(entry)
