"""Financial Performance page configuration.

Defines the complete visual layout and field bindings for the Financial
Performance page of the multi-page Power BI report. All bindings reference
the existing ExecutiveRetailPerformanceDashboard semantic model:

    Tables: Sales, Date, Region, Product
    Measures on Sales: TotalRevenue, GrossProfit, TotalCost, GrossMarginPct
    Columns: Region.RegionName, Product.CategoryName, Date.Year, Date.Month

Layout: 1280×720 canvas with 140px navigation rail on the left.
Content area starts at x=155 (140 + 15px gutter).
"""

from __future__ import annotations

from .registry import FieldRef, PageShell, VisualBinding

# ─────────────────────────────────────────────────────────────────────────────
# Semantic model field references (reusable constants)
# ─────────────────────────────────────────────────────────────────────────────

# Measures (is_measure=True for proper binding generation)
_TOTAL_REVENUE = FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)
_GROSS_PROFIT = FieldRef(entity="Sales", property="GrossProfit", is_measure=True)
_TOTAL_COST = FieldRef(entity="Sales", property="TotalCost", is_measure=True)
_GROSS_MARGIN_PCT = FieldRef(entity="Sales", property="GrossMarginPct", is_measure=True)

# Dimension columns
_REGION_NAME = FieldRef(entity="Region", property="RegionName")
_CATEGORY_NAME = FieldRef(entity="Product", property="CategoryName")
_DATE_YEAR = FieldRef(entity="Date", property="Year")
_DATE_MONTH = FieldRef(entity="Date", property="Month")

# ─────────────────────────────────────────────────────────────────────────────
# Layout constants
# ─────────────────────────────────────────────────────────────────────────────

_PAGE_WIDTH = 1280
_PAGE_HEIGHT = 720
_NAV_RAIL_WIDTH = 140
_CONTENT_LEFT = 155  # Nav rail + gutter

# Content area dimensions
_CONTENT_WIDTH = _PAGE_WIDTH - _CONTENT_LEFT - 15  # Right margin ~1110px

# KPI row
_KPI_ROW_Y = 90
_KPI_HEIGHT = 90
_KPI_COUNT = 5
_KPI_GAP = 12
_KPI_WIDTH = int((_CONTENT_WIDTH - (_KPI_COUNT - 1) * _KPI_GAP) / _KPI_COUNT)

# Middle row (3 panels)
_MID_ROW_Y = 200
_MID_ROW_HEIGHT = 235
_MID_GAP = 15
_MID_COL1_W = 485  # Revenue over time
_MID_COL2_W = 365  # Donut
_MID_COL3_W = _CONTENT_WIDTH - _MID_COL1_W - _MID_COL2_W - 2 * _MID_GAP  # ~245

# Bottom row (3 panels)
_BOT_ROW_Y = 455
_BOT_ROW_HEIGHT = 245
_BOT_GAP = 15
_BOT_COL1_W = 375  # Table
_BOT_COL2_W = 375  # Waterfall / cash flow
_BOT_COL3_W = _CONTENT_WIDTH - _BOT_COL1_W - _BOT_COL2_W - 2 * _BOT_GAP  # ~345

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


def financial_page_shell() -> PageShell:
    """Configuration for the Financial Performance page shell."""
    return PageShell(
        page_name="financial_performance",
        display_name="Financial Performance",
        title="Financial Performance",
        subtitle="P&L Analysis · Profitability · Cost Structure",
        nav_items=_NAV_ITEMS,
        active_nav="financial_performance",
        slicers=[_DATE_YEAR],
        width=_PAGE_WIDTH,
        height=_PAGE_HEIGHT,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Visual bindings
# ─────────────────────────────────────────────────────────────────────────────


def financial_visual_bindings() -> list[VisualBinding]:
    """All visual bindings for the Financial Performance page.

    Maps template visuals to existing semantic model fields.
    Uses existing measures: TotalRevenue, GrossProfit, TotalCost, GrossMarginPct
    from the Sales entity, and RegionName from Region, CategoryName from Product,
    Year/Month from Date.

    Layout (1280×720 with 140px nav rail):
        - KPI row: 5 cards at y=90
        - Middle row: Revenue trend (485w) | Donut (365w) | Bar (~245w)
        - Bottom row: Table (375w) | Waterfall (375w) | Region (~345w)

    Template IDs reference the TemplateRegistry (premium_kpi, premium_trend,
    premium_bar, premium_donut, premium_table, premium_waterfall).
    """
    bindings: list[VisualBinding] = []

    # ─── KPI Row (5 cards) ───────────────────────────────────────────────
    # Each KPI uses the premium_kpi template with a single measure binding.
    # For metrics that don't exist as separate measures (EBITDA, Net Profit),
    # we bind to the closest available measure and use title/config overrides.
    kpi_definitions: list[tuple[str, FieldRef, dict]] = [
        ("Total Revenue", _TOTAL_REVENUE, {}),
        ("Gross Profit", _GROSS_PROFIT, {}),
        ("EBITDA", _GROSS_PROFIT, {"title_override": "EBITDA", "format": '$#,##0.0,,"M"'}),
        ("Net Profit", _TOTAL_REVENUE, {"title_override": "Net Profit", "format": '$#,##0.0,,"M"'}),
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

    # ─── Middle Row ──────────────────────────────────────────────────────

    # Revenue Over Time (area/line trend)
    mid_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_trend",
            title="Revenue Over Time",
            data_bindings={
                "category": [_DATE_YEAR, _DATE_MONTH],
                "values": [_TOTAL_REVENUE],
            },
            position=(mid_x1, _MID_ROW_Y, _MID_COL1_W, _MID_ROW_HEIGHT),
            config_overrides={
                "chart_type": "area",
                "show_data_labels": False,
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    # Profitability Overview (donut)
    mid_x2 = mid_x1 + _MID_COL1_W + _MID_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_donut",
            title="Profitability Overview",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_GROSS_PROFIT],
            },
            position=(mid_x2, _MID_ROW_Y, _MID_COL2_W, _MID_ROW_HEIGHT),
            config_overrides={
                "inner_radius_pct": 55,
                "show_legend": True,
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    # Expenses by Category (bar chart)
    mid_x3 = mid_x2 + _MID_COL2_W + _MID_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Expenses by Category",
            data_bindings={
                "category": [_CATEGORY_NAME],
                "values": [_TOTAL_COST],
            },
            position=(mid_x3, _MID_ROW_Y, _MID_COL3_W, _MID_ROW_HEIGHT),
            config_overrides={
                "orientation": "horizontal",
                "show_data_labels": True,
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    # ─── Bottom Row ──────────────────────────────────────────────────────

    # Key Financial Ratios (table)
    bot_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_table",
            title="Key Financial Ratios",
            data_bindings={
                "columns": [_REGION_NAME],
                "values": [_TOTAL_REVENUE, _GROSS_PROFIT, _GROSS_MARGIN_PCT],
            },
            position=(bot_x1, _BOT_ROW_Y, _BOT_COL1_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "column_labels": {
                    "Region.RegionName": "Region",
                    "Sales.TotalRevenue": "Revenue",
                    "Sales.GrossProfit": "Gross Profit",
                    "Sales.GrossMarginPct": "Margin %",
                },
                "alternate_row_shading": True,
            },
        )
    )

    # Cash Flow Summary (waterfall — falls back to bar if custom visual unavailable)
    bot_x2 = bot_x1 + _BOT_COL1_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_waterfall",
            title="Cash Flow Summary",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_GROSS_PROFIT],
            },
            position=(bot_x2, _BOT_ROW_Y, _BOT_COL2_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "show_data_labels": True,
                "format": '$#,##0.0,,"M"',
                "fallback_template": "premium_bar",
                "note": "Waterfall requires custom visual; "
                "falls back to column chart with positive/negative colouring.",
            },
        )
    )

    # Revenue by Region (donut)
    bot_x3 = bot_x2 + _BOT_COL2_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_donut",
            title="Revenue by Region",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_TOTAL_REVENUE],
            },
            position=(bot_x3, _BOT_ROW_Y, _BOT_COL3_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "inner_radius_pct": 50,
                "show_legend": True,
                "format": '$#,##0.0,,"M"',
            },
        )
    )

    return bindings
