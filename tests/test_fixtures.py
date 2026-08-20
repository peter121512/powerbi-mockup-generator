"""Fixture tests for enterprise design system generality.

Verifies that the design system and renderer apply without retail-specific assumptions
to materially different dashboard shapes (finance, SaaS/operations).
"""

import json
from pathlib import Path

import pytest

from pbi_gen.models.dashboard_spec import (
    DashboardSpec,
    DashboardIntent,
    PageSpec,
    PageRole,
    PageLayout,
    VisualSpec,
    VisualType,
    VisualPosition,
    FieldRef,
    FilterSpec,
    FilterType,
    TableSpec,
    ColumnSpec,
    MeasureSpec,
    RevisionMetadata,
    ThemeSpec,
)
from pbi_gen.renderer import render_powerbi_project
from pbi_gen.renderer.design_system import EnterpriseDesignSystem


def _make_finance_spec() -> DashboardSpec:
    """Finance/variance dashboard fixture — no retail concepts."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="CFO Financial Variance",
            business_purpose="Monthly P&L variance analysis for CFO",
        ),
        revision=RevisionMetadata(spec_id="fin-001", version=1),
        pages=[
            PageSpec(
                id="page-pnl",
                title="P&L Overview",
                role=PageRole.EXECUTIVE_OVERVIEW,
                layout=PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8),
                visuals=[
                    VisualSpec(
                        id="v-rev", visual_type=VisualType.CARD, title="Revenue",
                        value_fields=[FieldRef(table="Finance", measure="Revenue")],
                        position=VisualPosition(x=0, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-cogs", visual_type=VisualType.CARD, title="COGS",
                        value_fields=[FieldRef(table="Finance", measure="COGS")],
                        position=VisualPosition(x=3, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-ebitda", visual_type=VisualType.CARD, title="EBITDA",
                        value_fields=[FieldRef(table="Finance", measure="EBITDA")],
                        position=VisualPosition(x=6, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-variance", visual_type=VisualType.CLUSTERED_BAR, title="Budget vs Actual",
                        category_fields=[FieldRef(table="Finance", column="Department")],
                        value_fields=[FieldRef(table="Finance", measure="Variance")],
                        position=VisualPosition(x=0, y=2, width=6, height=4),
                    ),
                    VisualSpec(
                        id="v-trend", visual_type=VisualType.LINE_CHART, title="Monthly Revenue Trend",
                        category_fields=[FieldRef(table="Period", column="Month")],
                        value_fields=[FieldRef(table="Finance", measure="Revenue")],
                        position=VisualPosition(x=6, y=2, width=6, height=4),
                    ),
                    VisualSpec(
                        id="v-table", visual_type=VisualType.TABLE, title="Department Detail",
                        category_fields=[FieldRef(table="Finance", column="Department")],
                        value_fields=[
                            FieldRef(table="Finance", measure="Revenue"),
                            FieldRef(table="Finance", measure="COGS"),
                            FieldRef(table="Finance", measure="EBITDA"),
                        ],
                        position=VisualPosition(x=0, y=6, width=12, height=2),
                    ),
                ],
                filters=[
                    FilterSpec(id="f-period", filter_type=FilterType.SLICER, field=FieldRef(table="Period", column="Quarter")),
                ],
            ),
        ],
        tables=[
            TableSpec(name="Finance", columns=[
                ColumnSpec(name="Department", data_type="STRING"),
                ColumnSpec(name="Amount", data_type="REAL"),
            ], row_count_hint=100),
            TableSpec(name="Period", columns=[
                ColumnSpec(name="Month", data_type="STRING"),
                ColumnSpec(name="Quarter", data_type="STRING"),
            ], row_count_hint=12),
        ],
        measures=[
            MeasureSpec(name="Revenue", expression="SUM(Finance[Amount])", table="Finance"),
            MeasureSpec(name="COGS", expression="SUM(Finance[Amount])*0.6", table="Finance"),
            MeasureSpec(name="EBITDA", expression="SUM(Finance[Amount])*0.25", table="Finance"),
            MeasureSpec(name="Variance", expression="SUM(Finance[Amount])*0.1", table="Finance"),
        ],
        theme=ThemeSpec(),
    )


def _make_saas_spec() -> DashboardSpec:
    """SaaS/operations dashboard fixture — no retail concepts."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="SaaS Operations Dashboard",
            business_purpose="Product usage, churn, and ARR tracking for VP Engineering",
        ),
        revision=RevisionMetadata(spec_id="saas-001", version=1),
        pages=[
            PageSpec(
                id="page-ops",
                title="Operations Overview",
                role=PageRole.EXECUTIVE_OVERVIEW,
                layout=PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8),
                visuals=[
                    VisualSpec(
                        id="v-arr", visual_type=VisualType.CARD, title="ARR",
                        value_fields=[FieldRef(table="Metrics", measure="ARR")],
                        position=VisualPosition(x=0, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-churn", visual_type=VisualType.CARD, title="Churn Rate",
                        value_fields=[FieldRef(table="Metrics", measure="ChurnRate")],
                        position=VisualPosition(x=3, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-nps", visual_type=VisualType.CARD, title="NPS",
                        value_fields=[FieldRef(table="Metrics", measure="NPS")],
                        position=VisualPosition(x=6, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-dau", visual_type=VisualType.CARD, title="DAU",
                        value_fields=[FieldRef(table="Metrics", measure="DAU")],
                        position=VisualPosition(x=9, y=0, width=3, height=2),
                    ),
                    VisualSpec(
                        id="v-usage", visual_type=VisualType.LINE_CHART, title="Daily Active Users",
                        category_fields=[FieldRef(table="TimeDim", column="Date")],
                        value_fields=[FieldRef(table="Metrics", measure="DAU")],
                        position=VisualPosition(x=0, y=2, width=8, height=3),
                    ),
                    VisualSpec(
                        id="v-segments", visual_type=VisualType.DONUT_CHART, title="Revenue by Plan",
                        category_fields=[FieldRef(table="Customers", column="Plan")],
                        value_fields=[FieldRef(table="Metrics", measure="ARR")],
                        position=VisualPosition(x=8, y=2, width=4, height=3),
                    ),
                    VisualSpec(
                        id="v-funnel", visual_type=VisualType.FUNNEL, title="Onboarding Funnel",
                        category_fields=[FieldRef(table="Funnel", column="Stage")],
                        value_fields=[FieldRef(table="Funnel", measure="Count")],
                        position=VisualPosition(x=0, y=5, width=6, height=3),
                    ),
                    VisualSpec(
                        id="v-incidents", visual_type=VisualType.TABLE, title="Recent Incidents",
                        category_fields=[
                            FieldRef(table="Incidents", column="Date"),
                            FieldRef(table="Incidents", column="Service"),
                            FieldRef(table="Incidents", column="Severity"),
                        ],
                        value_fields=[FieldRef(table="Incidents", measure="Duration")],
                        position=VisualPosition(x=6, y=5, width=6, height=3),
                    ),
                ],
                filters=[
                    FilterSpec(id="f-plan", filter_type=FilterType.SLICER, field=FieldRef(table="Customers", column="Plan")),
                    FilterSpec(id="f-region", filter_type=FilterType.SLICER, field=FieldRef(table="Customers", column="Region")),
                ],
            ),
        ],
        tables=[
            TableSpec(name="Metrics", columns=[ColumnSpec(name="Value", data_type="REAL")], row_count_hint=365),
            TableSpec(name="TimeDim", columns=[ColumnSpec(name="Date", data_type="DATETIME")], row_count_hint=365),
            TableSpec(name="Customers", columns=[
                ColumnSpec(name="Plan", data_type="STRING"),
                ColumnSpec(name="Region", data_type="STRING"),
            ], row_count_hint=500),
            TableSpec(name="Funnel", columns=[ColumnSpec(name="Stage", data_type="STRING")], row_count_hint=5),
            TableSpec(name="Incidents", columns=[
                ColumnSpec(name="Date", data_type="DATETIME"),
                ColumnSpec(name="Service", data_type="STRING"),
                ColumnSpec(name="Severity", data_type="STRING"),
            ], row_count_hint=50),
        ],
        measures=[
            MeasureSpec(name="ARR", expression="SUM(Metrics[Value])", table="Metrics"),
            MeasureSpec(name="ChurnRate", expression="0.035", table="Metrics"),
            MeasureSpec(name="NPS", expression="72", table="Metrics"),
            MeasureSpec(name="DAU", expression="COUNTROWS(Metrics)", table="Metrics"),
            MeasureSpec(name="Count", expression="SUM(Funnel[Stage])", table="Funnel"),
            MeasureSpec(name="Duration", expression="SUM(Incidents[Severity])", table="Incidents"),
        ],
        theme=ThemeSpec(),
    )


class TestFinanceFixture:
    """Finance dashboard renders correctly with enterprise design system."""

    def test_finance_renders_successfully(self, tmp_path):
        spec = _make_finance_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        assert result.outcome.value == "success"

    def test_finance_all_visuals_present(self, tmp_path):
        spec = _make_finance_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        assert result.fidelity.rendered_visuals == 6

    def test_finance_slicer_within_bounds(self, tmp_path):
        spec = _make_finance_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        # Check slicer visual exists and is within canvas
        import json
        page_dir = Path(result.output_path) / "CFOFinancialVariance.Report" / "definition" / "pages" / "page-pnl"
        slicers = list((page_dir / "visuals").glob("f-*"))
        assert len(slicers) == 1
        slicer_json = json.loads((slicers[0] / "visual.json").read_text())
        pos = slicer_json["position"]
        assert pos["x"] >= 0
        assert pos["y"] >= 0
        assert pos["x"] + pos["width"] <= 1280
        assert pos["y"] + pos["height"] <= 720

    def test_finance_design_system_applies(self):
        spec = _make_finance_spec()
        ds = EnterpriseDesignSystem.from_theme(spec.theme)
        assert ds.colours.primary_series_color
        assert ds.typography.kpi_value > 0
        assert ds.spacing.page_margin > 0


class TestSaaSFixture:
    """SaaS operations dashboard renders correctly with enterprise design system."""

    def test_saas_renders_successfully(self, tmp_path):
        spec = _make_saas_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        assert result.outcome.value == "success"

    def test_saas_all_visuals_present(self, tmp_path):
        spec = _make_saas_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        assert result.fidelity.rendered_visuals == 8

    def test_saas_multiple_slicers_within_bounds(self, tmp_path):
        spec = _make_saas_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        import json
        page_dir = Path(result.output_path) / "SaaSOperationsDashboard.Report" / "definition" / "pages" / "page-ops"
        slicers = list((page_dir / "visuals").glob("f-*"))
        assert len(slicers) == 2
        for slicer_dir in slicers:
            slicer_json = json.loads((slicer_dir / "visual.json").read_text())
            pos = slicer_json["position"]
            assert pos["x"] >= 0, f"Slicer {slicer_dir.name} x={pos['x']} out of bounds"
            assert pos["x"] + pos["width"] <= 1280, f"Slicer {slicer_dir.name} exceeds right edge"
            assert pos["y"] + pos["height"] <= 720, f"Slicer {slicer_dir.name} exceeds bottom"

    def test_saas_page_has_background(self, tmp_path):
        spec = _make_saas_spec()
        result = render_powerbi_project(spec=spec, output_dir=tmp_path)
        import json
        page_json = json.loads(
            (Path(result.output_path) / "SaaSOperationsDashboard.Report" / "definition" / "pages" / "page-ops" / "page.json").read_text()
        )
        assert "objects" in page_json
        assert "background" in page_json["objects"]

    def test_saas_no_retail_specific_logic(self):
        """The design system should have no retail-specific constants or IDs."""
        import inspect
        from pbi_gen.renderer import design_system as ds_module
        source = inspect.getsource(ds_module)
        # Should not contain retail-specific IDs or fixture values
        forbidden_terms = ["page-executive-overview", "TotalRevenue", "GrossMarginPct",
                           "regional store", "product category", "Store"]
        for term in forbidden_terms:
            assert term not in source, f"Found retail-specific term '{term}' in design_system.py"
