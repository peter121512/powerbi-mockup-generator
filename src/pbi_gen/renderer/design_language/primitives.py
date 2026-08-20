"""PBIR structural/decorative primitives for Power BI reports.

Generates native Power BI visual container definitions for non-data elements:
text boxes, shapes (rectangles), and divider lines.

Used to create page identity headers, section backgrounds, dividers, and
KPI band backgrounds. NOT for data visuals.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pbi_gen.renderer.design_language.variants import DesignLanguageVariant

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_VISUAL_CONTAINER_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
    "visualContainer/2.0.0/schema.json"
)

# Z-index tiers — structural elements render behind data visuals.
Z_BACKGROUND = 0
Z_SECTION_BG = 5
Z_DIVIDER = 10
Z_LABEL = 100


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _uid(prefix: str) -> str:
    """Generate a unique visual name with a human-readable prefix."""
    return f"{prefix}-{uuid4().hex[:8]}"


def _literal(value: str) -> dict:
    """Wrap a raw value in the PBIR Literal expression structure."""
    return {"expr": {"Literal": {"Value": value}}}


def _color_literal(hex_color: str) -> dict:
    """Wrap a hex colour in the PBIR solid-colour expression."""
    return {"solid": {"color": _literal(f"'{hex_color}'")}}


def _make_shape(
    name: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    fill_color: str,
    transparency: int = 0,
    show_border: bool = False,
) -> dict:
    """Create a shape (rectangle) visual container definition."""
    objects: dict = {
        "general": [
            {
                "properties": {
                    "background": _color_literal(fill_color),
                    "backgroundTransparency": _literal(f"{transparency}D"),
                }
            }
        ],
        "line": [
            {
                "properties": {
                    "show": _literal("false" if not show_border else "true"),
                }
            }
        ],
    }

    return {
        "$schema": _VISUAL_CONTAINER_SCHEMA,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "height": height,
            "width": width,
            "tabOrder": 0,
        },
        "visual": {
            "visualType": "shape",
            "objects": objects,
            "drillFilterOtherVisuals": True,
        },
    }


def _make_textbox(
    name: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    text: str,
    font_size_pt: int | float = 14,
    bold: bool = False,
    color: str = "#FFFFFF",
) -> dict:
    """Create a textbox visual container definition.

    The paragraphs value is a JSON-encoded string inside a PBIR literal,
    following the Power BI textbox paragraph format.
    """
    paragraph_item: dict = {
        "text": text,
        "font": {
            "size": f"{int(font_size_pt)}pt",
            "color": color,
        },
    }
    if bold:
        paragraph_item["font"]["bold"] = True

    # Encode the paragraph array as a JSON string inside the PBIR literal.
    # Power BI expects: '[{"text":"...","font":{...}}]'
    paragraph_json = json.dumps([paragraph_item], separators=(",", ":"))
    # Escape inner double quotes for the PBIR literal string
    escaped = paragraph_json.replace('"', '\\"')
    literal_value = f"'{escaped}'"

    objects: dict = {
        "general": [
            {
                "properties": {
                    "paragraphs": _literal(literal_value),
                }
            }
        ],
    }

    return {
        "$schema": _VISUAL_CONTAINER_SCHEMA,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "height": height,
            "width": width,
            "tabOrder": 0,
        },
        "visual": {
            "visualType": "textbox",
            "objects": objects,
            "drillFilterOtherVisuals": True,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def make_header_band(
    variant: DesignLanguageVariant,
    page_title: str,
    subtitle: str = "",
    canvas_width: int = 1280,
    height: int = 56,
    y: int = 0,
) -> list[dict]:
    """Create a page identity header band.

    Returns a list of visual dicts:
    - background shape (full width, accent/primary colour)
    - title textbox overlaid on the background

    If *subtitle* is provided, an additional smaller textbox is included
    below the title within the same band.
    """
    visuals: list[dict] = []

    # Background shape — full-width accent band
    bg = _make_shape(
        _uid("struct-header-bg"),
        x=0,
        y=y,
        width=canvas_width,
        height=height,
        z=Z_BACKGROUND,
        fill_color=variant.header_band_color,
        transparency=0,
    )
    visuals.append(bg)

    # Title textbox — inset from left edge
    title_x = 24
    title_y = y + (8 if not subtitle else 6)
    title_height = 32 if not subtitle else 26

    title_tb = _make_textbox(
        _uid("struct-header-title"),
        x=title_x,
        y=title_y,
        width=canvas_width - 48,
        height=title_height,
        z=Z_LABEL,
        text=page_title,
        font_size_pt=variant.page_title_size,
        bold=True,
        color=variant.header_text_color,
    )
    visuals.append(title_tb)

    # Optional subtitle
    if subtitle:
        sub_y = title_y + title_height + 2
        sub_tb = _make_textbox(
            _uid("struct-header-subtitle"),
            x=title_x,
            y=sub_y,
            width=canvas_width - 48,
            height=18,
            z=Z_LABEL,
            text=subtitle,
            font_size_pt=variant.page_subtitle_size,
            bold=False,
            color=variant.header_text_color,
        )
        visuals.append(sub_tb)

    return visuals


def make_section_band(
    variant: DesignLanguageVariant,
    y: int,
    height: int,
    canvas_width: int = 1280,
    label: str = "",
) -> list[dict]:
    """Create a subtle section background band.

    Returns visual dicts for a light-coloured rectangle that spans the
    full canvas width.  If *label* is provided, a small section label
    textbox is placed at the top-left of the band.
    """
    visuals: list[dict] = []

    bg = _make_shape(
        _uid("struct-section-bg"),
        x=0,
        y=y,
        width=canvas_width,
        height=height,
        z=Z_SECTION_BG,
        fill_color=variant.section_band_color,
        transparency=0,
    )
    visuals.append(bg)

    if label:
        label_tb = _make_textbox(
            _uid("struct-section-label"),
            x=24,
            y=y + 6,
            width=300,
            height=20,
            z=Z_LABEL,
            text=label,
            font_size_pt=variant.section_label_size,
            bold=True,
            color=variant.text_secondary,
        )
        visuals.append(label_tb)

    return visuals


def make_divider(
    variant: DesignLanguageVariant,
    y: int,
    canvas_width: int = 1280,
    margin: int = 45,
) -> dict:
    """Create a horizontal divider line.

    Returns a single shape visual dict — a thin rectangle (2px height)
    with horizontal margins on both sides.
    """
    return _make_shape(
        _uid("struct-divider"),
        x=margin,
        y=y,
        width=canvas_width - (margin * 2),
        height=2,
        z=Z_DIVIDER,
        fill_color=variant.divider_color,
        transparency=0,
    )


def make_kpi_band_background(
    variant: DesignLanguageVariant,
    y: int,
    height: int,
    canvas_width: int = 1280,
) -> dict:
    """Create a subtle background for the KPI section.

    Returns a single shape visual dict — a full-width rectangle
    with a slightly differentiated surface colour to visually group
    KPI cards together.
    """
    return _make_shape(
        _uid("struct-kpi-bg"),
        x=0,
        y=y,
        width=canvas_width,
        height=height,
        z=Z_BACKGROUND,
        fill_color=variant.section_band_color,
        transparency=0,
    )
