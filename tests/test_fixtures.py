"""Cross-domain template reuse fixtures.

Proves that the same visual templates can bind to completely different
metric sets without visual source-code changes. This is the Part A
reuse validation required by Stage 08.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.renderer.templates.registry import (
    DesignTokens,
    FieldRef,
    PageShell,
    TemplateRegistry,
    VisualBinding,
)
from pbi_gen.renderer.templates.builder import PageBuilder


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tokens():
    return DesignTokens()


@pytest.fixture
def registry():
    return TemplateRegistry.default()


@pytest.fixture
def minimal_shell():
    return PageShell(
        page_name="test",
        display_name="Test Page",
        title="Test Dashboard",
        subtitle="Cross-domain reuse validation",
        nav_items=[("🏠 Overview", "exec")],
        active_nav="test",
        slicers=[],
    )


def _make_builder(shell, tokens, registry, name="TestReport"):
    return PageBuilder(
        shell=shell,
        tokens=tokens,
        registry=registry,
        semantic_model_id="test-model-id",
        semantic_model_name="TestModel",
        report_name=name,
    )


# ─────────────────────────────────────────────────────────────────────────────
# KPI Template — Two Different Domains
# ─────────────────────────────────────────────────────────────────────────────

class TestKPIReuse:
    """Prove KPI template works with retail revenue AND HR headcount."""

    def test_kpi_binds_to_revenue(self, tokens, registry, minimal_shell):
        """KPI template with Sales.TotalRevenue binding."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_kpi",
            title="Total Revenue",
            data_bindings={
                "measure": [FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)]
            },
            position=(155, 90, 245, 100),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        # Find the KPI visual part
        kpi_parts = [p for p in parts if "kpi_" in p["path"]]
        assert len(kpi_parts) == 1
        # Verify it references the correct entity/property
        payload = json.loads(
            __import__("base64").b64decode(kpi_parts[0]["payload"]).decode()
        )
        query_state = payload["visual"]["query"]["queryState"]
        assert "measure" in query_state
        proj = query_state["measure"]["projections"][0]["field"]
        assert proj["Measure"]["Property"] == "TotalRevenue"

    def test_kpi_binds_to_headcount(self, tokens, registry, minimal_shell):
        """KPI template with HR.Headcount binding — completely different domain."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_kpi",
            title="Total Headcount",
            data_bindings={
                "measure": [FieldRef(entity="HR", property="Headcount", is_measure=True)]
            },
            position=(155, 90, 245, 100),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        kpi_parts = [p for p in parts if "kpi_" in p["path"]]
        assert len(kpi_parts) == 1
        payload = json.loads(
            __import__("base64").b64decode(kpi_parts[0]["payload"]).decode()
        )
        query_state = payload["visual"]["query"]["queryState"]
        proj = query_state["measure"]["projections"][0]["field"]
        assert proj["Measure"]["Property"] == "Headcount"
        assert proj["Measure"]["Expression"]["SourceRef"]["Entity"] == "HR"

    def test_kpi_same_visual_type_both_domains(self, tokens, registry, minimal_shell):
        """Both domain bindings use the same custom visual GUID."""
        builder = _make_builder(minimal_shell, tokens, registry)
        for binding in [
            VisualBinding(
                template_id="premium_kpi",
                title="Revenue",
                data_bindings={"measure": [FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)]},
                position=(155, 90, 245, 100),
            ),
            VisualBinding(
                template_id="premium_kpi",
                title="Headcount",
                data_bindings={"measure": [FieldRef(entity="HR", property="Headcount", is_measure=True)]},
                position=(415, 90, 245, 100),
            ),
        ]:
            builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        kpi_parts = [p for p in parts if "kpi_" in p["path"]]
        assert len(kpi_parts) == 2
        # Both use the same visual type (KPI GUID)
        for kp in kpi_parts:
            payload = json.loads(
                __import__("base64").b64decode(kp["payload"]).decode()
            )
            assert "premiumKPI" in payload["visual"]["visualType"]


# ─────────────────────────────────────────────────────────────────────────────
# Trend Template — Two Different Domains
# ─────────────────────────────────────────────────────────────────────────────

class TestTrendReuse:
    """Prove trend/area chart template works with revenue over time AND customers over time."""

    def test_trend_revenue_over_time(self, tokens, registry, minimal_shell):
        """Trend template with Revenue over Date."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_trend",
            title="Revenue Over Time",
            data_bindings={
                "category": [
                    FieldRef(entity="Date", property="Year", is_measure=False),
                    FieldRef(entity="Date", property="Month", is_measure=False),
                ],
                "values": [
                    FieldRef(entity="Sales", property="TotalRevenue", is_measure=True),
                ],
            },
            position=(155, 200, 635, 240),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        trend_parts = [p for p in parts if "trend_" in p["path"]]
        assert len(trend_parts) == 1
        payload = json.loads(
            __import__("base64").b64decode(trend_parts[0]["payload"]).decode()
        )
        qs = payload["visual"]["query"]["queryState"]
        assert "category" in qs
        assert "values" in qs
        assert qs["values"]["projections"][0]["field"]["Measure"]["Property"] == "TotalRevenue"

    def test_trend_customers_over_time(self, tokens, registry, minimal_shell):
        """Trend template with CustomerCount over Date — different measure, same template."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_trend",
            title="Customer Growth",
            data_bindings={
                "category": [
                    FieldRef(entity="Date", property="Year", is_measure=False),
                    FieldRef(entity="Date", property="Month", is_measure=False),
                ],
                "values": [
                    FieldRef(entity="Customers", property="ActiveCount", is_measure=True),
                ],
            },
            position=(155, 200, 635, 240),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        trend_parts = [p for p in parts if "trend_" in p["path"]]
        assert len(trend_parts) == 1
        payload = json.loads(
            __import__("base64").b64decode(trend_parts[0]["payload"]).decode()
        )
        qs = payload["visual"]["query"]["queryState"]
        assert qs["values"]["projections"][0]["field"]["Measure"]["Property"] == "ActiveCount"
        assert qs["values"]["projections"][0]["field"]["Measure"]["Expression"]["SourceRef"]["Entity"] == "Customers"


# ─────────────────────────────────────────────────────────────────────────────
# Bar Template — Two Different Domains
# ─────────────────────────────────────────────────────────────────────────────

class TestBarReuse:
    """Prove bar chart template works with expenses by category AND sales by product."""

    def test_bar_expenses_by_category(self, tokens, registry, minimal_shell):
        """Bar template with financial expense categories."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_bar",
            title="Expenses by Category",
            data_bindings={
                "category": [FieldRef(entity="Expense", property="CategoryName", is_measure=False)],
                "values": [FieldRef(entity="Expense", property="Amount", is_measure=True)],
            },
            position=(155, 460, 365, 240),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        bar_parts = [p for p in parts if "bar_" in p["path"]]
        assert len(bar_parts) == 1
        payload = json.loads(
            __import__("base64").b64decode(bar_parts[0]["payload"]).decode()
        )
        qs = payload["visual"]["query"]["queryState"]
        assert qs["Category"]["projections"][0]["field"]["Column"]["Property"] == "CategoryName"
        assert qs["Y"]["projections"][0]["field"]["Measure"]["Property"] == "Amount"

    def test_bar_sales_by_product(self, tokens, registry, minimal_shell):
        """Bar template with retail product categories."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_bar",
            title="Sales by Product",
            data_bindings={
                "category": [FieldRef(entity="Product", property="ProductName", is_measure=False)],
                "values": [FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)],
            },
            position=(155, 460, 365, 240),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        bar_parts = [p for p in parts if "bar_" in p["path"]]
        assert len(bar_parts) == 1
        payload = json.loads(
            __import__("base64").b64decode(bar_parts[0]["payload"]).decode()
        )
        qs = payload["visual"]["query"]["queryState"]
        assert qs["Category"]["projections"][0]["field"]["Column"]["Property"] == "ProductName"
        assert qs["Y"]["projections"][0]["field"]["Measure"]["Property"] == "TotalRevenue"


# ─────────────────────────────────────────────────────────────────────────────
# Table Template — Two Different Domains
# ─────────────────────────────────────────────────────────────────────────────

class TestTableReuse:
    """Prove table template works with financial ratios AND product performance."""

    def test_table_financial_ratios(self, tokens, registry, minimal_shell):
        """Table template for financial ratio display."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_table",
            title="Key Financial Ratios",
            data_bindings={
                "columns": [FieldRef(entity="Finance", property="RatioName", is_measure=False)],
                "values": [
                    FieldRef(entity="Finance", property="CurrentValue", is_measure=True),
                    FieldRef(entity="Finance", property="PriorYear", is_measure=True),
                ],
            },
            position=(155, 460, 375, 260),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        table_parts = [p for p in parts if "table_" in p["path"]]
        assert len(table_parts) == 1

    def test_table_product_performance(self, tokens, registry, minimal_shell):
        """Table template for product performance — different domain."""
        builder = _make_builder(minimal_shell, tokens, registry)
        binding = VisualBinding(
            template_id="premium_table",
            title="Product Performance",
            data_bindings={
                "columns": [FieldRef(entity="Product", property="ProductName", is_measure=False)],
                "values": [
                    FieldRef(entity="Sales", property="TotalRevenue", is_measure=True),
                    FieldRef(entity="Sales", property="GrossProfit", is_measure=True),
                ],
            },
            position=(155, 460, 375, 260),
        )
        builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        table_parts = [p for p in parts if "table_" in p["path"]]
        assert len(table_parts) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Full Page Reuse — Financial vs Executive
# ─────────────────────────────────────────────────────────────────────────────

class TestFullPageReuse:
    """Prove that a full Financial page and a full Executive page both build
    successfully from the same template system with different configurations."""

    def test_financial_page_builds(self, tokens, registry):
        """Financial page generates complete PBIR parts."""
        from pbi_gen.renderer.templates.financial_config import (
            financial_page_shell,
            financial_visual_bindings,
        )
        builder = _make_builder(financial_page_shell(), tokens, registry, "FinancialTest")
        for binding in financial_visual_bindings():
            builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        # Should have platform + definition + report + theme + pages + visuals + custom visuals
        assert len(parts) >= 25
        # Verify structural integrity
        paths = [p["path"] for p in parts]
        assert ".platform" in paths
        assert "definition.pbir" in paths
        assert "definition/report.json" in paths

    def test_executive_page_builds(self, tokens, registry):
        """Executive page generates complete PBIR parts from same system."""
        from pbi_gen.renderer.templates.executive_config import (
            executive_page_shell,
            executive_visual_bindings,
        )
        builder = _make_builder(executive_page_shell(), tokens, registry, "ExecutiveTest")
        for binding in executive_visual_bindings():
            builder.add_visual(binding)
        parts = builder.build_pbir_parts()
        assert len(parts) >= 20
        paths = [p["path"] for p in parts]
        assert ".platform" in paths
        assert "definition.pbir" in paths
        assert "definition/report.json" in paths

    def test_both_use_same_design_tokens(self, tokens, registry):
        """Both pages share the exact same design tokens (no per-page token copies)."""
        from pbi_gen.renderer.templates.financial_config import financial_page_shell, financial_visual_bindings
        from pbi_gen.renderer.templates.executive_config import executive_page_shell, executive_visual_bindings

        builder_fin = _make_builder(financial_page_shell(), tokens, registry, "Fin")
        builder_exec = _make_builder(executive_page_shell(), tokens, registry, "Exec")

        for b in financial_visual_bindings():
            builder_fin.add_visual(b)
        for b in executive_visual_bindings():
            builder_exec.add_visual(b)

        parts_fin = builder_fin.build_pbir_parts()
        parts_exec = builder_exec.build_pbir_parts()

        # Both generate the same theme file
        theme_fin = next(p for p in parts_fin if "ExecutiveDark" in p["path"])
        theme_exec = next(p for p in parts_exec if "ExecutiveDark" in p["path"])
        assert theme_fin["payload"] == theme_exec["payload"]

    def test_financial_uses_different_measures(self, tokens, registry):
        """Financial page binds to different measures than Executive."""
        from pbi_gen.renderer.templates.financial_config import financial_visual_bindings
        from pbi_gen.renderer.templates.executive_config import executive_visual_bindings

        fin_titles = {b.title for b in financial_visual_bindings()}
        exec_titles = {b.title for b in executive_visual_bindings()}

        # At least some overlap (both have Revenue) but not identical
        assert fin_titles != exec_titles
        # Financial has finance-specific visuals
        assert "EBITDA" in fin_titles or "Net Profit" in fin_titles
        assert "Cash Flow Summary" in fin_titles

    def test_custom_visual_guids_shared(self, tokens, registry):
        """Both pages share the same custom visual registry (no duplication)."""
        from pbi_gen.renderer.templates.financial_config import financial_page_shell, financial_visual_bindings
        from pbi_gen.renderer.templates.executive_config import executive_page_shell, executive_visual_bindings

        builder_fin = _make_builder(financial_page_shell(), tokens, registry, "Fin")
        builder_exec = _make_builder(executive_page_shell(), tokens, registry, "Exec")

        for b in financial_visual_bindings():
            builder_fin.add_visual(b)
        for b in executive_visual_bindings():
            builder_exec.add_visual(b)

        # Both pull from the same registry
        fin_cvs = set(builder_fin.custom_visual_packages())
        exec_cvs = set(builder_exec.custom_visual_packages())

        # Both use premiumKPI and premiumAreaChart
        assert "premiumKPI0E21B11FE691418A84E3F774DD6461A5" in fin_cvs
        assert "premiumKPI0E21B11FE691418A84E3F774DD6461A5" in exec_cvs


# ─────────────────────────────────────────────────────────────────────────────
# Template Registry Integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryIntegrity:
    """Verify template registry structure and consistency."""

    def test_all_templates_have_data_roles(self, registry):
        """Every registered template has at least one data role."""
        for tid in registry.list_templates():
            template = registry.get(tid)
            assert len(template.data_roles) > 0, f"Template {tid} has no data roles"

    def test_custom_visuals_have_guids(self, registry):
        """Custom visual templates reference valid GUIDs."""
        guids = registry.custom_visual_guids()
        assert len(guids) >= 3  # KPI, AreaChart, Waterfall at minimum

    def test_templates_have_reasonable_dimensions(self, registry):
        """Default dimensions are within page bounds."""
        for tid in registry.list_templates():
            template = registry.get(tid)
            assert 50 <= template.default_width <= 1280
            assert 50 <= template.default_height <= 720

    def test_design_tokens_produce_valid_theme(self, tokens):
        """Design tokens generate a valid Power BI theme structure."""
        theme = tokens.to_pbi_theme()
        assert theme["name"] == "ExecutiveDark"
        assert len(theme["dataColors"]) == 8
        assert theme["background"] == "#0f1623"
        assert "visualStyles" in theme
        assert "page" in theme["visualStyles"]

    def test_no_retail_specific_constants_in_registry(self, registry):
        """Registry does not contain retail-specific field names."""
        import inspect
        source = inspect.getsource(registry.__class__)
        # Should not hardcode specific business entity names in the registry itself
        assert "Electronics" not in source
        assert "Clothing" not in source
        assert "grocery" not in source.lower()
