"""Canonical combined report assembly (Stage 12B).

Assembles the four existing dashboards (Executive, Financial, Customer, Product)
into ONE coherent multi-page report — ``ExecutiveAnalyticsDemo`` — bound to the
shared ExecutiveRetailPerformanceDashboard semantic model, with a shared
functional navigation rail.

The four pages keep their accepted analytical content; only the navigation and
report packaging change.
"""

from __future__ import annotations

from .customer_config import customer_page_shell, customer_visual_bindings
from .executive_config import executive_page_shell, executive_visual_bindings
from .financial_config import financial_page_shell, financial_visual_bindings
from .navigation import NAV_TOKENS, default_nav_items
from .product_config import product_page_shell, product_visual_bindings
from .registry import DesignTokens
from .report_builder import ReportPage, ReportSpec

CANONICAL_REPORT_NAME = "ExecutiveAnalyticsDemo"
SEMANTIC_MODEL_ID = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
SEMANTIC_MODEL_NAME = "ExecutiveRetailPerformanceDashboard"


def build_canonical_report_spec(
    *,
    report_name: str = CANONICAL_REPORT_NAME,
    semantic_model_id: str = SEMANTIC_MODEL_ID,
    semantic_model_name: str = SEMANTIC_MODEL_NAME,
    subtitle_suffix: str = "",
) -> ReportSpec:
    """Build the canonical four-page ReportSpec.

    ``subtitle_suffix`` is appended to each page subtitle; used by the update
    test to make a visible in-place change while preserving report identity.
    """
    page_defs = [
        (executive_page_shell, executive_visual_bindings),
        (financial_page_shell, financial_visual_bindings),
        (customer_page_shell, customer_visual_bindings),
        (product_page_shell, product_visual_bindings),
    ]

    pages: list[ReportPage] = []
    for shell_fn, bindings_fn in page_defs:
        shell = shell_fn()
        if subtitle_suffix:
            shell = shell.model_copy(update={"subtitle": f"{shell.subtitle}{subtitle_suffix}"})
        pages.append(ReportPage(shell=shell, bindings=bindings_fn()))

    return ReportSpec(
        report_name=report_name,
        semantic_model_id=semantic_model_id,
        semantic_model_name=semantic_model_name,
        pages=pages,
        default_page="executive_overview",
        nav_items=default_nav_items(),
        tokens=DesignTokens(),
        nav_tokens=NAV_TOKENS,
    )
