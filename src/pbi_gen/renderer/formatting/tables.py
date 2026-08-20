"""PBIR formatting objects for table and matrix visuals.

Generates the `objects` dict that controls visual presentation properties
(headers, grid lines, row padding, font sizes) for table-type visuals in
Power BI Report (PBIR) format.
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
# Defaults
# ─────────────────────────────────────────────────────────────────────────────

_HEADER_BG_TINT = "#F3F2F1"  # Light neutral tint for header background
_HEADER_FONT_COLOR = "#252423"  # Near-black for strong header contrast
_BODY_FONT_SIZE = 9  # Body text default
_HEADER_FONT_SIZE = 10  # Slightly larger for header
_ROW_PADDING = 4  # Comfortable row density


# ─────────────────────────────────────────────────────────────────────────────
# Object builders
# ─────────────────────────────────────────────────────────────────────────────


def _general_objects(visual: VisualSpec) -> list[dict]:
    """Build general properties (title)."""
    title = visual.title or ""
    return [{"properties": {"title": _str_lit(title)}}]


def _grid_objects(ds: DesignSystemLike) -> list[dict]:
    """Build grid properties with restrained styling.

    Policies:
    - Horizontal gridlines only (vertical suppressed for cleanliness).
    - Adequate row padding for readable density.
    - Consistent text sizing from design system.
    """
    body_size = ds.typography.axis_label_size or _BODY_FONT_SIZE
    return [{"properties": {
        "gridVertical": _bool_lit(False),
        "gridHorizontal": _bool_lit(True),
        "gridHorizontalColor": _str_lit(ds.colours.grid_color),
        "gridHorizontalWeight": _num_lit(1),
        "rowPadding": _num_lit(_ROW_PADDING),
        "textSize": _num_lit(body_size),
        "outline": _str_lit("None"),
    }}]


def _column_headers_objects(ds: DesignSystemLike) -> list[dict]:
    """Build column header properties.

    Policies:
    - Bold / semibold font for clear hierarchy.
    - Background tint to distinguish from body rows.
    - Slightly larger font than body text.
    """
    header_size = (ds.typography.axis_label_size or _BODY_FONT_SIZE) + 1
    return [{"properties": {
        "fontColor": _str_lit(_HEADER_FONT_COLOR),
        "backColor": _str_lit(_HEADER_BG_TINT),
        "bold": _bool_lit(True),
        "fontSize": _num_lit(header_size),
        "wordWrap": _bool_lit(True),
    }}]


def _values_objects(ds: DesignSystemLike) -> list[dict]:
    """Build body value properties.

    Applies consistent font colour and size for data cells.
    """
    body_size = ds.typography.axis_label_size or _BODY_FONT_SIZE
    return [{"properties": {
        "fontColor": _str_lit(ds.colours.text_secondary),
        "fontSize": _num_lit(body_size),
        "wordWrap": _bool_lit(False),
    }}]


def _total_objects() -> list[dict]:
    """Build total/subtotal row properties for pivot tables."""
    return [{"properties": {
        "bold": _bool_lit(True),
        "fontColor": _str_lit(_HEADER_FONT_COLOR),
    }}]


def _build_table_ex(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Build objects for tableEx (flat table)."""
    return {
        "general": _general_objects(visual),
        "grid": _grid_objects(ds),
        "columnHeaders": _column_headers_objects(ds),
        "values": _values_objects(ds),
    }


def _build_pivot_table(ds: DesignSystemLike, visual: VisualSpec) -> dict:
    """Build objects for pivotTable (matrix).

    Includes row and column headers plus subtotal styling.
    """
    return {
        "general": _general_objects(visual),
        "grid": _grid_objects(ds),
        "columnHeaders": _column_headers_objects(ds),
        "values": _values_objects(ds),
        "total": _total_objects(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Type dispatch
# ─────────────────────────────────────────────────────────────────────────────

_TABLE_FORMATTERS: dict[str, Any] = {
    "tableEx": _build_table_ex,
    "pivotTable": _build_pivot_table,
}


def build_table_objects(
    design_system: DesignSystemLike,
    visual_spec: VisualSpec,
    pbi_type: str,
) -> dict:
    """Build the PBIR objects dict for a table or matrix visual.

    Applies enterprise table formatting policies: clear bold headers with a
    background tint, restrained horizontal gridlines, readable row density,
    and consistent font sizing.

    Args:
        design_system: The resolved design system providing typography,
            colour, and spacing values.
        visual_spec: The visual specification with field bindings and title.
        pbi_type: The Power BI visual type string ('tableEx' or 'pivotTable').

    Returns:
        A dict suitable for the visual's ``objects`` property in PBIR format.
    """
    formatter = _TABLE_FORMATTERS.get(pbi_type)
    if formatter is None:
        # Fallback: return minimal general-only objects
        return {"general": _general_objects(visual_spec)}

    return formatter(design_system, visual_spec)
