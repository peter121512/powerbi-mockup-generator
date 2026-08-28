"""Product Performance page configuration (Stage 12B).

Extracted from ``scripts/_deploy_product_v1.py`` into a reusable config that
matches the Executive/Financial/Customer config shape (shell + bindings), so
the Product page can be assembled into the canonical multi-page report.

Uses the shared ExecutiveRetailPerformanceDashboard semantic model.
Analytical content is unchanged from Stage 11/12A.
"""

from __future__ import annotations

from .composites import make_donut_composite_bindings
from .registry import FieldRef, PageShell, VisualBinding

# ── Field references ─────────────────────────────────────────────────────────
_TOTAL_REVENUE = FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)
_GROSS_PROFIT = FieldRef(entity="Sales", property="GrossProfit", is_measure=True)
_GROSS_MARGIN_PCT = FieldRef(entity="Sales", property="GrossMarginPct", is_measure=True)
_ACTIVE_PRODUCTS = FieldRef(entity="Sales", property="ActiveProducts", is_measure=True)

_CATEGORY_NAME = FieldRef(entity="Product", property="CategoryName")
_PRODUCT_NAME = FieldRef(entity="Product", property="ProductName")
_SUBCATEGORY_NAME = FieldRef(entity="Product", property="SubcategoryName")
_DATE_YEAR = FieldRef(entity="Date", property="Year")
_DATE_MONTH = FieldRef(entity="Date", property="Month")

# ── Layout constants (match Stage 12A product layout) ─────────────────────────
_PAGE_WIDTH = 1280
_PAGE_HEIGHT = 720
_CX = 155
_CW = 1115
_GUTTER = 10
_KPI_W = (_CW - 3 * _GUTTER) // 4

# Nav items are supplied by the report-level navigation system in Stage 12B;
# this list is retained for standalone use / backward compatibility.
_NAV_ITEMS: list[tuple[str, str]] = [
    ("Overview", "executive_overview"),
    ("Financial", "financial_performance"),
    ("Customers", "customer_performance"),
    ("Products", "product_performance"),
]


def product_page_shell() -> PageShell:
    """Configuration for the Product Performance page shell."""
    return PageShell(
        page_name="product_performance",
        display_name="Product Performance",
        title="Product Performance",
        subtitle="Sales · Profitability · Product Mix",
        nav_items=_NAV_ITEMS,
        active_nav="product_performance",
        slicers=[_DATE_YEAR, _CATEGORY_NAME],
        width=_PAGE_WIDTH,
        height=_PAGE_HEIGHT,
    )


def product_visual_bindings() -> list[VisualBinding]:
    """Visual bindings for Product Performance (unchanged analytical content)."""
    bindings: list[VisualBinding] = []

    # ── KPI row (no container titles; cards render their own labels) ──
    kpi_defs: list[FieldRef] = [
        _TOTAL_REVENUE, _GROSS_PROFIT, _GROSS_MARGIN_PCT, _ACTIVE_PRODUCTS,
    ]
    for i, measure in enumerate(kpi_defs):
        x = _CX + i * (_KPI_W + _GUTTER)
        bindings.append(
            VisualBinding(
                template_id="premium_kpi",
                title="",
                data_bindings={"measure": [measure]},
                position=(x, 90, _KPI_W, 75),
            )
        )

    # ── Hero: Sales Trend (grouped by Year + Month) ──
    bindings.append(
        VisualBinding(
            template_id="premium_trend",
            title="Sales Trend",
            data_bindings={
                "category": [_DATE_YEAR, _DATE_MONTH],
                "values": [_TOTAL_REVENUE, _GROSS_PROFIT],
            },
            position=(_CX, 175, 635, 240),
        )
    )

    # ── Product Mix donut with self-centring centre KPI ──
    (donut_binding,) = make_donut_composite_bindings(
        donut_position=(_CX + 635 + _GUTTER, 175, 470, 240),
        donut_title="Product Mix by Category",
        donut_category=_CATEGORY_NAME,
        donut_measure=_TOTAL_REVENUE,
        center_title="128",
        center_measure=_ACTIVE_PRODUCTS,
        center_subtitle="Products",
    )
    bindings.append(donut_binding)

    # ── Bottom row: three horizontal bars ──
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Top Products by Sales",
            data_bindings={"category": [_PRODUCT_NAME], "values": [_TOTAL_REVENUE]},
            position=(_CX, 425, 365, 240),
        )
    )
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Gross Margin by Category",
            data_bindings={"category": [_CATEGORY_NAME], "values": [_GROSS_MARGIN_PCT]},
            position=(_CX + 365 + _GUTTER, 425, 365, 240),
        )
    )
    bindings.append(
        VisualBinding(
            template_id="premium_bar",
            title="Sales by Subcategory",
            data_bindings={"category": [_SUBCATEGORY_NAME], "values": [_TOTAL_REVENUE]},
            position=(_CX + 2 * (365 + _GUTTER), 425, 365, 240),
        )
    )

    return bindings
