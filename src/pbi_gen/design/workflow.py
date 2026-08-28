"""Conversational design workflow orchestrator (Stage 13).

Ties the pieces together into the user journey:
  start_session -> (ingest data) -> propose initial design + mockup
  revise(instruction)   -> incremental amendment + new mockup
  approve(...)          -> DashboardDesignSpec

Inference (KPIs, initial visuals, revision parsing) is deterministic and
grounded in the DataContext + template inventory. An LLM could enrich this, but
a dependency-light heuristic path always works (offline, tested).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .data_context import DataContext, FieldRole
from .feasibility import ImplementationClass
from .mockup_service import DashboardMockupService, MockupRevision
from .session import (
    DashboardDesignSession,
    DashboardDesignSpec,
    ProposedVisual,
    RevisionDelta,
    is_approval_intent,
)

# ── audience inference ────────────────────────────────────────────────────────
_AUDIENCE = [
    (r"\bcfo\b|\bfinance\b|\bp&l\b|\bfinancial\b", "CFO / Finance leadership"),
    (r"\bceo\b|\bexecutive\b|\bboard\b|\bc-suite\b", "CEO / Executive"),
    (r"\bcustomer|\bretention\b|\bchurn\b|\bcrm\b", "Customer / Growth leadership"),
    (r"\bproduct\b|\bcatalogue|\bcatalog\b", "Product leadership"),
    (r"\bsales\b|\bpipeline\b|\brevenue\b", "Sales leadership"),
]


def infer_audience(request: str) -> str:
    m = request.lower()
    for pat, label in _AUDIENCE:
        if re.search(pat, m):
            return label
    return "Executive"


# ── KPI + initial visual inference ────────────────────────────────────────────

def infer_kpis(ctx: Optional[DataContext], request: str) -> list[str]:
    """Pick up to 4 headline KPIs from candidate measures / request keywords."""
    kpis: list[str] = []
    if ctx:
        for m in ctx.candidate_measures:
            kpis.append(m)
            if len(kpis) >= 4:
                break
    if len(kpis) < 4:
        # supplement from common exec KPIs implied by the request
        for kw in ["Revenue", "Gross Margin", "Churn Rate", "Active Customers",
                   "ARR", "MRR", "Retention Rate"]:
            if kw.lower() in request.lower() and kw not in kpis:
                kpis.append(kw)
            if len(kpis) >= 4:
                break
    return kpis[:4]


def propose_initial_visuals(ctx: Optional[DataContext], kpis: list[str]) -> list[ProposedVisual]:
    """Grounded first proposal biased to the existing template library."""
    visuals: list[ProposedVisual] = []

    # KPI row
    for k in kpis:
        visuals.append(ProposedVisual(intent="headline_metric", visual="kpi card",
                                       title=k, region="kpi_row"))

    has_date = bool(ctx and ctx.date_fields)
    first_measure = kpis[0] if kpis else "Revenue"
    first_dim = (ctx.candidate_dimensions[0] if ctx and ctx.candidate_dimensions else "Category")

    # Hero: trend if a date exists, else column comparison
    if has_date:
        visuals.append(ProposedVisual(intent="time_trend", visual="area/line trend",
                                       title=f"{first_measure} Trend", region="hero"))
    else:
        visuals.append(ProposedVisual(intent="categorical_comparison", visual="column chart",
                                       title=f"{first_measure} by {first_dim}", region="hero"))

    # Companion: donut composition
    visuals.append(ProposedVisual(intent="composition_share", visual="donut chart",
                                   title=f"{first_measure} Mix", region="companion"))

    # Bottom row: ranking bar, comparison, insights
    visuals.append(ProposedVisual(intent="ranking", visual="horizontal bar",
                                   title=f"Top {first_dim}", region="bottom"))
    visuals.append(ProposedVisual(intent="categorical_comparison", visual="column chart",
                                   title="Comparison", region="bottom"))
    visuals.append(ProposedVisual(intent="narrative_insight", visual="key insights panel",
                                   title="Key Insights", region="bottom"))
    return visuals


# ── revision parsing (deterministic NL -> RevisionDelta) ──────────────────────

_COLOUR_WORDS = {
    "teal": "#14b8a6", "purple": "#a78bfa", "blue": "#3898ff", "green": "#34d399",
    "red": "#f87171", "orange": "#fb923c", "gold": "#fbbf24", "navy": "#0f1623",
}
_VISUAL_WORDS = {
    "donut": ("composition_share", "donut chart"),
    "pie": ("composition_share", "donut chart"),
    "bar": ("ranking", "horizontal bar"),
    "column": ("categorical_comparison", "column chart"),
    "line": ("time_trend", "area/line trend"),
    "trend": ("time_trend", "area/line trend"),
    "area": ("time_trend", "area/line trend"),
    "table": ("detail_table", "data table"),
    "gauge": ("progress_gauge", "radial gauge"),
    "waterfall": ("bridge_waterfall", "waterfall chart"),
}
_BESPOKE_WORDS = ["bespoke", "custom", "completely different", "radial bar",
                  "variance bridge", "outer target ring", "unique", "sankey",
                  "bullet chart", "calendar heatmap", "waffle"]


def parse_revision(instruction: str) -> RevisionDelta:
    """Parse a plain-English revision into a structured delta (best-effort)."""
    text = instruction.lower()
    delta = RevisionDelta()

    # Colour changes: "use teal instead of purple", "use these colours: teal"
    for word, hexval in _COLOUR_WORDS.items():
        if re.search(rf"\b{word}\b", text) and ("colour" in text or "color" in text
                                                 or "instead" in text or "theme" in text):
            delta.palette_changes["accent"] = hexval
            break

    # Filter/slicer additions: "add a regional filter", "move filters top right"
    m = re.search(r"add (?:a )?(\w+)\s+(?:filter|slicer)", text)
    if m:
        delta.added_slicers.append(m.group(1).title())
    if "filter" in text and ("top right" in text or "top-right" in text or "move" in text):
        delta.preference_changes["filter_position"] = "top-right"

    # Layout preferences
    if "kpi" in text and ("smaller" in text or "same width" in text or "bigger" in text):
        delta.preference_changes["kpi_row"] = (
            "smaller" if "smaller" in text else "same-width" if "same width" in text else "bigger"
        )
    if "executive" in text or "premium" in text or "boardroom" in text:
        delta.preference_changes["tone"] = "more executive"

    # Visual type change / bespoke request:
    # "switch gross margin from bar to donut", "make the margin visual radial ..."
    bespoke = any(b in text for b in _BESPOKE_WORDS) or "look completely different" in text
    # find target by "margin", "revenue", named metric etc.
    target_match = None
    tm = re.search(r"(?:switch|change|make|replace)\s+(?:the\s+)?([a-z ]+?)\s+(?:visual|chart|from|to|with|into)", text)
    if tm:
        target_match = tm.group(1).strip()

    new_visual = None
    for word, (intent, vis) in _VISUAL_WORDS.items():
        if re.search(rf"\bto (?:a )?{word}\b|\binto (?:a )?{word}\b|\buse (?:a )?{word}\b", text):
            new_visual = (intent, vis)
            break

    if bespoke and target_match:
        delta.visual_changes.append({
            "match_title": target_match,
            "match_intent": target_match,
            "new_visual": _bespoke_label(instruction),
            "new_intent": f"bespoke {target_match}",
            "user_forced_deviation": True,
        })
    elif new_visual and target_match:
        delta.visual_changes.append({
            "match_title": target_match, "match_intent": target_match,
            "new_intent": new_visual[0], "new_visual": new_visual[1],
        })
    elif bespoke:
        # bespoke without a clear target -> add a new bespoke visual
        delta.added_visuals.append(ProposedVisual(
            intent="bespoke", visual=_bespoke_label(instruction),
            title="Bespoke Visual", region="bottom", user_forced_deviation=True,
        ))
    else:
        # Generic "add a <thing>" that is neither a known template word nor a
        # tagged bespoke word (e.g. an exotic/infeasible request). Capture it so
        # the feasibility classifier can judge it (NEEDS_REDESIGN / native / etc).
        addm = re.search(r"\badd (?:a |an )?(.+)", text)
        if addm and "filter" not in text and "slicer" not in text:
            desc = addm.group(1).strip()
            delta.added_visuals.append(ProposedVisual(
                intent=desc, visual=desc, title=desc[:40].title(),
                region="bottom", user_forced_deviation=False,
            ))

    return delta


def _bespoke_label(instruction: str) -> str:
    # keep a short descriptive label of the requested bespoke visual
    txt = instruction.strip()
    return (txt[:60] + "…") if len(txt) > 60 else txt


# ── workflow orchestrator ─────────────────────────────────────────────────────


class DesignWorkflow:
    """Orchestrates the conversational image-first design workflow."""

    def __init__(self, mockup_service: Optional[DashboardMockupService] = None):
        self.mockup = mockup_service or DashboardMockupService()

    def start_session(
        self, request: str, *, data_context: Optional[DataContext] = None,
        audience: str = "",
    ) -> DashboardDesignSession:
        session = DashboardDesignSession(original_request=request)
        session.log("user", request)
        session.audience = audience or infer_audience(request)
        session.data_context = data_context
        session.inferred_kpis = infer_kpis(data_context, request)
        session.set_visuals(propose_initial_visuals(data_context, session.inferred_kpis))
        return session

    def needs_clarification(self, session: DashboardDesignSession) -> bool:
        """Below ~50% combined confidence on a design-material decision -> ask."""
        return session.design_confidence < 0.5

    def generate_initial_mockup(self, session: DashboardDesignSession) -> MockupRevision:
        rev = self.mockup.create_mockup(session)
        session.add_revision(rev)
        session.log("system", f"initial mockup {rev.revision_id}")
        return rev

    def revise(self, session: DashboardDesignSession, instruction: str) -> MockupRevision:
        session.log("user", instruction)
        delta = parse_revision(instruction)
        session.apply_revision_delta(delta)
        rev = self.mockup.revise_mockup(session, instruction)
        session.add_revision(rev)
        session.log("system", f"revised mockup {rev.revision_id}: {instruction}")
        return rev

    def handle_message(self, session: DashboardDesignSession, message: str):
        """Route a conversational message: approval vs revision."""
        if is_approval_intent(message):
            session.log("user", message)
            return "APPROVAL"
        return self.revise(session, message)

    def approve(self, session: DashboardDesignSession, *, page_title: str,
                page_subtitle: str = "", navigation: Optional[list[str]] = None) -> DashboardDesignSpec:
        return session.approve_and_build_spec(
            page_title=page_title, page_subtitle=page_subtitle, navigation=navigation,
        )
