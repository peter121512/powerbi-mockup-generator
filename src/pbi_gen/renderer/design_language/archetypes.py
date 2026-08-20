"""Page archetypes and composition region system.

Maps PageRole to structured page archetypes that define composition regions,
density, and visual placement rules for enterprise Power BI dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pbi_gen.models.dashboard_spec import (
    FilterSpec,
    PageRole,
    PageSpec,
    VisualSpec,
    VisualType,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CompositionRegion:
    """A named rectangular region within a page archetype.

    Coordinates are expressed as percentages (0.0–1.0) of the canvas
    dimensions, enabling resolution-independent layout.
    """

    name: str  # 'header', 'filter_bar', 'kpi_band', 'hero', 'primary', 'secondary', 'detail', 'footer'
    y_start_pct: float  # 0.0-1.0 of canvas height
    y_end_pct: float
    x_start_pct: float  # 0.0-1.0 of canvas width
    x_end_pct: float
    role: str  # what this region is for
    max_visuals: int  # max visuals in this region
    priority_boost: float  # extra sizing for high-priority visuals


@dataclass
class PageArchetype:
    """A complete page composition template driven by functional role.

    Defines named regions, density characteristics, and layout parameters
    that together prescribe how visuals should be arranged on a page.
    """

    name: str
    regions: list[CompositionRegion] = field(default_factory=list)
    density: str = "medium"  # 'low', 'medium', 'high'
    hero_visual_count: int = 0  # how many visuals get hero treatment
    kpi_max: int = 0  # max KPIs in the KPI band
    outer_margin_pct: float = 2.5  # margin as % of canvas
    section_gap_px: int = 12  # gap between regions


@dataclass
class VisualPlacement:
    """Concrete pixel-level placement for a visual within a region."""

    visual_id: str
    region_name: str
    x: float  # pixel position
    y: float
    width: float
    height: float
    is_hero: bool = False
    is_kpi: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Archetype definitions
# ─────────────────────────────────────────────────────────────────────────────


def _build_executive_overview() -> PageArchetype:
    """Low density, spacious — designed for senior stakeholders."""
    return PageArchetype(
        name="executive_overview",
        density="low",
        hero_visual_count=1,
        kpi_max=4,
        outer_margin_pct=3.5,
        section_gap_px=16,
        regions=[
            CompositionRegion(
                name="header",
                y_start_pct=0.0,
                y_end_pct=0.08,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Page identity and title",
                max_visuals=0,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="filter_bar",
                y_start_pct=0.08,
                y_end_pct=0.15,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Compact slicers",
                max_visuals=4,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="kpi_band",
                y_start_pct=0.15,
                y_end_pct=0.30,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Strong KPI callout cards",
                max_visuals=4,
                priority_boost=0.2,
            ),
            CompositionRegion(
                name="hero",
                y_start_pct=0.30,
                y_end_pct=0.65,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Single dominant visual",
                max_visuals=1,
                priority_boost=0.4,
            ),
            CompositionRegion(
                name="secondary",
                y_start_pct=0.65,
                y_end_pct=0.95,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Supporting visuals",
                max_visuals=3,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="footer",
                y_start_pct=0.95,
                y_end_pct=1.0,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Navigation and context",
                max_visuals=0,
                priority_boost=0.0,
            ),
        ],
    )


def _build_diagnostic_analysis() -> PageArchetype:
    """Medium density — balanced for analytical exploration."""
    return PageArchetype(
        name="diagnostic_analysis",
        density="medium",
        hero_visual_count=0,
        kpi_max=3,
        outer_margin_pct=2.5,
        section_gap_px=12,
        regions=[
            CompositionRegion(
                name="header",
                y_start_pct=0.0,
                y_end_pct=0.06,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Page identity and title",
                max_visuals=0,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="filter_bar",
                y_start_pct=0.06,
                y_end_pct=0.12,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Compact slicers",
                max_visuals=4,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="kpi_band",
                y_start_pct=0.12,
                y_end_pct=0.24,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Contextual KPI indicators",
                max_visuals=3,
                priority_boost=0.1,
            ),
            CompositionRegion(
                name="primary",
                y_start_pct=0.24,
                y_end_pct=0.64,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Primary analytical visuals (side by side)",
                max_visuals=2,
                priority_boost=0.2,
            ),
            CompositionRegion(
                name="secondary",
                y_start_pct=0.64,
                y_end_pct=0.94,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Supporting visuals",
                max_visuals=3,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="detail",
                y_start_pct=0.80,
                y_end_pct=1.0,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Tables and detail grids",
                max_visuals=2,
                priority_boost=0.0,
            ),
        ],
    )


def _build_comparison_analysis() -> PageArchetype:
    """Medium density — optimised for side-by-side comparison."""
    return PageArchetype(
        name="comparison_analysis",
        density="medium",
        hero_visual_count=0,
        kpi_max=0,
        outer_margin_pct=2.5,
        section_gap_px=12,
        regions=[
            CompositionRegion(
                name="header",
                y_start_pct=0.0,
                y_end_pct=0.06,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Page identity and title",
                max_visuals=0,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="filter_bar",
                y_start_pct=0.06,
                y_end_pct=0.12,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Compact slicers",
                max_visuals=4,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="primary",
                y_start_pct=0.12,
                y_end_pct=0.56,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Side-by-side comparison charts",
                max_visuals=2,
                priority_boost=0.2,
            ),
            CompositionRegion(
                name="secondary",
                y_start_pct=0.56,
                y_end_pct=0.94,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Supporting detail",
                max_visuals=3,
                priority_boost=0.0,
            ),
        ],
    )


def _build_risk_detail() -> PageArchetype:
    """Medium-high density — detailed view with tables."""
    return PageArchetype(
        name="risk_detail",
        density="high",
        hero_visual_count=0,
        kpi_max=4,
        outer_margin_pct=2.0,
        section_gap_px=10,
        regions=[
            CompositionRegion(
                name="header",
                y_start_pct=0.0,
                y_end_pct=0.06,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Page identity and title",
                max_visuals=0,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="filter_bar",
                y_start_pct=0.06,
                y_end_pct=0.12,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Compact slicers",
                max_visuals=4,
                priority_boost=0.0,
            ),
            CompositionRegion(
                name="kpi_band",
                y_start_pct=0.12,
                y_end_pct=0.22,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Risk summary KPIs",
                max_visuals=4,
                priority_boost=0.1,
            ),
            CompositionRegion(
                name="primary",
                y_start_pct=0.22,
                y_end_pct=0.57,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Main risk visualization",
                max_visuals=2,
                priority_boost=0.2,
            ),
            CompositionRegion(
                name="detail",
                y_start_pct=0.57,
                y_end_pct=0.94,
                x_start_pct=0.0,
                x_end_pct=1.0,
                role="Risk table and detail grids",
                max_visuals=2,
                priority_boost=0.0,
            ),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Archetype registry
# ─────────────────────────────────────────────────────────────────────────────

_ARCHETYPES: dict[str, PageArchetype] = {
    "executive_overview": _build_executive_overview(),
    "diagnostic_analysis": _build_diagnostic_analysis(),
    "comparison_analysis": _build_comparison_analysis(),
    "risk_detail": _build_risk_detail(),
}

# Map PageRole enum values to archetype keys
_ROLE_TO_ARCHETYPE: dict[PageRole, str] = {
    PageRole.EXECUTIVE_OVERVIEW: "executive_overview",
    PageRole.DIAGNOSTIC: "diagnostic_analysis",
    PageRole.DETAIL: "risk_detail",
    PageRole.DRILL_THROUGH: "risk_detail",
    PageRole.TOOLTIP: "executive_overview",
    PageRole.NAVIGATION: "executive_overview",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

_KPI_TYPES: set[VisualType] = {VisualType.CARD, VisualType.MULTI_ROW_CARD, VisualType.KPI}
_TABLE_TYPES: set[VisualType] = {VisualType.TABLE, VisualType.MATRIX}


def select_archetype(page: PageSpec) -> PageArchetype:
    """Select the appropriate archetype based on page role and content.

    Uses the page role as the primary selector, then considers visual
    types and counts to refine the choice where appropriate.
    """
    archetype_key = _ROLE_TO_ARCHETYPE.get(page.role, "diagnostic_analysis")

    # Content-based adjustments: if a diagnostic page is dominated by tables,
    # switch to the detail-oriented archetype for better table accommodation.
    if page.role == PageRole.DIAGNOSTIC:
        table_count = sum(
            1 for v in page.visuals if v.visual_type in _TABLE_TYPES
        )
        total = len(page.visuals)
        if total > 0 and table_count / total > 0.5:
            archetype_key = "risk_detail"

    # If a detail page has very few visuals, use a spacious layout
    if page.role == PageRole.DETAIL and len(page.visuals) <= 3:
        archetype_key = "executive_overview"

    return _ARCHETYPES[archetype_key]


def assign_visuals_to_regions(
    visuals: list[VisualSpec],
    filters: list[FilterSpec],
    archetype: PageArchetype,
    canvas_width: int = 1280,
    canvas_height: int = 720,
) -> dict[str, list[VisualPlacement]]:
    """Assign visuals to archetype regions based on type and priority.

    Assignment logic:
    - Cards/KPIs go to kpi_band (up to archetype.kpi_max)
    - Highest-priority non-KPI visual goes to hero region (if archetype has one)
    - Tables go to detail region if available
    - Remaining visuals distributed to primary/secondary by priority
    - Filters go to filter_bar

    Within a region, visuals are arranged in a grid:
    - KPI band: equal-width cards in a row
    - Hero: full region width
    - Primary/secondary: split width equally among assigned visuals
    """
    region_map: dict[str, CompositionRegion] = {r.name: r for r in archetype.regions}
    placements: dict[str, list[VisualPlacement]] = {r.name: [] for r in archetype.regions}

    margin_px_x = canvas_width * (archetype.outer_margin_pct / 100.0)
    margin_px_y = canvas_height * (archetype.outer_margin_pct / 100.0)

    # Categorise visuals
    kpi_visuals: list[VisualSpec] = []
    table_visuals: list[VisualSpec] = []
    chart_visuals: list[VisualSpec] = []

    for v in visuals:
        if v.visual_type in _KPI_TYPES:
            kpi_visuals.append(v)
        elif v.visual_type in _TABLE_TYPES:
            table_visuals.append(v)
        else:
            chart_visuals.append(v)

    # Sort charts by priority (1=highest priority value)
    chart_visuals.sort(key=lambda v: v.priority)

    # --- KPI band ---
    if "kpi_band" in region_map:
        region = region_map["kpi_band"]
        assigned_kpis = kpi_visuals[: archetype.kpi_max]
        _place_in_row(
            assigned_kpis, region, placements, canvas_width, canvas_height,
            margin_px_x, margin_px_y, is_kpi=True,
        )
        # Overflow KPIs become charts
        chart_visuals = kpi_visuals[archetype.kpi_max :] + chart_visuals
    else:
        # No KPI band — treat KPIs as normal visuals
        chart_visuals = kpi_visuals + chart_visuals
        chart_visuals.sort(key=lambda v: v.priority)

    # --- Hero region ---
    hero_assigned: list[VisualSpec] = []
    if "hero" in region_map and archetype.hero_visual_count > 0 and chart_visuals:
        region = region_map["hero"]
        hero_assigned = chart_visuals[: archetype.hero_visual_count]
        chart_visuals = chart_visuals[archetype.hero_visual_count :]
        _place_in_row(
            hero_assigned, region, placements, canvas_width, canvas_height,
            margin_px_x, margin_px_y, is_hero=True,
        )

    # --- Detail region (tables) ---
    if "detail" in region_map and table_visuals:
        region = region_map["detail"]
        assigned_tables = table_visuals[: region.max_visuals]
        _place_in_row(
            assigned_tables, region, placements, canvas_width, canvas_height,
            margin_px_x, margin_px_y,
        )
        table_visuals = table_visuals[region.max_visuals :]
        # Overflow tables go to secondary
        chart_visuals = chart_visuals + table_visuals
    elif table_visuals:
        # No detail region — tables become normal visuals
        chart_visuals = chart_visuals + table_visuals

    # --- Primary region ---
    if "primary" in region_map and chart_visuals:
        region = region_map["primary"]
        assigned = chart_visuals[: region.max_visuals]
        chart_visuals = chart_visuals[region.max_visuals :]
        _place_in_row(
            assigned, region, placements, canvas_width, canvas_height,
            margin_px_x, margin_px_y,
        )

    # --- Secondary region ---
    if "secondary" in region_map and chart_visuals:
        region = region_map["secondary"]
        assigned = chart_visuals[: region.max_visuals]
        chart_visuals = chart_visuals[region.max_visuals :]
        _place_in_row(
            assigned, region, placements, canvas_width, canvas_height,
            margin_px_x, margin_px_y,
        )

    # --- Filter bar ---
    if "filter_bar" in region_map and filters:
        region = region_map["filter_bar"]
        _place_filters_in_row(
            filters, region, placements, canvas_width, canvas_height,
            margin_px_x, margin_px_y,
        )

    return placements


# ─────────────────────────────────────────────────────────────────────────────
# Internal placement helpers
# ─────────────────────────────────────────────────────────────────────────────


def _place_in_row(
    visuals: list[VisualSpec],
    region: CompositionRegion,
    placements: dict[str, list[VisualPlacement]],
    canvas_width: int,
    canvas_height: int,
    margin_px_x: float,
    margin_px_y: float,
    *,
    is_hero: bool = False,
    is_kpi: bool = False,
) -> None:
    """Place visuals in an equal-width row within a region."""
    if not visuals:
        return

    # Compute usable region bounds in pixels
    region_x = region.x_start_pct * canvas_width + margin_px_x
    region_y = region.y_start_pct * canvas_height + margin_px_y
    region_w = (region.x_end_pct - region.x_start_pct) * canvas_width - 2 * margin_px_x
    region_h = (region.y_end_pct - region.y_start_pct) * canvas_height

    count = len(visuals)
    gap = 8.0 if count > 1 else 0.0
    total_gap = gap * (count - 1)
    cell_width = (region_w - total_gap) / count
    cell_height = region_h

    for i, visual in enumerate(visuals):
        x = region_x + i * (cell_width + gap)
        placements[region.name].append(
            VisualPlacement(
                visual_id=visual.id,
                region_name=region.name,
                x=round(x, 1),
                y=round(region_y, 1),
                width=round(cell_width, 1),
                height=round(cell_height, 1),
                is_hero=is_hero,
                is_kpi=is_kpi,
            )
        )


def _place_filters_in_row(
    filters: list[FilterSpec],
    region: CompositionRegion,
    placements: dict[str, list[VisualPlacement]],
    canvas_width: int,
    canvas_height: int,
    margin_px_x: float,
    margin_px_y: float,
) -> None:
    """Place filter slicers in an equal-width row within the filter bar."""
    if not filters:
        return

    region_x = region.x_start_pct * canvas_width + margin_px_x
    region_y = region.y_start_pct * canvas_height + margin_px_y
    region_w = (region.x_end_pct - region.x_start_pct) * canvas_width - 2 * margin_px_x
    region_h = (region.y_end_pct - region.y_start_pct) * canvas_height

    # Limit to max_visuals
    placed_filters = filters[: region.max_visuals]
    count = len(placed_filters)
    gap = 8.0 if count > 1 else 0.0
    total_gap = gap * (count - 1)
    cell_width = (region_w - total_gap) / count
    cell_height = region_h

    for i, filt in enumerate(placed_filters):
        x = region_x + i * (cell_width + gap)
        placements[region.name].append(
            VisualPlacement(
                visual_id=filt.id,
                region_name=region.name,
                x=round(x, 1),
                y=round(region_y, 1),
                width=round(cell_width, 1),
                height=round(cell_height, 1),
                is_hero=False,
                is_kpi=False,
            )
        )
