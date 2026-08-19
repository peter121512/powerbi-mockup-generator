"""Visual type mapping and query builder for PBIR visuals.

Maps DashboardSpec VisualType enum values to Power BI visualType strings,
and builds the query/field binding structures for each visual.
"""

from __future__ import annotations

from pbi_gen.models import FieldRef, MeasureSpec, VisualSpec, VisualType
from pbi_gen.renderer.result import VisualFidelity


# ─────────────────────────────────────────────────────────────────────────────
# Visual Type Mapping
# ─────────────────────────────────────────────────────────────────────────────

VISUAL_TYPE_MAP: dict[str, str] = {
    VisualType.CARD.value: "card",
    VisualType.LINE_CHART.value: "lineChart",
    VisualType.BAR_CHART.value: "barChart",
    VisualType.CLUSTERED_BAR.value: "clusteredBarChart",
    VisualType.CLUSTERED_COLUMN.value: "clusteredColumnChart",
    VisualType.STACKED_BAR.value: "stackedBarChart",
    VisualType.STACKED_COLUMN.value: "stackedColumnChart",
    VisualType.TABLE.value: "tableEx",
    VisualType.MATRIX.value: "pivotTable",
    VisualType.DONUT_CHART.value: "donutChart",
    VisualType.PIE_CHART.value: "pieChart",
    VisualType.SLICER.value: "slicer",
    VisualType.MAP.value: "map",
    VisualType.FILLED_MAP.value: "filledMap",
    VisualType.SCATTER.value: "scatterChart",
    VisualType.TREEMAP.value: "treemap",
    VisualType.FUNNEL.value: "funnel",
    VisualType.WATERFALL.value: "waterfallChart",
    VisualType.COMBO_CHART.value: "lineClusteredColumnComboChart",
    VisualType.AREA_CHART.value: "areaChart",
    VisualType.KPI.value: "card",
    VisualType.GAUGE.value: "gauge",
    VisualType.TEXT_BOX.value: "textbox",
    VisualType.BUTTON.value: "actionButton",
    VisualType.MULTI_ROW_CARD.value: "multiRowCard",
    VisualType.RIBBON.value: "ribbonChart",
    VisualType.COLUMN_CHART.value: "clusteredColumnChart",
    VisualType.DECOMPOSITION_TREE.value: "decompositionTreeVisual",
    VisualType.KEY_INFLUENCERS.value: "keyInfluencers",
    VisualType.SHAPE_MAP.value: "shapeMap",
    VisualType.IMAGE.value: "image",
}

# Fallback type for unrecognized visuals.
FALLBACK_VISUAL_TYPE = "card"


def map_visual_type(visual: VisualSpec) -> tuple[str, bool, str]:
    """Map a VisualSpec to its Power BI visual type string.

    Returns:
        Tuple of (pbi_visual_type, is_fallback, fallback_reason).
    """
    pbi_type = VISUAL_TYPE_MAP.get(visual.visual_type.value)
    if pbi_type is not None:
        # KPI is a fallback to card
        is_fallback = visual.visual_type == VisualType.KPI
        reason = "KPI type mapped to card" if is_fallback else ""
        return pbi_type, is_fallback, reason

    # Unknown type - fallback
    return FALLBACK_VISUAL_TYPE, True, f"Unsupported type '{visual.visual_type.value}' fell back to card"


def make_visual_fidelity(visual: VisualSpec, rendered_type: str, is_fallback: bool, reason: str) -> VisualFidelity:
    """Create a fidelity record for a visual."""
    return VisualFidelity(
        visual_id=visual.id,
        visual_type=visual.visual_type.value,
        rendered_type=rendered_type,
        is_fallback=is_fallback,
        fallback_reason=reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Field Reference Builders
# ─────────────────────────────────────────────────────────────────────────────


def build_field_ref(field: FieldRef, measures: list[MeasureSpec] | None = None) -> dict:
    """Build a PBIR field reference dict for a FieldRef.

    Determines whether the field references a measure or column.
    """
    if field.measure:
        return {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": field.table}},
                "Property": field.measure,
            }
        }
    else:
        return {
            "Column": {
                "Expression": {"SourceRef": {"Entity": field.table}},
                "Property": field.column,
            }
        }


def build_query_ref(field: FieldRef) -> str:
    """Build the queryRef string for a field."""
    if field.measure:
        return f"{field.table}.{field.measure}"
    return f"{field.table}.{field.column}"


def build_projection(field: FieldRef, measures: list[MeasureSpec] | None = None) -> dict:
    """Build a single projection entry."""
    return {
        "field": build_field_ref(field, measures),
        "queryRef": build_query_ref(field),
        "active": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Query State Builders (per visual type)
# ─────────────────────────────────────────────────────────────────────────────


def _build_card_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Card: Values <- value_fields."""
    projections = [build_projection(f, measures) for f in visual.value_fields]
    if not projections and visual.category_fields:
        projections = [build_projection(f, measures) for f in visual.category_fields]
    return {"Values": {"projections": projections}}


def _build_line_area_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Line/Area: Category <- category_fields, Y <- value_fields, Series <- series_field."""
    state: dict = {}
    if visual.category_fields:
        state["Category"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if visual.value_fields:
        state["Y"] = {"projections": [build_projection(f, measures) for f in visual.value_fields]}
    if visual.series_field:
        state["Series"] = {"projections": [build_projection(visual.series_field, measures)]}
    return state


def _build_bar_column_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Bar/Column: Category <- category_fields, Y <- value_fields, Series <- series_field."""
    state: dict = {}
    if visual.category_fields:
        state["Category"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if visual.value_fields:
        state["Y"] = {"projections": [build_projection(f, measures) for f in visual.value_fields]}
    if visual.series_field:
        state["Series"] = {"projections": [build_projection(visual.series_field, measures)]}
    return state


def _build_table_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Table: Values <- category_fields + value_fields."""
    all_fields = list(visual.category_fields) + list(visual.value_fields)
    projections = [build_projection(f, measures) for f in all_fields]
    return {"Values": {"projections": projections}}


def _build_slicer_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Slicer: Values <- category_fields (or first field)."""
    fields = visual.category_fields or visual.value_fields
    projections = [build_projection(f, measures) for f in fields]
    return {"Values": {"projections": projections}}


def _build_map_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Map: Category/Location <- category_fields, Size <- value_fields."""
    state: dict = {}
    if visual.category_fields:
        state["Category"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if visual.value_fields:
        state["Size"] = {"projections": [build_projection(f, measures) for f in visual.value_fields]}
    return state


def _build_scatter_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Scatter: X <- value_fields[0], Y <- value_fields[1], Category <- category_fields."""
    state: dict = {}
    if visual.category_fields:
        state["Category"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if len(visual.value_fields) >= 1:
        state["X"] = {"projections": [build_projection(visual.value_fields[0], measures)]}
    if len(visual.value_fields) >= 2:
        state["Y"] = {"projections": [build_projection(visual.value_fields[1], measures)]}
    return state


def _build_donut_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Donut/Pie: Category <- category_fields, Y <- value_fields."""
    state: dict = {}
    if visual.category_fields:
        state["Category"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if visual.value_fields:
        state["Y"] = {"projections": [build_projection(f, measures) for f in visual.value_fields]}
    return state


def _build_treemap_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Treemap: Group <- category_fields, Values <- value_fields."""
    state: dict = {}
    if visual.category_fields:
        state["Group"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if visual.value_fields:
        state["Values"] = {"projections": [build_projection(f, measures) for f in visual.value_fields]}
    return state


def _build_gauge_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Gauge: Value <- value_fields[0]."""
    state: dict = {}
    if visual.value_fields:
        state["Value"] = {"projections": [build_projection(visual.value_fields[0], measures)]}
    return state


def _build_funnel_query(visual: VisualSpec, measures: list[MeasureSpec] | None = None) -> dict:
    """Funnel: Category <- category_fields, Y <- value_fields."""
    state: dict = {}
    if visual.category_fields:
        state["Category"] = {"projections": [build_projection(f, measures) for f in visual.category_fields]}
    if visual.value_fields:
        state["Y"] = {"projections": [build_projection(f, measures) for f in visual.value_fields]}
    return state


# Map of pbi visual types to their query builder
_QUERY_BUILDERS: dict[str, callable] = {
    "card": _build_card_query,
    "lineChart": _build_line_area_query,
    "areaChart": _build_line_area_query,
    "barChart": _build_bar_column_query,
    "clusteredBarChart": _build_bar_column_query,
    "stackedBarChart": _build_bar_column_query,
    "clusteredColumnChart": _build_bar_column_query,
    "stackedColumnChart": _build_bar_column_query,
    "lineClusteredColumnComboChart": _build_bar_column_query,
    "tableEx": _build_table_query,
    "pivotTable": _build_table_query,
    "slicer": _build_slicer_query,
    "map": _build_map_query,
    "filledMap": _build_map_query,
    "shapeMap": _build_map_query,
    "scatterChart": _build_scatter_query,
    "donutChart": _build_donut_query,
    "pieChart": _build_donut_query,
    "treemap": _build_treemap_query,
    "gauge": _build_gauge_query,
    "funnel": _build_funnel_query,
    "waterfallChart": _build_bar_column_query,
    "ribbonChart": _build_bar_column_query,
    "multiRowCard": _build_card_query,
}


def build_query_state(visual: VisualSpec, pbi_type: str, measures: list[MeasureSpec] | None = None) -> dict:
    """Build the queryState for a visual based on its Power BI type.

    Args:
        visual: The visual spec with field bindings.
        pbi_type: The resolved Power BI visual type string.
        measures: List of measures from the spec (for determining field types).

    Returns:
        The queryState dict for the visual's query.
    """
    builder = _QUERY_BUILDERS.get(pbi_type, _build_card_query)
    return builder(visual, measures)


def build_active_projections(query_state: dict) -> dict:
    """Build the activeProjections dict based on which roles have data."""
    return {role: True for role in query_state}
