"""Financial measure definitions for the Power BI semantic model.

Defines DAX measures that derive financial metrics from the existing
ExecutiveRetailPerformanceDashboard semantic model. The existing model
provides: TotalRevenue, GrossProfit, TotalCost, GrossMarginPct on Sales.

For measures that cannot be directly derived (EBITDA, NetProfit, OpEx),
we define synthetic DAX expressions using scaling factors applied to
existing measures. In a production environment these would be proper
calculated measures backed by GL/P&L data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FinancialMeasure:
    """A financial measure definition with DAX expression metadata.

    Attributes:
        name: Display name of the measure.
        entity: Home table in the semantic model.
        property: Source measure/column to derive from.
        dax_expression: Full DAX expression (if custom).
        format_string: DAX format string for display.
        scale: Scaling factor applied to the source measure (1.0 = direct).
        description: Business description of what this measure represents.
        is_synthetic: Whether this measure requires synthetic derivation.
    """

    name: str
    entity: str
    property: str
    dax_expression: str = ""
    format_string: str = '$#,##0.0,,"M"'
    scale: float = 1.0
    description: str = ""
    is_synthetic: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Core P&L measures (derived from existing semantic model)
# ─────────────────────────────────────────────────────────────────────────────

REVENUE = FinancialMeasure(
    name="Revenue",
    entity="Sales",
    property="TotalRevenue",
    dax_expression="[TotalRevenue]",
    format_string='$#,##0.0,,"M"',
    description="Total revenue from all sales channels.",
)

COGS = FinancialMeasure(
    name="COGS",
    entity="Sales",
    property="TotalCost",
    dax_expression="[TotalCost]",
    format_string='$#,##0.0,,"M"',
    description="Cost of goods sold — direct costs attributable to production.",
)

GROSS_PROFIT = FinancialMeasure(
    name="Gross Profit",
    entity="Sales",
    property="GrossProfit",
    dax_expression="[GrossProfit]",
    format_string='$#,##0.0,,"M"',
    description="Revenue minus cost of goods sold.",
)

GROSS_MARGIN = FinancialMeasure(
    name="Gross Margin %",
    entity="Sales",
    property="GrossMarginPct",
    dax_expression="[GrossMarginPct]",
    format_string="0.0%",
    description="Gross profit as a percentage of revenue.",
)

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic P&L measures (scaled from existing data)
# ─────────────────────────────────────────────────────────────────────────────

EBITDA = FinancialMeasure(
    name="EBITDA",
    entity="Sales",
    property="TotalRevenue",
    dax_expression="[TotalRevenue] * 0.216",
    format_string='$#,##0.0,,"M"',
    scale=0.216,
    description="Earnings before interest, taxes, depreciation, and amortisation. "
    "Synthetic: ~21.6% of revenue (typical retail EBITDA margin).",
    is_synthetic=True,
)

NET_PROFIT = FinancialMeasure(
    name="Net Profit",
    entity="Sales",
    property="TotalRevenue",
    dax_expression="[TotalRevenue] * 0.152",
    format_string='$#,##0.0,,"M"',
    scale=0.152,
    description="Bottom-line profit after all expenses, taxes, and interest. "
    "Synthetic: ~15.2% net margin.",
    is_synthetic=True,
)

OPERATING_EXPENSES = FinancialMeasure(
    name="Operating Expenses",
    entity="Sales",
    property="TotalRevenue",
    dax_expression="[TotalRevenue] * 0.270",
    format_string='$#,##0.0,,"M"',
    scale=0.270,
    description="SG&A and other operating expenses. "
    "Synthetic: ~27.0% of revenue (retail industry benchmark).",
    is_synthetic=True,
)

EBIT = FinancialMeasure(
    name="EBIT",
    entity="Sales",
    property="TotalRevenue",
    dax_expression="[GrossProfit] - [TotalRevenue] * 0.270",
    format_string='$#,##0.0,,"M"',
    scale=0.0,  # Computed from GrossProfit - OpEx
    description="Earnings before interest and taxes.",
    is_synthetic=True,
)

NET_MARGIN_PCT = FinancialMeasure(
    name="Net Margin %",
    entity="Sales",
    property="TotalRevenue",
    dax_expression="[TotalRevenue] * 0.152 / [TotalRevenue]",
    format_string="0.0%",
    scale=0.152,
    description="Net profit as a percentage of revenue.",
    is_synthetic=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Aggregate collections
# ─────────────────────────────────────────────────────────────────────────────

# All financial measures in P&L order
FINANCIAL_MEASURES: list[FinancialMeasure] = [
    REVENUE,
    COGS,
    GROSS_PROFIT,
    GROSS_MARGIN,
    OPERATING_EXPENSES,
    EBITDA,
    EBIT,
    NET_PROFIT,
    NET_MARGIN_PCT,
]

# Measures that map directly to existing semantic model fields (no new DAX needed)
DIRECT_MEASURES: list[FinancialMeasure] = [
    m for m in FINANCIAL_MEASURES if not m.is_synthetic
]

# Measures that require synthetic DAX (report-level measures or model updates)
SYNTHETIC_MEASURES: list[FinancialMeasure] = [
    m for m in FINANCIAL_MEASURES if m.is_synthetic
]

# Dict-based representation for backward compatibility with older config code
FINANCIAL_MEASURES_DICT: list[dict[str, Any]] = [
    {
        "name": m.name,
        "entity": m.entity,
        "property": m.property,
        "format": m.format_string,
        **({"scale": m.scale} if m.is_synthetic else {}),
        **({"dax": m.dax_expression} if m.dax_expression else {}),
    }
    for m in FINANCIAL_MEASURES
]
