"""PBIR formatting objects for chart visuals.

Generates the `objects` dict that controls visual presentation properties
(axes, gridlines, legends, markers) for chart-type visuals in Power BI
Report (PBIR) format.
"""

from __future__ import annotations

from typing import Any, Protocol

from pbi_gen.models import VisualSpec


# ─────────────────────────────────────────────────────────────────────────────
# Design system protocol
# ─────────────────────────────────────────────────────────────────────────────


class _Typography(Protocol):
    visual_title_size: float
    axis_label_size: float
    legend_size: float


class _Colours(Protocol):
    text_secondary: str
    grid_color: str


class _Spacing(Protocol):
    title_margin: float


class DesignSystemLike(Protocol):
    """Structural protocol for the design system parameter."""

    typography: _Typography
    colours: _Colours
    spacing: _Spacing


# ─────────────────────────────────────────────────────────────────────────────
# PBIR literal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _literal(value: str) -> dict:
    """Wrap a value in the PBIR Literal expression structure."""
    return {"expr": {"Literal": {"Value": value}}}


def _bool_lit(val: bool) -> dict:
    return _literal("true" if val else "false")


def _num_lit(val: float | int) -> dict:
    return _literal(f"{val}D")


def _str_lit(val: str) -> dict:
    return _literal(f"'{val}'")


# ─────────────────────────────────────────────────────────────────────────────
# Shared object builders
# ─────────────────────────────────────────────────────────────────────────────


def _general_objects(visual: VisualSpec) -> list[dict]:
    """Build general properties (title)."""
    title = visual.title or ""
    return [{"properties": {"title": _str_lit(title)}}]


def _category_axis(ds: DesignSystemLike, *, show_title: bool = False) -> list[dict]:
    """Build categoryAxis properties with restrained styling."""
    return [{"properties": {
        "show": _bool_lit(True),
        "fontSize": _num_lit(ds.typography.axis_label_size),
        "fontColor": _str_lit(ds.colours.text_secondary),
        "showAxisTitle": _bool_lit(show_title),
    }}]


def _value_axis(
    ds: DesignSystemLike,
    *,
    show_title: bool = False,
    show_gridlines: bool = True,
) -> list[dict]:
    """Build valueAxis properties with restrained gridlines."""
    return [{"properties": {
        "show": _bool_lit(True),
        "fontSize": _num_lit(ds.typography.axis_label_size),
        "fontColor": _str_lit(ds.colours.text_secondary),
        "gridlineShow": _bool_lit(show_gridlines),
        "gridlineColor": _str_lit(ds.colours.grid_color),
        "gridlineThickness": _num_lit(1),
        "showAxisTitle": _bool_lit(show_title),
    }}]


def _legend(ds: DesignSystemLike, *, show: bool = True, position: str = "Top") -> list[dict]:
    """Build legend properties."""
    return [{"properties": {
        "show": _bool_lit(show),
        "position": _str_lit(position),
        "fontSize": _num_lit(ds.typography.legend_size),
        "fontColor": _str_lit(ds.colours.text_secondary),
    }}]


def _is_single_series(visual: VisualSpec) -> bool:
    """Determine if the visual has only one data series (no legend needed)."""
    return visual.series_field is None and len(visual.value_fields) <= 1


# ─────────────────────────────────────────────────────────────────────────────
# Per-type formatters
# ─────────────────────────────────────────────────────────────────────────────


def _line_area_objects(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Format objects for lineChart and areaChart."""
    objects: dict[str, Any] = {
        "general": _general_objects(visual),
        "categoryAxis": _category_axis(ds),
        "valueAxis": _value_axis(ds),
    }

    # Line-specific: markers and line weight
    objects["lineStyles"] = [{"properties": {
        "strokeWidth": _num_lit(2),
        "showMarker": _bool_lit(False),
    }}]

    # Hide legend for single-series
    show_legend = not _is_single_series(visual)
    objects["legend"] = _legend(ds, show=show_legend)

    return objects


def _bar_column_objects(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Format objects for bar and column chart variants."""
    objects: dict[str, Any] = {
        "general": _general_objects(visual),
        "categoryAxis": _category_axis(ds),
        "valueAxis": _value_axis(ds),
    }

    # Gap width for readability
    objects["dataPoint"] = [{"properties": {
        "categoryGap": _num_lit(30),
    }}]

    # Hide legend for single-series
    show_legend = not _is_single_series(visual)
    objects["legend"] = _legend(ds, show=show_legend)

    return objects


def _donut_pie_objects(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Format objects for donutChart and pieChart."""
    return {
        "general": _general_objects(visual),
        "legend": _legend(ds, show=True, position="Right"),
        "labels": [{"properties": {
            "show": _bool_lit(True),
            "fontSize": _num_lit(ds.typography.axis_label_size),
            "fontColor": _str_lit(ds.colours.text_secondary),
            "labelStyle": _str_lit("Category"),
        }}],
    }


def _scatter_objects(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Format objects for scatterChart."""
    return {
        "general": _general_objects(visual),
        "categoryAxis": _category_axis(ds),
        "valueAxis": _value_axis(ds),
        "legend": _legend(ds, show=not _is_single_series(visual)),
        "fillPoint": [{"properties": {
            "show": _bool_lit(True),
        }}],
        "dataPoint": [{"properties": {
            "defaultSize": _num_lit(8),
        }}],
    }


def _combo_objects(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Format objects for lineClusteredColumnComboChart."""
    objects: dict[str, Any] = {
        "general": _general_objects(visual),
        "categoryAxis": _category_axis(ds),
        "valueAxis": _value_axis(ds),
        "legend": _legend(ds, show=True),
    }

    # Column gap and line styling for combo
    objects["dataPoint"] = [{"properties": {
        "categoryGap": _num_lit(30),
    }}]
    objects["lineStyles"] = [{"properties": {
        "strokeWidth": _num_lit(2),
        "showMarker": _bool_lit(True),
    }}]

    return objects


def _map_objects(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Format objects for map and filledMap — minimal styling."""
    return {
        "general": _general_objects(visual),
        "legend": _legend(ds, show=not _is_single_series(visual)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Type dispatch
# ─────────────────────────────────────────────────────────────────────────────

_CHART_FORMATTERS: dict[str, Any] = {
    "lineChart": _line_area_objects,
    "areaChart": _line_area_objects,
    "barChart": _bar_column_objects,
    "clusteredBarChart": _bar_column_objects,
    "clusteredColumnChart": _bar_column_objects,
    "stackedBarChart": _bar_column_objects,
    "stackedColumnChart": _bar_column_objects,
    "donutChart": _donut_pie_objects,
    "pieChart": _donut_pie_objects,
    "scatterChart": _scatter_objects,
    "lineClusteredColumnComboChart": _combo_objects,
    "map": _map_objects,
    "filledMap": _map_objects,
}


def build_chart_objects(
    design_system: DesignSystemLike,
    visual_spec: VisualSpec,
    pbi_type: str,
) -> dict:
    """Build the PBIR objects dict for a chart visual.

    Selects the appropriate formatting based on the Power BI visual type
    and applies enterprise design policies: restrained gridlines, readable
    axis labels, hidden redundant legends, and consistent title styling.

    Args:
        design_system: The resolved design system providing typography,
            colour, and spacing values.
        visual_spec: The visual specification with field bindings and title.
        pbi_type: The Power BI visual type string (e.g. 'lineChart').

    Returns:
        A dict suitable for the visual's ``objects`` property in PBIR format.
    """
    formatter = _CHART_FORMATTERS.get(pbi_type)
    if formatter is None:
        # Fallback: return minimal general-only objects
        return {"general": _general_objects(visual_spec)}

    return formatter(design_system, visual_spec)
