"""Financial Performance page configuration — v2 (aesthetic match to exec overview).

Restructured layout to match Executive Overview proportions:
- 4 KPI cards (not 5)
- 2-column middle row (trend 57% + donut 43%)
- 3-column bottom row with equal widths, all dark-themed

Uses ExecutiveRetailPerformanceDashboard semantic model.
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
# Layout constants — matching exec overview proportions
# ─────────────────────────────────────────────────────────────────────────────

_PAGE_WIDTH = 1280
_PAGE_HEIGHT = 720
_NAV_RAIL_WIDTH = 140
_CONTENT_LEFT = 155

_CONTENT_WIDTH = _PAGE_WIDTH - _CONTENT_LEFT - 15  # ~1110px

# KPI row — 4 cards like exec overview
_KPI_ROW_Y = 90
_KPI_HEIGHT = 100
_KPI_COUNT = 4
_KPI_GAP = 14
_KPI_WIDTH = int((_CONTENT_WIDTH - (_KPI_COUNT - 1) * _KPI_GAP) / _KPI_COUNT)  # ~265

# Middle row — 2 panels (57% / 43%) like exec overview
_MID_ROW_Y = 200
_MID_ROW_HEIGHT = 240
_MID_GAP = 10
_MID_COL1_W = int(_CONTENT_WIDTH * 0.57)  # ~633 (trend chart)
_MID_COL2_W = _CONTENT_WIDTH - _MID_COL1_W - _MID_GAP  # ~467 (donut)

# Bottom row — 3 equal panels like exec overview
_BOT_ROW_Y = _MID_ROW_Y + _MID_ROW_HEIGHT + 10
_BOT_ROW_HEIGHT = 240
_BOT_GAP = 10
_BOT_COL_W = int((_CONTENT_WIDTH - 2 * _BOT_GAP) / 3)  # ~363

# Navigation items
_NAV_ITEMS: list[tuple[str, str]] = [
    ("🏠 Overview", "executive_overview"),
    ("💰 Financial", "financial_performance"),
    ("👥 Customers", "sales_detail"),
    ("📦 Products", "regional_breakdown"),
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
    """Visual bindings for Financial Performance — v2 layout.

    Matches exec overview structure:
    - 4 KPI cards
    - 2-column middle row (trend + donut)
    - 3-column bottom row (bar + waterfall + bar)
    """
    bindings: list[VisualBinding] = []

    # ─── KPI Row (4 cards) ───────────────────────────────────────────────
    kpi_definitions: list[tuple[str, FieldRef]] = [
        ("Total Revenue", _TOTAL_REVENUE),
        ("Gross Profit", _GROSS_PROFIT),
        ("Total Cost", _TOTAL_COST),
        ("Gross Margin %", _GROSS_MARGIN_PCT),
    ]

    for i, (title, measure) in enumerate(kpi_definitions):
        x = _CONTENT_LEFT + i * (_KPI_WIDTH + _KPI_GAP)
        bindings.append(
            VisualBinding(
                template_id="premium_kpi",
                title="",  # KPI visual renders its own label internally
                data_bindings={"measure": [measure]},
                position=(x, _KPI_ROW_Y, _KPI_WIDTH, _KPI_HEIGHT),
                config_overrides={"kpi_index": i},
            )
        )

    # ─── Middle Row (2 panels) ───────────────────────────────────────────

    # Revenue Over Time (area/line trend) — wide hero chart
    mid_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_trend",
            title="Revenue & Cost Trend",
            data_bindings={
                "category": [_DATE_YEAR, _DATE_MONTH],
                "values": [_TOTAL_REVENUE, _TOTAL_COST],
            },
            position=(mid_x1, _MID_ROW_Y, _MID_COL1_W, _MID_ROW_HEIGHT),
            config_overrides={},
        )
    )

    # Profitability by Region (donut)
    mid_x2 = mid_x1 + _MID_COL1_W + _MID_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_donut",
            title="Profitability by Region",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_GROSS_PROFIT],
            },
            position=(mid_x2, _MID_ROW_Y, _MID_COL2_W, _MID_ROW_HEIGHT),
            config_overrides={"show_center_kpi": True},
        )
    )

    # Donut center KPI overlay (uses cardVisual title, not premiumKPI)
    donut_kpi_x = mid_x2 + int(_MID_COL2_W * 0.25)
    donut_kpi_y = _MID_ROW_Y + int(_MID_ROW_HEIGHT * 0.40)
    bindings.append(
        VisualBinding(
            template_id="donut_center_kpi",
            title="£1.0M",
            data_bindings={"measure": [_GROSS_PROFIT]},
            position=(donut_kpi_x, donut_kpi_y, 100, 44),
            config_overrides={
                "subtitle": "Gross Profit",
                "show_background": False,
                "show_border": False,
                "title_bold": True,
                "title_font_size": 14,
                "title_color": "#ffffff",
            },
        )
    )

    # ─── Bottom Row (3 equal panels) ─────────────────────────────────────

    # Revenue by Category (bar chart)
    bot_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Revenue by Category",
            data_bindings={
                "category": [_CATEGORY_NAME],
                "values": [_TOTAL_REVENUE],
            },
            position=(bot_x1, _BOT_ROW_Y, _BOT_COL_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "show_data_labels": True,
                "label_display_units": 1000000,
                "label_precision": 2,
            },
        )
    )

    # Expense Breakdown (waterfall)
    bot_x2 = bot_x1 + _BOT_COL_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_waterfall",
            title="Cost Breakdown",
            data_bindings={
                "category": [_CATEGORY_NAME],
                "values": [_TOTAL_COST],
            },
            position=(bot_x2, _BOT_ROW_Y, _BOT_COL_W, _BOT_ROW_HEIGHT),
            config_overrides={},
        )
    )

    # Gross Profit by Region (bar chart)
    bot_x3 = bot_x2 + _BOT_COL_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Gross Profit by Region",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_GROSS_PROFIT],
            },
            position=(bot_x3, _BOT_ROW_Y, _BOT_COL_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "show_data_labels": True,
                "label_display_units": 1000000,
                "label_precision": 2,
            },
        )
    )

    return bindings
