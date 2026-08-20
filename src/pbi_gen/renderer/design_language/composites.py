"""Composite visual components — native PBI visuals as data primitives in renderer-owned shells.

Architecture: Each composite component is a logical bounding box containing:
- Background/surface shapes (z=0-10)
- Label/title textboxes (z=100-200)
- Stripped native data visuals (z=1000+)
- Optional accent/divider elements (z=50-90)

The native visual is stripped of its own title/background/chrome and used
primarily for data rendering. The renderer owns the visual identity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from pbi_gen.renderer.design_language.variants import DesignLanguageVariant


# ─────────────────────────────────────────────────────────────────────────────
# Base component abstraction
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CompositeComponent:
    """A composite visual module with renderer-owned shell and native data visual."""

    # Logical bounding box
    x: float
    y: float
    width: float
    height: float

    # Generated visual dicts
    parts: list[dict] = field(default_factory=list)

    def add_background(self, name: str, color: str, *, z: int = 0, transparency: int = 0,
                       inset: int = 0) -> None:
        """Add a background shape to the component."""
        self.parts.append({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
            "name": name,
            "position": {
                "x": self.x + inset, "y": self.y + inset,
                "z": z,
                "width": self.width - 2 * inset, "height": self.height - 2 * inset,
                "tabOrder": 0,
            },
            "visual": {
                "visualType": "shape",
                "objects": {
                    "general": [{"properties": {
                        "background": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{color}'"}}}}},
                        "backgroundTransparency": {"expr": {"Literal": {"Value": f"{transparency}D"}}},
                    }}],
                    "line": [{"properties": {
                        "show": {"expr": {"Literal": {"Value": "false"}}},
                    }}],
                },
                "drillFilterOtherVisuals": True,
            },
        })

    def add_accent_line(self, name: str, color: str, *, position: str = "left",
                         thickness: int = 3, z: int = 50) -> None:
        """Add an accent line/bar to the component edge."""
        if position == "left":
            lx, ly, lw, lh = self.x, self.y, thickness, self.height
        elif position == "top":
            lx, ly, lw, lh = self.x, self.y, self.width, thickness
        elif position == "bottom":
            lx, ly, lw, lh = self.x, self.y + self.height - thickness, self.width, thickness
        else:
            lx, ly, lw, lh = self.x + self.width - thickness, self.y, thickness, self.height

        self.parts.append({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
            "name": name,
            "position": {"x": lx, "y": ly, "z": z, "width": lw, "height": lh, "tabOrder": 0},
            "visual": {
                "visualType": "shape",
                "objects": {
                    "general": [{"properties": {
                        "background": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{color}'"}}}}},
                        "backgroundTransparency": {"expr": {"Literal": {"Value": "0D"}}},
                    }}],
                    "line": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                },
                "drillFilterOtherVisuals": True,
            },
        })

    def add_textbox(self, name: str, text: str, *, font_size: float = 10,
                    color: str = "#1A1A2E", bold: bool = False,
                    x_offset: float = 0, y_offset: float = 0,
                    width: Optional[float] = None, height: float = 24,
                    z: int = 100) -> None:
        """Add a text label to the component."""
        # Build paragraph JSON for textbox
        font_props = {"size": f"{font_size}pt", "color": color}
        if bold:
            font_props["bold"] = True
        para = json.dumps([{"text": text, "font": font_props}])
        # Escape for PBIR literal
        escaped = para.replace("\\", "\\\\").replace("'", "\\'")

        self.parts.append({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
            "name": name,
            "position": {
                "x": self.x + x_offset, "y": self.y + y_offset,
                "z": z,
                "width": width or self.width - x_offset,
                "height": height,
                "tabOrder": 0,
            },
            "visual": {
                "visualType": "textbox",
                "objects": {
                    "general": [{"properties": {
                        "paragraphs": {"expr": {"Literal": {"Value": f"'{escaped}'"}}},
                    }}],
                },
                "drillFilterOtherVisuals": True,
            },
        })


# ─────────────────────────────────────────────────────────────────────────────
# Stripped native visual configs
# ─────────────────────────────────────────────────────────────────────────────


def stripped_card_objects(variant: DesignLanguageVariant) -> dict:
    """PBIR objects for a card stripped of its native chrome.

    Hides title (shell owns it), makes background transparent,
    shows only the callout value.
    """
    return {
        "general": [{"properties": {
            "titleShow": {"expr": {"Literal": {"Value": "false"}}},
            "background": {"solid": {"color": {"expr": {"Literal": {"Value": "'#FFFFFF'"}}}}},
            "backgroundTransparency": {"expr": {"Literal": {"Value": "100D"}}},
        }}],
        "labels": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "fontSize": {"expr": {"Literal": {"Value": f"{int(variant.kpi_value_size)}D"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{variant.kpi_value_color}'"}}}}},
        }}],
        "categoryLabels": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "false"}}},
        }}],
    }


def stripped_chart_objects(variant: DesignLanguageVariant) -> dict:
    """PBIR objects for a chart stripped of native title/background."""
    return {
        "general": [{"properties": {
            "titleShow": {"expr": {"Literal": {"Value": "false"}}},
            "background": {"solid": {"color": {"expr": {"Literal": {"Value": "'#FFFFFF'"}}}}},
            "backgroundTransparency": {"expr": {"Literal": {"Value": "100D"}}},
        }}],
        "categoryAxis": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
        }}],
        "valueAxis": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
            "gridlineShow": {"expr": {"Literal": {"Value": "true"}}},
        }}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Composite KPI component
# ─────────────────────────────────────────────────────────────────────────────


def build_composite_kpi(
    visual_id: str,
    title: str,
    query_state: dict,
    variant: DesignLanguageVariant,
    *,
    x: float, y: float, width: float, height: float,
    z_base: int = 1000,
    priority: int = 1,
) -> list[dict]:
    """Build a composite KPI component.

    Structure:
    - White card surface with subtle accent
    - External label textbox (metric name)
    - Stripped native card (value only, no title, no category label)

    Args:
        visual_id: The original visual ID for the native card.
        title: The KPI metric label.
        query_state: The card's query state for data binding.
        variant: Design language variant.
        x, y, width, height: Bounding box.
        z_base: Z-index base for the data visual.
        priority: Visual priority (1=most important).

    Returns:
        List of PBIR visual dicts.
    """
    comp = CompositeComponent(x=x, y=y, width=width, height=height)

    # 1. Card surface
    comp.add_background(f"comp-kpi-bg-{visual_id}", variant.card_background, z=2)

    # 2. Left accent bar (subtle branded accent)
    comp.add_accent_line(f"comp-kpi-accent-{visual_id}", variant.accent_primary,
                          position="left", thickness=3, z=5)

    # 3. Label textbox (metric name) — positioned at top of card
    label_height = 20
    comp.add_textbox(
        f"comp-kpi-label-{visual_id}",
        title,
        font_size=variant.kpi_label_size,
        color=variant.text_secondary,
        bold=False,
        x_offset=12,
        y_offset=8,
        height=label_height,
        z=100,
    )

    # 4. Stripped native card — positioned below label, fills remaining space
    value_y = y + label_height + 4
    value_height = height - label_height - 12
    native_card = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": visual_id,
        "position": {
            "x": x + 8, "y": value_y,
            "z": z_base,
            "width": width - 16, "height": value_height,
            "tabOrder": z_base,
        },
        "visual": {
            "visualType": "card",
            "query": {"queryState": query_state},
            "objects": stripped_card_objects(variant),
            "drillFilterOtherVisuals": True,
        },
    }

    return comp.parts + [native_card]


# ─────────────────────────────────────────────────────────────────────────────
# Composite chart component
# ─────────────────────────────────────────────────────────────────────────────


def build_composite_chart(
    visual_id: str,
    title: str,
    pbi_type: str,
    query_state: dict,
    variant: DesignLanguageVariant,
    *,
    x: float, y: float, width: float, height: float,
    z_base: int = 1000,
    is_hero: bool = False,
) -> list[dict]:
    """Build a composite chart component.

    Structure:
    - White surface background
    - External title textbox
    - Stripped native chart (no title, transparent bg, minimal axes)

    Args:
        visual_id: Original visual ID.
        title: Chart title text.
        pbi_type: Power BI visual type string.
        query_state: Chart query state.
        variant: Design language variant.
        x, y, width, height: Bounding box.
        z_base: Z-index base.
        is_hero: Whether this is the hero visual (gets extra emphasis).

    Returns:
        List of PBIR visual dicts.
    """
    comp = CompositeComponent(x=x, y=y, width=width, height=height)

    # 1. Surface
    comp.add_background(f"comp-chart-bg-{visual_id}", variant.card_background, z=2)

    # 2. Title textbox
    title_height = 28
    title_size = variant.visual_title_size + (2 if is_hero else 0)
    comp.add_textbox(
        f"comp-chart-title-{visual_id}",
        title,
        font_size=title_size,
        color=variant.text_primary,
        bold=True,
        x_offset=12,
        y_offset=8,
        height=title_height,
        z=100,
    )

    # 3. Stripped native chart — positioned below title
    chart_y = y + title_height + 4
    chart_height = height - title_height - 12
    native_chart = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": visual_id,
        "position": {
            "x": x + 8, "y": chart_y,
            "z": z_base,
            "width": width - 16, "height": chart_height,
            "tabOrder": z_base,
        },
        "visual": {
            "visualType": pbi_type,
            "query": {"queryState": query_state},
            "objects": stripped_chart_objects(variant),
            "drillFilterOtherVisuals": True,
        },
    }

    return comp.parts + [native_chart]
