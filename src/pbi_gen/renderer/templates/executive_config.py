"""Executive Overview page configuration.

Recreates the existing Stage 07e Executive Overview page layout using the
declarative template/binding system. This proves the template system can fully
express the page that was previously hand-coded, enabling both pages to be
generated from a unified rendering pipeline.

Semantic model: ExecutiveRetailPerformanceDashboard
    Tables: Sales, Date, Region, Product
    Measures on Sales: TotalRevenue, GrossProfit, TotalCost, GrossMarginPct
    Columns: Region.RegionName, Product.CategoryName, Date.Year, Date.Month

Layout: 1280×720 canvas with 140px navigation rail on the left.
"""

from __future__ import annotations

from .registry import FieldRef, PageShell, VisualBinding

# ─────────────────────────────────────────────────────────────────────────────
# Semantic model field references
# ─────────────────────────────────────────────────────────────────────────────

_TOTAL_REVENUE = FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)
_GROSS_PROFIT = FieldRef(entity="Sales", property="GrossProfit", is_measure=True)
_TOTAL_COST = FieldRef(entity="Sales", property="TotalCost", is_measure=True)
_GROSS_MARGIN_PCT = FieldRef(entity="Sales", property="GrossMarginPct", is_measure=True)

_REGION_NAME = FieldRef(entity="Region", property="RegionName")
_CATEGORY_NAME = FieldRef(entity="Product", property="CategoryName")
_DATE_YEAR = FieldRef(entity="Date", property="Year")
_DATE_MONTH = FieldRef(entity="Date", property="Month")

# ─────────────────────────────────────────────────────────────────────────────
# Layout constants (matching Stage 07e rendered output)
# ─────────────────────────────────────────────────────────────────────────────

_PAGE_WIDTH = 1280
_PAGE_HEIGHT = 720
_NAV_RAIL_WIDTH = 140
_CONTENT_LEFT = 155  # Nav rail + gutter

_CONTENT_WIDTH = _PAGE_WIDTH - _CONTENT_LEFT - 15  # Right margin ~1110px

# KPI row
_KPI_ROW_Y = 90
_KPI_HEIGHT = 90
_KPI_COUNT = 4
_KPI_GAP = 15
_KPI_WIDTH = int((_CONTENT_WIDTH - (_KPI_COUNT - 1) * _KPI_GAP) / _KPI_COUNT)

# Hero chart (large area chart spanning most of the width)
_HERO_Y = 200
_HERO_HEIGHT = 240
_HERO_WIDTH = 700

# Side panel (donut, right of hero)
_SIDE_X = _CONTENT_LEFT + _HERO_WIDTH + 15
_SIDE_WIDTH = _CONTENT_WIDTH - _HERO_WIDTH - 15

# Bottom row
_BOT_ROW_Y = 460
_BOT_ROW_HEIGHT = 240
_BOT_GAP = 15
_BOT_COL1_W = 420  # Bar chart
_BOT_COL2_W = 350  # Gauge
_BOT_COL3_W = _CONTENT_WIDTH - _BOT_COL1_W - _BOT_COL2_W - 2 * _BOT_GAP  # Insights

# Navigation items shared across pages
_NAV_ITEMS: list[tuple[str, str]] = [
    ("📊 Executive", "executive_overview"),
    ("💰 Financial", "financial_performance"),
    ("📈 Sales", "sales_detail"),
    ("🌍 Regional", "regional_breakdown"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Page shell
# ─────────────────────────────────────────────────────────────────────────────


def executive_page_shell() -> PageShell:
    """Configuration for the Executive Overview page shell."""
    return PageShell(
        page_name="executive_overview",
        display_name="Executive Overview",
        title="Executive Overview",
        subtitle="Retail Performance Dashboard · FY 2024",
        nav_items=_NAV_ITEMS,
        active_nav="executive_overview",
        slicers=[_DATE_YEAR, _REGION_NAME],
        width=_PAGE_WIDTH,
        height=_PAGE_HEIGHT,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Visual bindings
# ─────────────────────────────────────────────────────────────────────────────


def executive_visual_bindings() -> list[VisualBinding]:
    """All visual bindings for the Executive Overview page.

    Recreates the Stage 07e layout:
        - 4 KPI cards: TotalRevenue, GrossProfit, TotalCost, GrossMarginPct
        - Hero area chart: Revenue + Gross Profit over Date (Year/Month)
        - Donut: Revenue by Region
        - Bar: Revenue by Product Category
        - Gauge: Total Revenue (placeholder for target tracking)
        - Insight card: placeholder for AI-generated narrative

    Template IDs reference the TemplateRegistry (premium_kpi, premium_trend,
    premium_bar, premium_donut, premium_gauge).
    """
    bindings: list[VisualBinding] = []

    # ─── KPI Row (4 cards) ───────────────────────────────────────────────
    kpi_definitions: list[tuple[str, FieldRef, dict]] = [
        ("Total Revenue", _TOTAL_REVENUE, {"format": '$#,##0.0,,"M"'}),
        ("Gross Profit", _GROSS_PROFIT, {"format": '$#,##0.0,,"M"'}),
        ("Total Cost", _TOTAL_COST, {"format": '$#,##0.0,,"M"'}),
        ("Gross Margin %", _GROSS_MARGIN_PCT, {"format": "0.0%"}),
    ]

    for i, (title, measure, overrides) in enumerate(kpi_definitions):
        x = _CONTENT_LEFT + i * (_KPI_WIDTH + _KPI_GAP)
        bindings.append(
            VisualBinding(
                template_id="premium_kpi",
                title=title,
                data_bindings={"measure": [measure]},
                position=(x, _KPI_ROW_Y, _KPI_WIDTH, _KPI_HEIGHT),
                config_overrides={
                    "kpi_index": i,
                    "show_trend_spark": True,
                    **overrides,
                },
            )
        )

    # ─── Hero Area Chart (Revenue + Profit over time) ────────────────────
    bindings.append(
        VisualBinding(
            template_id="premium_trend",
            title="Revenue & Profit Trend",
            data_bindings={
                "category": [_DATE_YEAR, _DATE_MONTH],
                "values": [_TOTAL_REVENUE, _GROSS_PROFIT],
            },
            position=(_CONTENT_LEFT, _HERO_Y, _HERO_WIDTH, _HERO_HEIGHT),
            config_overrides={
                "chart_type": "area",
                "show_data_labels": False,
                "stacked": False,
                "show_legend": True,
                "legend_position": "top",
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    # ─── Donut Chart (Revenue by Region) ─────────────────────────────────
    bindings.append(
        VisualBinding(
            template_id="premium_donut",
            title="Revenue by Region",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_TOTAL_REVENUE],
            },
            position=(_SIDE_X, _HERO_Y, _SIDE_WIDTH, _HERO_HEIGHT),
            config_overrides={
                "inner_radius_pct": 55,
                "show_legend": True,
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    # ─── Bottom Row ──────────────────────────────────────────────────────

    # Bar Chart (Revenue by Product Category)
    bot_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Revenue by Category",
            data_bindings={
                "category": [_CATEGORY_NAME],
                "values": [_TOTAL_REVENUE],
            },
            position=(bot_x1, _BOT_ROW_Y, _BOT_COL1_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "orientation": "horizontal",
                "show_data_labels": True,
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    # Gauge (Total Revenue — placeholder for target-based tracking)
    bot_x2 = bot_x1 + _BOT_COL1_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_gauge",
            title="Revenue vs Target",
            data_bindings={
                "measure": [_TOTAL_REVENUE],
            },
            position=(bot_x2, _BOT_ROW_Y, _BOT_COL2_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "target_value": None,
                "min_value": 0,
                "show_callout": True,
                "format": '$#,##0.0,,"M"',
                "note": "Gauge target would come from a Targets/Budget table. "
                "Currently shows total revenue as the gauge value.",
            },
        )
    )

    # AI Insights Card (placeholder — uses premium_kpi as fallback template)
    bot_x3 = bot_x2 + _BOT_COL2_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_kpi",
            title="Key Insights",
            data_bindings={
                "measure": [_TOTAL_REVENUE],
            },
            position=(bot_x3, _BOT_ROW_Y, _BOT_COL3_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "insight_type": "ai_narrative",
                "placeholder_text": "AI-generated executive summary of key "
                "performance trends and anomalies.",
                "note": "Rendered as a text visual or smart narrative "
                "in full Power BI deployment. Uses KPI template as "
                "structural placeholder.",
            },
        )
    )

    return bindings
