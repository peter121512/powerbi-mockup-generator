"""Premium template registry for Power BI PBIP/PBIR generation.

Centralises design tokens, visual template definitions, and data-role metadata
so that page builders can compose dashboards from configuration rather than
hard-coded visual JSON.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Design Tokens
# ─────────────────────────────────────────────────────────────────────────────


class DesignTokens(BaseModel):
    """Centralised dark-premium design tokens for the entire template system."""

    # Canvas colours
    canvas: str = "#0f1623"
    surface: str = "#151d2e"
    border: str = "#1e293b"
    nav: str = "#060a10"

    # Text colours
    text_primary: str = "#ffffff"
    text_secondary: str = "#e2e8f0"
    text_muted: str = "#94a3b8"
    text_subtle: str = "#64748b"

    # Accent colours
    accent_blue: str = "#3898ff"
    accent_teal: str = "#34d399"
    accent_purple: str = "#a78bfa"
    accent_gold: str = "#fbbf24"
    accent_orange: str = "#fb923c"
    accent_red: str = "#f87171"

    # Semantic colours
    positive: str = "#34d399"
    negative: str = "#f87171"
    warning: str = "#fbbf24"

    # Spacing (px)
    page_margin: int = 10
    gutter: int = 10
    card_padding: int = 12

    # Typography
    font_heading: str = "Segoe UI Semibold"
    font_body: str = "Segoe UI"
    title_size: int = 24
    section_size: int = 12
    label_size: int = 11
    axis_size: int = 9
    value_size: int = 14

    # Shape
    radius: int = 8
    border_width: int = 1

    @property
    def data_colors(self) -> list[str]:
        """Ordered data-colour palette for Power BI theme."""
        return [
            self.accent_blue,
            self.accent_purple,
            self.accent_teal,
            self.accent_gold,
            self.negative,
            "#06b6d4",  # cyan
            "#818cf8",  # indigo
            self.accent_orange,
        ]

    def to_pbi_theme(self, theme_name: str = "ExecutiveDark") -> dict:
        """Generate the Power BI theme JSON dict (dark canvas variant)."""
        return {
            "name": theme_name,
            "dataColors": self.data_colors,
            "background": self.canvas,
            "foreground": self.text_primary,
            "foregroundNeutralSecondary": self.text_muted,
            "foregroundNeutralTertiary": self.text_subtle,
            "backgroundLight": self.surface,
            "backgroundNeutral": self.border,
            "backgroundDark": "#0a0e17",
            "tableAccent": self.accent_blue,
            "good": self.positive,
            "bad": self.negative,
            "neutral": self.warning,
            "visualStyles": {
                "page": {"*": {
                    "background": [{"show": True, "color": {"solid": {"color": self.canvas}}, "transparency": 0}],
                    "outspace": [{"color": {"solid": {"color": "#0a0e17"}}}],
                }},
                "*": {"*": {
                    "background": [{"show": False, "transparency": 100}],
                    "title": [{"show": True, "color": {"solid": {"color": self.text_secondary}}, "fontSize": self.label_size, "fontFamily": self.font_heading}],
                    "labels": [{"color": {"solid": {"color": self.text_muted}}, "fontSize": self.axis_size}],
                    "categoryAxis": [{"showAxisTitle": False, "labelColor": {"solid": {"color": self.text_muted}}, "fontSize": self.axis_size}],
                    "valueAxis": [{"showAxisTitle": False, "labelColor": {"solid": {"color": self.text_subtle}}, "fontSize": self.axis_size, "gridlineColor": {"solid": {"color": self.border}}, "gridlineStyle": 1}],
                    "legend": [{"labelColor": {"solid": {"color": self.text_muted}}, "fontSize": self.axis_size}],
                    "dataPoint": [{}],
                }},
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Data Role & Field Reference
# ─────────────────────────────────────────────────────────────────────────────


class DataRole(BaseModel):
    """A single data role slot within a visual template."""

    name: str
    kind: Literal["Grouping", "Measure"]
    display_name: str
    required: bool = True


class FieldRef(BaseModel):
    """Reference to a semantic model field (column or measure)."""

    entity: str
    property: str
    is_measure: bool = False
    query_ref: Optional[str] = None

    @property
    def resolved_query_ref(self) -> str:
        """Return explicit query_ref or synthesised entity.property."""
        return self.query_ref or f"{self.entity}.{self.property}"


# ─────────────────────────────────────────────────────────────────────────────
# Visual Template
# ─────────────────────────────────────────────────────────────────────────────


class VisualTemplate(BaseModel):
    """Definition of a reusable visual template (independent of data bindings)."""

    template_id: str
    visual_type: str  # GUID for custom visuals, native type string otherwise
    data_roles: list[DataRole]
    default_width: int
    default_height: int
    supports_cross_filter: bool = True
    supports_tooltips: bool = True
    description: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Visual Binding (instance of a template on a page)
# ─────────────────────────────────────────────────────────────────────────────


class VisualBinding(BaseModel):
    """A concrete binding of a visual template to data and position on a page."""

    template_id: str
    title: str
    data_bindings: dict[str, list[FieldRef]]
    position: tuple[int, int, int, int]  # (x, y, w, h)
    config_overrides: dict = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Page Shell
# ─────────────────────────────────────────────────────────────────────────────


class PageShell(BaseModel):
    """Structural definition of a report page (chrome, navigation, slicers)."""

    page_name: str
    display_name: str
    title: str
    subtitle: str
    nav_items: list[tuple[str, str]]  # (emoji+label, page_name)
    active_nav: str
    slicers: list[FieldRef] = Field(default_factory=list)
    width: int = 1280
    height: int = 720


# ─────────────────────────────────────────────────────────────────────────────
# Custom Visual GUIDs
# ─────────────────────────────────────────────────────────────────────────────

# Central registry of all custom visual GUIDs used by the premium template set.
CUSTOM_VISUAL_GUIDS = {
    "kpi": "premiumKPI0E21B11FE691418A84E3F774DD6461A5",
    "area_chart": "premiumAreaChart1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D",
    "gauge": "premiumGauge7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C",
    "insights": "premiumInsights2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D",
    "waterfall": "premiumWaterfall3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D",
}


# ─────────────────────────────────────────────────────────────────────────────
# Template Registry
# ─────────────────────────────────────────────────────────────────────────────


class TemplateRegistry(BaseModel):
    """Registry of available visual templates with lookup helpers."""

    templates: dict[str, VisualTemplate] = Field(default_factory=dict)

    @classmethod
    def default(cls) -> TemplateRegistry:
        """Return a pre-populated registry with the full premium template set."""
        templates: dict[str, VisualTemplate] = {}

        # premium_kpi — custom KPI card
        templates["premium_kpi"] = VisualTemplate(
            template_id="premium_kpi",
            visual_type=CUSTOM_VISUAL_GUIDS["kpi"],
            data_roles=[
                DataRole(name="measure", kind="Measure", display_name="Measure", required=True),
                DataRole(name="delta", kind="Measure", display_name="Delta / Comparison", required=False),
            ],
            default_width=245,
            default_height=100,
            supports_cross_filter=True,
            supports_tooltips=False,
            description="Premium dark KPI card with value, delta, and spark indicator.",
        )

        # premium_trend — custom area chart
        templates["premium_trend"] = VisualTemplate(
            template_id="premium_trend",
            visual_type=CUSTOM_VISUAL_GUIDS["area_chart"],
            data_roles=[
                DataRole(name="category", kind="Grouping", display_name="Category Axis", required=True),
                DataRole(name="values", kind="Measure", display_name="Values", required=True),
            ],
            default_width=635,
            default_height=240,
            supports_cross_filter=True,
            supports_tooltips=True,
            description="Premium area/line chart with gradient fill and toggle buttons.",
        )

        # premium_bar — native bar chart with premium styling
        templates["premium_bar"] = VisualTemplate(
            template_id="premium_bar",
            visual_type="barChart",
            data_roles=[
                DataRole(name="category", kind="Grouping", display_name="Category", required=True),
                DataRole(name="values", kind="Measure", display_name="Values", required=True),
            ],
            default_width=365,
            default_height=240,
            supports_cross_filter=True,
            supports_tooltips=True,
            description="Horizontal bar chart with dark styling and data labels.",
        )

        # premium_column — native column chart with premium styling
        templates["premium_column"] = VisualTemplate(
            template_id="premium_column",
            visual_type="columnChart",
            data_roles=[
                DataRole(name="category", kind="Grouping", display_name="Category", required=True),
                DataRole(name="values", kind="Measure", display_name="Values", required=True),
            ],
            default_width=365,
            default_height=240,
            supports_cross_filter=True,
            supports_tooltips=True,
            description="Vertical column chart with dark styling and legend.",
        )

        # premium_donut — native donut chart
        templates["premium_donut"] = VisualTemplate(
            template_id="premium_donut",
            visual_type="donutChart",
            data_roles=[
                DataRole(name="category", kind="Grouping", display_name="Category", required=True),
                DataRole(name="values", kind="Measure", display_name="Values", required=True),
            ],
            default_width=470,
            default_height=240,
            supports_cross_filter=True,
            supports_tooltips=True,
            description="Donut chart with center KPI label and legend.",
        )

        # premium_table — native enhanced table
        templates["premium_table"] = VisualTemplate(
            template_id="premium_table",
            visual_type="tableEx",
            data_roles=[
                DataRole(name="columns", kind="Grouping", display_name="Columns", required=True),
                DataRole(name="values", kind="Measure", display_name="Values", required=True),
            ],
            default_width=375,
            default_height=260,
            supports_cross_filter=True,
            supports_tooltips=False,
            description="Premium styled data table with alternating row colours.",
        )

        # premium_waterfall — custom waterfall visual
        templates["premium_waterfall"] = VisualTemplate(
            template_id="premium_waterfall",
            visual_type=CUSTOM_VISUAL_GUIDS["waterfall"],
            data_roles=[
                DataRole(name="category", kind="Grouping", display_name="Category", required=True),
                DataRole(name="values", kind="Measure", display_name="Values", required=True),
            ],
            default_width=375,
            default_height=260,
            supports_cross_filter=True,
            supports_tooltips=True,
            description="Waterfall chart showing incremental contribution to a total.",
        )

        # premium_gauge — custom gauge visual
        templates["premium_gauge"] = VisualTemplate(
            template_id="premium_gauge",
            visual_type=CUSTOM_VISUAL_GUIDS["gauge"],
            data_roles=[
                DataRole(name="measure", kind="Measure", display_name="Measure", required=True),
            ],
            default_width=365,
            default_height=240,
            supports_cross_filter=False,
            supports_tooltips=False,
            description="Premium radial gauge with animated needle and target band.",
        )

        # donut_center_kpi — transparent overlay for donut center label
        templates["donut_center_kpi"] = VisualTemplate(
            template_id="donut_center_kpi",
            visual_type="cardVisual",
            data_roles=[
                DataRole(name="measure", kind="Measure", display_name="Measure", required=True),
            ],
            default_width=100,
            default_height=44,
            supports_cross_filter=False,
            supports_tooltips=False,
            description="Transparent card overlay showing KPI value in donut center.",
        )

        return cls(templates=templates)

    def get(self, template_id: str) -> VisualTemplate:
        """Retrieve a template by ID. Raises KeyError if not found."""
        if template_id not in self.templates:
            available = ", ".join(sorted(self.templates.keys()))
            raise KeyError(f"Template '{template_id}' not found. Available: {available}")
        return self.templates[template_id]

    def list_templates(self) -> list[str]:
        """Return sorted list of registered template IDs."""
        return sorted(self.templates.keys())

    def custom_visual_guids(self) -> list[str]:
        """Return list of all custom-visual GUIDs that require PBIP packaging."""
        guids: list[str] = []
        for tmpl in self.templates.values():
            # Custom visuals have long GUID-style types (not simple names)
            if len(tmpl.visual_type) > 20 and tmpl.visual_type not in guids:
                guids.append(tmpl.visual_type)
        return sorted(guids)
