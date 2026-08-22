"""Customer Performance page configuration.

Uses reusable premium templates with the existing semantic model.
Measures are proxied with title overrides since no real customer data exists.

Layout matches Executive Overview proportions:
- 4 KPI cards (no external titles)
- 2-column middle row (hero trend 57% + donut 43%)
- 3-column bottom row (bar + bar + insights)
"""

from __future__ import annotations

from .registry import FieldRef, PageShell, VisualBinding

# ─────────────────────────────────────────────────────────────────────────────
# Semantic model field references (proxied for customer metrics)
# ─────────────────────────────────────────────────────────────────────────────

_TOTAL_REVENUE = FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)
_GROSS_PROFIT = FieldRef(entity="Sales", property="GrossProfit", is_measure=True)
_TOTAL_COST = FieldRef(entity="Sales", property="TotalCost", is_measure=True)
_GROSS_MARGIN_PCT = FieldRef(entity="Sales", property="GrossMarginPct", is_measure=True)

# Customer measures (added to semantic model)
_ACTIVE_CUSTOMERS = FieldRef(entity="Sales", property="ActiveCustomers", is_measure=True)
_NEW_CUSTOMERS = FieldRef(entity="Sales", property="NewCustomers", is_measure=True)
_RETENTION_RATE = FieldRef(entity="Sales", property="RetentionRate", is_measure=True)
_CUSTOMER_LTV = FieldRef(entity="Sales", property="CustomerLTV", is_measure=True)
_CUSTOMER_GROWTH = FieldRef(entity="Sales", property="CustomerGrowth", is_measure=True)
_CUSTOMER_RETENTION = FieldRef(entity="Sales", property="CustomerRetention", is_measure=True)

# Dimensions
_REGION_NAME = FieldRef(entity="Region", property="RegionName")
_CATEGORY_NAME = FieldRef(entity="Product", property="CategoryName")
_DATE_YEAR = FieldRef(entity="Date", property="Year")
_DATE_MONTH = FieldRef(entity="Date", property="Month")

# ─────────────────────────────────────────────────────────────────────────────
# Layout constants
# ─────────────────────────────────────────────────────────────────────────────

_PAGE_WIDTH = 1280
_PAGE_HEIGHT = 720
_CONTENT_LEFT = 155
_CONTENT_WIDTH = _PAGE_WIDTH - _CONTENT_LEFT - 15  # ~1110

# KPI row — 4 cards
_KPI_ROW_Y = 90
_KPI_HEIGHT = 100
_KPI_COUNT = 4
_KPI_GAP = 14
_KPI_WIDTH = int((_CONTENT_WIDTH - (_KPI_COUNT - 1) * _KPI_GAP) / _KPI_COUNT)

# Middle row — 2 panels (57% / 43%)
_MID_ROW_Y = 200
_MID_ROW_HEIGHT = 240
_MID_GAP = 10
_MID_COL1_W = int(_CONTENT_WIDTH * 0.57)
_MID_COL2_W = _CONTENT_WIDTH - _MID_COL1_W - _MID_GAP

# Bottom row — 3 equal panels
_BOT_ROW_Y = _MID_ROW_Y + _MID_ROW_HEIGHT + 10
_BOT_ROW_HEIGHT = 240
_BOT_GAP = 10
_BOT_COL_W = int((_CONTENT_WIDTH - 2 * _BOT_GAP) / 3)

# Navigation
_NAV_ITEMS: list[tuple[str, str]] = [
    ("🏠 Overview", "executive_overview"),
    ("💰 Financial", "financial_performance"),
    ("👥 Customers", "customer_performance"),
    ("📦 Products", "product_performance"),
]


def customer_page_shell() -> PageShell:
    return PageShell(
        page_name="customer_performance",
        display_name="Customer Performance",
        title="Customer Performance",
        subtitle="Growth · Retention · Segmentation · Value",
        nav_items=_NAV_ITEMS,
        active_nav="customer_performance",
        slicers=[_DATE_YEAR],
        width=_PAGE_WIDTH,
        height=_PAGE_HEIGHT,
    )


def customer_visual_bindings() -> list[VisualBinding]:
    bindings: list[VisualBinding] = []

    # ─── KPI Row (4 cards) ───────────────────────────────────────────────
    kpi_definitions: list[tuple[str, FieldRef]] = [
        ("Active Customers", _ACTIVE_CUSTOMERS),
        ("New Customers", _NEW_CUSTOMERS),
        ("Retention Rate", _RETENTION_RATE),
        ("Customer LTV", _CUSTOMER_LTV),
    ]

    for i, (title, measure) in enumerate(kpi_definitions):
        x = _CONTENT_LEFT + i * (_KPI_WIDTH + _KPI_GAP)
        bindings.append(
            VisualBinding(
                template_id="premium_kpi",
                title="",
                data_bindings={"measure": [measure]},
                position=(x, _KPI_ROW_Y, _KPI_WIDTH, _KPI_HEIGHT),
                config_overrides={"kpi_index": i},
            )
        )

    # ─── Middle Row ──────────────────────────────────────────────────────

    # Customer Growth Trend (hero area chart)
    mid_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_trend",
            title="Customer Growth & Retention",
            data_bindings={
                "category": [_DATE_YEAR, _DATE_MONTH],
                "values": [_CUSTOMER_GROWTH, _CUSTOMER_RETENTION],
            },
            position=(mid_x1, _MID_ROW_Y, _MID_COL1_W, _MID_ROW_HEIGHT),
            config_overrides={},
        )
    )

    # Customer Segments (donut)
    mid_x2 = mid_x1 + _MID_COL1_W + _MID_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_donut",
            title="Customers by Segment",
            data_bindings={
                "category": [_CATEGORY_NAME],
                "values": [_ACTIVE_CUSTOMERS],
            },
            position=(mid_x2, _MID_ROW_Y, _MID_COL2_W, _MID_ROW_HEIGHT),
            config_overrides={},
        )
    )

    # Donut center KPI
    donut_kpi_x = mid_x2 + int(_MID_COL2_W * 0.22)
    donut_kpi_y = _MID_ROW_Y + int(_MID_ROW_HEIGHT * 0.38)
    bindings.append(
        VisualBinding(
            template_id="donut_center_kpi",
            title="24.4K",
            data_bindings={"measure": [_ACTIVE_CUSTOMERS]},
            position=(donut_kpi_x, donut_kpi_y, 100, 44),
            config_overrides={
                "subtitle": "Active Customers",
                "show_background": False,
                "show_border": False,
                "title_bold": True,
                "title_font_size": 14,
                "title_color": "#ffffff",
            },
        )
    )

    # ─── Bottom Row (3 panels) ───────────────────────────────────────────

    # Acquisition by Channel (bar chart)
    bot_x1 = _CONTENT_LEFT
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Acquisition by Channel",
            data_bindings={
                "category": [_CATEGORY_NAME],
                "values": [_NEW_CUSTOMERS],
            },
            position=(bot_x1, _BOT_ROW_Y, _BOT_COL_W, _BOT_ROW_HEIGHT),
            config_overrides={
                "show_data_labels": True,
                "label_display_units": 1000000,
                "label_precision": 2,
            },
        )
    )

    # Customer Value by Region (column chart)
    bot_x2 = bot_x1 + _BOT_COL_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_column",
            title="Customer Value by Region",
            data_bindings={
                "category": [_REGION_NAME],
                "values": [_ACTIVE_CUSTOMERS, _NEW_CUSTOMERS],
            },
            position=(bot_x2, _BOT_ROW_Y, _BOT_COL_W, _BOT_ROW_HEIGHT),
            config_overrides={"show_legend": True},
        )
    )

    # Customer Insights (custom visual)
    bot_x3 = bot_x2 + _BOT_COL_W + _BOT_GAP
    bindings.append(
        VisualBinding(
            template_id="premium_insights",
            title="",
            data_bindings={"measure": [_ACTIVE_CUSTOMERS]},
            position=(bot_x3, _BOT_ROW_Y, _BOT_COL_W, _BOT_ROW_HEIGHT),
            config_overrides={},
        )
    )

    return bindings
