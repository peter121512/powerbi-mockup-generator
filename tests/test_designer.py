"""Comprehensive tests for the AI Dashboard Designer (Stage 02).

All tests use mocked providers — no network access or credentials required.

Test categories:
1. Successful design flow with realistic structured output
2. Pydantic validation of model output
3. Semantic cross-reference validation
4. Malformed provider output → typed failure
5. Provider error → typed failure
6. High-confidence prompt proceeds without clarification
7. Material ambiguity triggers clarification gate
8. Routine uncertainty does NOT cause clarification
9. Initial revision metadata validity
10. Assumptions/confidence preserved in spec
11. No external credentials or network required
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from pbi_gen.models.dashboard_spec import (
    AggregationType,
    Assumption,
    ColourRole,
    ColumnSpec,
    ConditionalFormat,
    ConfidenceAssessment,
    ConfidenceDimension,
    DashboardIntent,
    DashboardSpec,
    DataPattern,
    DataPatternType,
    DensityPreference,
    DrillThroughConfig,
    FieldRef,
    FilterSpec,
    FilterType,
    InteractionConfig,
    InteractionType,
    MeasureSpec,
    MockDataNarrative,
    NavigationButton,
    PageLayout,
    PageRole,
    PageSpec,
    PresentationMode,
    Relationship,
    RelationshipCardinality,
    RevisionMetadata,
    SortSpec,
    SpecConfidence,
    TableSpec,
    ThemeSpec,
    TooltipSpec,
    TypographySpec,
    VisualPosition,
    VisualSpec,
    VisualType,
)
from pbi_gen.designer import (
    ClarificationRequest,
    DashboardDesigner,
    DesignDiagnostics,
    DesignOutcome,
    DesignResult,
    GateDecision,
    LLMProvider,
    ProviderConfig,
    ProviderError,
    ProviderResponse,
    ValidationIssue,
    design_dashboard,
    evaluate_clarification_gate,
    validate_spec,
)
from pbi_gen.designer.clarification import (
    HIGH_IMPACT_DIMENSIONS,
    _is_critical_assumption,
    _is_net_negative,
)
from pbi_gen.designer.prompt import (
    build_user_message,
    get_dashboard_schema,
    get_system_prompt,
)
from pbi_gen.designer.service import _extract_json, _ensure_initial_revision


# ─────────────────────────────────────────────────────────────────────────────
# Mock Provider
# ─────────────────────────────────────────────────────────────────────────────


class MockProvider(LLMProvider):
    """A mock LLM provider for testing without network access."""

    def __init__(self, response_content: str = "", should_error: bool = False, error_message: str = ""):
        self._response_content = response_content
        self._should_error = should_error
        self._error_message = error_message
        self.call_count = 0
        self.last_system_prompt = ""
        self.last_user_message = ""

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model-v1"

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        json_schema: dict | None = None,
    ) -> ProviderResponse:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_message = user_message

        if self._should_error:
            raise ProviderError(self._error_message or "Mock provider error")

        return ProviderResponse(
            content=self._response_content,
            model_id="mock-model-v1",
            stop_reason="end_turn",
            input_tokens=100,
            output_tokens=500,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Realistic test fixture: executive retail dashboard spec
# ─────────────────────────────────────────────────────────────────────────────


def _build_valid_retail_spec_json() -> str:
    """Build a realistic valid DashboardSpec as JSON (simulates LLM output)."""
    spec = DashboardSpec(
        intent=DashboardIntent(
            title="UK Retail Performance Dashboard",
            business_purpose="Provide CEO/CFO with at-a-glance retail performance metrics, trends, and regional comparison.",
            intended_audience="CEO and CFO",
            business_domain="retail",
            design_tone="Premium, restrained and boardroom-ready",
            key_questions=[
                "What is current revenue and how does it compare to last year?",
                "Which regions are performing well?",
                "What are the margin trends?",
                "Which categories drive growth?",
            ],
        ),
        revision=RevisionMetadata(
            spec_id="spec-retail-001",
            version=1,
        ),
        pages=[
            PageSpec(
                id="page-exec-overview",
                title="Executive Overview",
                purpose="At-a-glance KPIs and key trends for executive audience.",
                role=PageRole.EXECUTIVE_OVERVIEW,
                layout=PageLayout(grid_columns=12, grid_rows=8),
                visuals=[
                    VisualSpec(
                        id="vis-revenue-card",
                        visual_type=VisualType.CARD,
                        title="Total Revenue",
                        analytical_purpose="Show current period total revenue.",
                        value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                        position=VisualPosition(x=0, y=0, width=3, height=2),
                        priority=1,
                    ),
                    VisualSpec(
                        id="vis-margin-card",
                        visual_type=VisualType.CARD,
                        title="Gross Margin %",
                        analytical_purpose="Show current gross margin percentage.",
                        value_fields=[FieldRef(table="Sales", measure="Gross Margin %")],
                        position=VisualPosition(x=3, y=0, width=3, height=2),
                        priority=1,
                    ),
                    VisualSpec(
                        id="vis-revenue-trend",
                        visual_type=VisualType.LINE_CHART,
                        title="Revenue Trend",
                        analytical_purpose="Show revenue trend over time.",
                        category_fields=[FieldRef(table="Calendar", column="Date")],
                        value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                        position=VisualPosition(x=0, y=2, width=8, height=3),
                        priority=2,
                        sort=SortSpec(
                            field=FieldRef(table="Calendar", column="Date"),
                            descending=False,
                        ),
                    ),
                    VisualSpec(
                        id="vis-region-bar",
                        visual_type=VisualType.BAR_CHART,
                        title="Revenue by Region",
                        analytical_purpose="Compare regional performance.",
                        category_fields=[FieldRef(table="Store", column="Region")],
                        value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                        position=VisualPosition(x=8, y=2, width=4, height=3),
                        priority=3,
                    ),
                ],
                filters=[
                    FilterSpec(
                        id="filter-period",
                        filter_type=FilterType.SLICER,
                        field=FieldRef(table="Calendar", column="Quarter"),
                        label="Period",
                        visual_style="dropdown",
                    ),
                    FilterSpec(
                        id="filter-region",
                        filter_type=FilterType.SLICER,
                        field=FieldRef(table="Store", column="Region"),
                        label="Region",
                        visual_style="dropdown",
                    ),
                ],
            ),
            PageSpec(
                id="page-category-detail",
                title="Category Performance",
                purpose="Detailed category breakdown.",
                role=PageRole.DETAIL,
                layout=PageLayout(grid_columns=12, grid_rows=8),
                visuals=[
                    VisualSpec(
                        id="vis-category-table",
                        visual_type=VisualType.TABLE,
                        title="Category Metrics",
                        analytical_purpose="Detailed category-level metrics.",
                        category_fields=[FieldRef(table="Product", column="Category")],
                        value_fields=[
                            FieldRef(table="Sales", measure="Total Revenue"),
                            FieldRef(table="Sales", measure="Gross Margin %"),
                        ],
                        position=VisualPosition(x=0, y=0, width=12, height=5),
                        priority=1,
                    ),
                ],
            ),
        ],
        interactions=InteractionConfig(
            drill_throughs=[
                DrillThroughConfig(
                    source_page_id="page-exec-overview",
                    target_page_id="page-category-detail",
                    filter_fields=[FieldRef(table="Product", column="Category")],
                ),
            ],
            default_interaction=InteractionType.CROSS_HIGHLIGHT,
        ),
        theme=ThemeSpec(
            presentation_mode=PresentationMode.LIGHT,
            style_family="corporate_restrained",
            colour_roles=[
                ColourRole(role="primary", intent="Brand identity", hex_value="#1B365D"),
                ColourRole(role="positive", intent="Growth", hex_value="#2E7D32"),
                ColourRole(role="negative", intent="Decline", hex_value="#C62828"),
            ],
            density=DensityPreference.COMFORTABLE,
            design_tone="Premium and boardroom-ready",
        ),
        tables=[
            TableSpec(
                name="Sales",
                columns=[
                    ColumnSpec(name="SaleID", data_type="INTEGER", is_key=True),
                    ColumnSpec(name="Date", data_type="DATE"),
                    ColumnSpec(name="StoreID", data_type="INTEGER"),
                    ColumnSpec(name="ProductID", data_type="INTEGER"),
                    ColumnSpec(name="Revenue", data_type="REAL"),
                    ColumnSpec(name="COGS", data_type="REAL"),
                ],
                row_count_hint=500,
            ),
            TableSpec(
                name="Store",
                columns=[
                    ColumnSpec(name="StoreID", data_type="INTEGER", is_key=True),
                    ColumnSpec(name="Region", data_type="TEXT"),
                ],
                row_count_hint=20,
            ),
            TableSpec(
                name="Product",
                columns=[
                    ColumnSpec(name="ProductID", data_type="INTEGER", is_key=True),
                    ColumnSpec(name="Category", data_type="TEXT"),
                ],
                row_count_hint=50,
            ),
            TableSpec(
                name="Calendar",
                columns=[
                    ColumnSpec(name="Date", data_type="DATE", is_key=True),
                    ColumnSpec(name="Quarter", data_type="TEXT"),
                    ColumnSpec(name="Year", data_type="INTEGER"),
                ],
                row_count_hint=730,
            ),
        ],
        relationships=[
            Relationship(
                from_table="Sales",
                from_column="StoreID",
                to_table="Store",
                to_column="StoreID",
            ),
            Relationship(
                from_table="Sales",
                from_column="ProductID",
                to_table="Product",
                to_column="ProductID",
            ),
            Relationship(
                from_table="Sales",
                from_column="Date",
                to_table="Calendar",
                to_column="Date",
            ),
        ],
        measures=[
            MeasureSpec(
                name="Total Revenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
                format_string="£#,0",
            ),
            MeasureSpec(
                name="Gross Margin %",
                expression="DIVIDE(SUM(Sales[Revenue]) - SUM(Sales[COGS]), SUM(Sales[Revenue]), 0)",
                table="Sales",
                format_string="0.0%",
            ),
        ],
        mock_data_narrative=MockDataNarrative(
            scenario_description="Mid-size UK retailer with moderate growth and regional variation.",
            time_period="FY2023-FY2024",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.YOY_GROWTH,
                    description="Overall revenue growing at ~8%.",
                    applies_to=[FieldRef(table="Sales", measure="Total Revenue")],
                ),
            ],
            key_insights=["London dominates revenue but growth is plateauing."],
        ),
        confidence=SpecConfidence(
            assessments=[
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.AUDIENCE_CLARITY,
                    evidence_for=["User explicitly stated CEO and CFO."],
                ),
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.METRIC_DEFINITIONS,
                    evidence_for=["Revenue and margin are standard retail KPIs."],
                    evidence_against=[],
                ),
            ],
            assumptions=[
                Assumption(
                    statement="Revenue is gross revenue before returns.",
                    reasoning="Standard retail reporting convention.",
                    impact="Net revenue would change margin calculations slightly.",
                ),
            ],
            requires_clarification=False,
        ),
    )
    return spec.model_dump_json()


def _build_ambiguous_spec_json() -> str:
    """Build a spec where clarification gate SHOULD trigger."""
    spec = DashboardSpec(
        intent=DashboardIntent(
            title="Profitability Dashboard",
            business_purpose="Show margin performance.",
            business_domain="unknown",
        ),
        revision=RevisionMetadata(spec_id="spec-ambiguous-001", version=1),
        pages=[
            PageSpec(
                id="page-overview",
                title="Overview",
                role=PageRole.EXECUTIVE_OVERVIEW,
                visuals=[
                    VisualSpec(
                        id="vis-margin-card",
                        visual_type=VisualType.CARD,
                        title="Margin",
                        value_fields=[FieldRef(table="Finance", measure="Margin")],
                        position=VisualPosition(x=0, y=0, width=4, height=2),
                    ),
                ],
            ),
        ],
        tables=[
            TableSpec(
                name="Finance",
                columns=[
                    ColumnSpec(name="ID", data_type="INTEGER", is_key=True),
                    ColumnSpec(name="Amount", data_type="REAL"),
                ],
            ),
        ],
        measures=[
            MeasureSpec(name="Margin", expression="SUM(Finance[Amount])", table="Finance"),
        ],
        confidence=SpecConfidence(
            assessments=[
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.METRIC_DEFINITIONS,
                    evidence_for=[],
                    evidence_against=[
                        "User said 'margin' without specifying type.",
                        "Could be gross, contribution, operating, or net margin.",
                    ],
                    open_questions=[
                        "Which margin type do you need: gross margin, contribution margin, or operating margin?",
                    ],
                ),
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.BUSINESS_CONTEXT,
                    evidence_for=[],
                    evidence_against=[
                        "No industry or company context provided.",
                        "Cannot determine appropriate benchmarks.",
                    ],
                    open_questions=[
                        "What industry are you in?",
                    ],
                ),
            ],
            assumptions=[
                Assumption(
                    statement="Using gross margin as the default.",
                    reasoning="Most common margin type requested.",
                    impact="If operating margin is needed, the entire cost structure and model would be fundamentally different.",
                    clarification_question="Which margin type do you need: gross, contribution, or operating?",
                ),
            ],
            requires_clarification=True,
        ),
    )
    return spec.model_dump_json()


def _build_high_confidence_spec_json() -> str:
    """Build a spec where clarification should NOT trigger (all routine uncertainty)."""
    spec = DashboardSpec(
        intent=DashboardIntent(
            title="SaaS Growth Dashboard",
            business_purpose="Track whether SaaS growth is healthy.",
            intended_audience="Board of Directors",
            business_domain="saas",
            design_tone="Modern and data-rich",
        ),
        revision=RevisionMetadata(spec_id="spec-saas-001", version=1),
        pages=[
            PageSpec(
                id="page-growth",
                title="Growth Overview",
                role=PageRole.EXECUTIVE_OVERVIEW,
                visuals=[
                    VisualSpec(
                        id="vis-mrr-card",
                        visual_type=VisualType.CARD,
                        title="MRR",
                        analytical_purpose="Show monthly recurring revenue.",
                        value_fields=[FieldRef(table="Revenue", measure="MRR")],
                        position=VisualPosition(x=0, y=0, width=3, height=2),
                    ),
                ],
            ),
        ],
        tables=[
            TableSpec(
                name="Revenue",
                columns=[
                    ColumnSpec(name="Month", data_type="DATE", is_key=True),
                    ColumnSpec(name="Amount", data_type="REAL"),
                ],
            ),
        ],
        measures=[
            MeasureSpec(name="MRR", expression="SUM(Revenue[Amount])", table="Revenue"),
        ],
        confidence=SpecConfidence(
            assessments=[
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.AUDIENCE_CLARITY,
                    evidence_for=["Board of directors - clear executive audience."],
                ),
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.METRIC_DEFINITIONS,
                    evidence_for=["SaaS growth metrics are well-defined industry standards."],
                    evidence_against=["Exact revenue recognition method unspecified."],
                ),
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.VISUAL_CHOICE,
                    evidence_for=["Standard dashboard patterns for SaaS metrics."],
                    evidence_against=["User may prefer specific chart types."],
                    open_questions=["Do you prefer waterfall or bar charts for MRR breakdown?"],
                ),
            ],
            assumptions=[
                Assumption(
                    statement="Using standard SaaS metrics: MRR, churn, NRR.",
                    reasoning="Industry-standard for SaaS board reporting.",
                    impact="Non-standard metrics would require different model.",
                ),
            ],
            requires_clarification=False,
        ),
    )
    return spec.model_dump_json()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Successful design flow
# ─────────────────────────────────────────────────────────────────────────────


class TestSuccessfulDesignFlow:
    """Test the happy path: requirement → validated DashboardSpec."""

    def test_full_successful_design(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard(
            "Create an executive retail performance dashboard for a UK retailer."
        )

        assert result.outcome == DesignOutcome.SUCCESS
        assert result.spec is not None
        assert result.spec.intent.title == "UK Retail Performance Dashboard"
        assert len(result.spec.pages) == 2
        assert result.spec.pages[0].role == PageRole.EXECUTIVE_OVERVIEW

    def test_convenience_function(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        result = design_dashboard(
            "Create an executive retail dashboard.",
            provider=provider,
        )
        assert result.outcome == DesignOutcome.SUCCESS

    def test_provider_receives_prompt_and_schema(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        designer.design_dashboard("Build a dashboard.")

        assert provider.call_count == 1
        assert "enterprise Power BI dashboard designer" in provider.last_system_prompt
        assert "Build a dashboard." in provider.last_user_message
        assert "DashboardSpec" in provider.last_system_prompt

    def test_diagnostics_populated_on_success(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a retail dashboard.")

        assert result.diagnostics.provider == "mock"
        assert result.diagnostics.model == "mock-model-v1"

    def test_debug_mode_includes_raw_response(self):
        content = _build_valid_retail_spec_json()
        provider = MockProvider(response_content=content)
        designer = DashboardDesigner(provider=provider, debug=True)
        result = designer.design_dashboard("Build a retail dashboard.")

        assert result.outcome == DesignOutcome.SUCCESS
        assert result.diagnostics.raw_response == content

    def test_assumptions_preserved_in_diagnostics(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert "Revenue is gross revenue before returns." in result.diagnostics.assumptions_made


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pydantic validation of model output
# ─────────────────────────────────────────────────────────────────────────────


class TestPydanticValidation:
    """Test that malformed JSON that doesn't match schema is caught."""

    def test_missing_required_fields(self):
        # Missing 'intent' which is required
        bad_json = json.dumps({"pages": [], "tables": []})
        provider = MockProvider(response_content=bad_json)
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build something.")

        assert result.outcome == DesignOutcome.INVALID_OUTPUT
        assert "schema validation" in result.error_message
        assert len(result.diagnostics.validation_errors) > 0

    def test_invalid_enum_value(self):
        bad_json = json.dumps({
            "intent": {
                "title": "Test",
                "business_purpose": "Test",
            },
            "pages": [{
                "id": "p1",
                "title": "Page",
                "role": "not_a_valid_role",
                "visuals": [],
            }],
        })
        provider = MockProvider(response_content=bad_json)
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build something.")

        assert result.outcome == DesignOutcome.INVALID_OUTPUT

    def test_invalid_field_ref_both_column_and_measure(self):
        bad_spec = {
            "intent": {"title": "T", "business_purpose": "P"},
            "pages": [{
                "id": "p1",
                "title": "Page",
                "visuals": [{
                    "id": "v1",
                    "visual_type": "card",
                    "title": "V",
                    "value_fields": [
                        {"table": "T", "column": "C", "measure": "M"}
                    ],
                }],
            }],
            "tables": [{"name": "T", "columns": [{"name": "C", "data_type": "TEXT"}]}],
            "measures": [{"name": "M", "expression": "1"}],
        }
        provider = MockProvider(response_content=json.dumps(bad_spec))
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build something.")

        assert result.outcome == DesignOutcome.INVALID_OUTPUT


# ─────────────────────────────────────────────────────────────────────────────
# 3. Semantic cross-reference validation
# ─────────────────────────────────────────────────────────────────────────────


class TestSemanticValidation:
    """Test the semantic validator catches broken references."""

    def test_missing_table_reference(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(
                    id="p1",
                    title="Page",
                    visuals=[
                        VisualSpec(
                            id="v1",
                            visual_type=VisualType.CARD,
                            title="V",
                            value_fields=[FieldRef(table="NonExistent", column="BadCol")],
                            position=VisualPosition(x=0, y=0, width=3, height=2),
                        ),
                    ],
                ),
            ],
            tables=[TableSpec(name="Real", columns=[ColumnSpec(name="C", data_type="TEXT")])],
        )
        issues = validate_spec(spec)
        assert len(issues) > 0
        assert any(i.category == "missing_table_ref" for i in issues)

    def test_missing_column_reference(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(
                    id="p1",
                    title="Page",
                    visuals=[
                        VisualSpec(
                            id="v1",
                            visual_type=VisualType.BAR_CHART,
                            title="V",
                            category_fields=[FieldRef(table="Sales", column="NonExistentCol")],
                            value_fields=[FieldRef(table="Sales", measure="Rev")],
                            position=VisualPosition(x=0, y=0, width=6, height=3),
                        ),
                    ],
                ),
            ],
            tables=[
                TableSpec(name="Sales", columns=[ColumnSpec(name="Amount", data_type="REAL")]),
            ],
            measures=[MeasureSpec(name="Rev", expression="SUM(Sales[Amount])", table="Sales")],
        )
        issues = validate_spec(spec)
        assert any(i.category == "missing_column_ref" for i in issues)

    def test_missing_measure_reference(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(
                    id="p1",
                    title="Page",
                    visuals=[
                        VisualSpec(
                            id="v1",
                            visual_type=VisualType.CARD,
                            title="V",
                            value_fields=[FieldRef(table="Sales", measure="MissingMeasure")],
                            position=VisualPosition(x=0, y=0, width=3, height=2),
                        ),
                    ],
                ),
            ],
            tables=[
                TableSpec(name="Sales", columns=[ColumnSpec(name="Amount", data_type="REAL")]),
            ],
        )
        issues = validate_spec(spec)
        assert any(i.category == "missing_measure_ref" for i in issues)

    def test_missing_page_reference_in_drill_through(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(id="p1", title="Page 1"),
            ],
            interactions=InteractionConfig(
                drill_throughs=[
                    DrillThroughConfig(
                        source_page_id="p1",
                        target_page_id="nonexistent-page",
                        filter_fields=[FieldRef(table="T", column="C")],
                    ),
                ],
            ),
            tables=[TableSpec(name="T", columns=[ColumnSpec(name="C", data_type="TEXT")])],
        )
        issues = validate_spec(spec)
        assert any(
            i.category == "missing_page_ref" and "nonexistent-page" in i.message
            for i in issues
        )

    def test_out_of_bounds_visual_position(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(
                    id="p1",
                    title="Page",
                    layout=PageLayout(grid_columns=12, grid_rows=8),
                    visuals=[
                        VisualSpec(
                            id="v1",
                            visual_type=VisualType.CARD,
                            title="V",
                            value_fields=[FieldRef(table="T", measure="M")],
                            position=VisualPosition(x=10, y=0, width=5, height=2),
                        ),
                    ],
                ),
            ],
            tables=[TableSpec(name="T", columns=[ColumnSpec(name="C", data_type="TEXT")])],
            measures=[MeasureSpec(name="M", expression="1", table="T")],
        )
        issues = validate_spec(spec)
        assert any(i.category == "out_of_bounds" for i in issues)

    def test_valid_spec_passes_validation(self):
        spec = DashboardSpec.model_validate_json(_build_valid_retail_spec_json())
        issues = validate_spec(spec)
        assert issues == []

    def test_relationship_missing_table(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            tables=[
                TableSpec(name="A", columns=[ColumnSpec(name="id", data_type="INTEGER")]),
            ],
            relationships=[
                Relationship(from_table="A", from_column="id", to_table="B", to_column="id"),
            ],
        )
        issues = validate_spec(spec)
        assert any(i.category == "missing_table_ref" and "B" in i.message for i in issues)

    def test_filter_referencing_missing_field(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(
                    id="p1",
                    title="Page",
                    filters=[
                        FilterSpec(
                            id="f1",
                            filter_type=FilterType.SLICER,
                            field=FieldRef(table="Missing", column="Col"),
                        ),
                    ],
                ),
            ],
            tables=[TableSpec(name="Real", columns=[ColumnSpec(name="C", data_type="TEXT")])],
        )
        issues = validate_spec(spec)
        assert any(i.category == "missing_table_ref" for i in issues)

    def test_designer_returns_validation_error_for_broken_spec(self):
        """The full designer pipeline should catch semantic issues."""
        # Build a spec with a bad reference
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[
                PageSpec(
                    id="p1",
                    title="Page",
                    visuals=[
                        VisualSpec(
                            id="v1",
                            visual_type=VisualType.CARD,
                            title="V",
                            value_fields=[FieldRef(table="NonExistent", measure="Bad")],
                            position=VisualPosition(x=0, y=0, width=3, height=2),
                        ),
                    ],
                ),
            ],
            tables=[TableSpec(name="Real", columns=[ColumnSpec(name="C", data_type="TEXT")])],
        )
        provider = MockProvider(response_content=spec.model_dump_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build something.")

        assert result.outcome == DesignOutcome.VALIDATION_ERROR
        assert len(result.diagnostics.validation_errors) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Malformed provider output
# ─────────────────────────────────────────────────────────────────────────────


class TestMalformedOutput:
    """Test handling of non-JSON or garbage LLM responses."""

    def test_non_json_response(self):
        provider = MockProvider(response_content="I'm sorry, I can't do that Dave.")
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.outcome == DesignOutcome.INVALID_OUTPUT
        assert "not valid JSON" in result.error_message

    def test_empty_response(self):
        provider = MockProvider(response_content="")
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.outcome == DesignOutcome.INVALID_OUTPUT

    def test_json_in_markdown_fences(self):
        """Model wraps JSON in markdown code fences — should still work."""
        json_content = _build_valid_retail_spec_json()
        fenced = f"```json\n{json_content}\n```"
        provider = MockProvider(response_content=fenced)
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.outcome == DesignOutcome.SUCCESS

    def test_json_with_preamble(self):
        """Model adds text before/after JSON — extract the JSON."""
        json_content = _build_valid_retail_spec_json()
        with_preamble = f"Here is the dashboard spec:\n{json_content}\nI hope this helps!"
        provider = MockProvider(response_content=with_preamble)
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.outcome == DesignOutcome.SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# 5. Provider error
# ─────────────────────────────────────────────────────────────────────────────


class TestProviderError:
    """Test handling of provider failures."""

    def test_provider_error_returns_typed_failure(self):
        provider = MockProvider(should_error=True, error_message="Service unavailable")
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.outcome == DesignOutcome.PROVIDER_ERROR
        assert "Service unavailable" in result.error_message
        assert result.diagnostics.provider == "mock"

    def test_provider_error_class(self):
        err = ProviderError("Throttled", retryable=True)
        assert str(err) == "Throttled"
        assert err.retryable is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. High-confidence prompt proceeds without clarification
# ─────────────────────────────────────────────────────────────────────────────


class TestHighConfidenceProceeds:
    """Test that inferable prompts proceed without asking questions."""

    def test_clear_retail_prompt_no_clarification(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard(
            "Create an executive retail performance dashboard for a UK retailer. "
            "CEO and CFO audience. Revenue, margin, YoY growth, regional."
        )

        assert result.outcome == DesignOutcome.SUCCESS
        assert result.clarification is None

    def test_high_confidence_saas_prompt(self):
        provider = MockProvider(response_content=_build_high_confidence_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard(
            "I run a SaaS company. Build me a board dashboard showing whether growth is healthy."
        )

        assert result.outcome == DesignOutcome.SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# 7. Material ambiguity triggers clarification
# ─────────────────────────────────────────────────────────────────────────────


class TestClarificationTriggered:
    """Test that material ambiguity triggers the clarification gate."""

    def test_ambiguous_margin_triggers_clarification(self):
        provider = MockProvider(response_content=_build_ambiguous_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a profitability dashboard focused on margin.")

        assert result.outcome == DesignOutcome.CLARIFICATION_NEEDED
        assert result.clarification is not None
        assert "margin" in result.clarification.question.lower()

    def test_clarification_has_dimension(self):
        provider = MockProvider(response_content=_build_ambiguous_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a profitability dashboard.")

        assert result.clarification.dimension in [
            "metric_definitions",
            "business_context",
            "critical_assumption",
        ]

    def test_clarification_diagnostics_include_dimensions(self):
        provider = MockProvider(response_content=_build_ambiguous_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Show me margins.")

        assert len(result.diagnostics.clarification_dimensions) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 8. Routine uncertainty does NOT trigger clarification
# ─────────────────────────────────────────────────────────────────────────────


class TestRoutineUncertaintyPasses:
    """Test that routine design uncertainty does not trigger clarification."""

    def test_visual_choice_uncertainty_no_clarification(self):
        """Open questions on VISUAL_CHOICE (routine) should not trigger."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            pages=[PageSpec(id="p1", title="P")],
            confidence=SpecConfidence(
                assessments=[
                    ConfidenceAssessment(
                        dimension=ConfidenceDimension.VISUAL_CHOICE,
                        evidence_for=["Bar chart is reasonable for comparison."],
                        evidence_against=["Line chart could also work."],
                        open_questions=["Bar or line chart?"],
                    ),
                ],
            ),
        )
        decision = evaluate_clarification_gate(spec)
        assert decision.should_clarify is False

    def test_layout_uncertainty_no_clarification(self):
        """LAYOUT_DECISION uncertainty should not trigger."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            confidence=SpecConfidence(
                assessments=[
                    ConfidenceAssessment(
                        dimension=ConfidenceDimension.LAYOUT_DECISION,
                        evidence_for=[],
                        evidence_against=["Multiple valid layouts exist."],
                        open_questions=["2 or 3 column layout?"],
                    ),
                ],
            ),
        )
        decision = evaluate_clarification_gate(spec)
        assert decision.should_clarify is False

    def test_non_critical_assumption_no_clarification(self):
        """Assumptions without critical-impact language should not trigger."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            confidence=SpecConfidence(
                assumptions=[
                    Assumption(
                        statement="Using calendar year for date range.",
                        reasoning="No fiscal year specified.",
                        impact="Reporting period would shift by a few months.",
                        clarification_question="When does your fiscal year start?",
                    ),
                ],
            ),
        )
        decision = evaluate_clarification_gate(spec)
        assert decision.should_clarify is False

    def test_empty_confidence_no_clarification(self):
        """No confidence info at all should not trigger."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
        )
        decision = evaluate_clarification_gate(spec)
        assert decision.should_clarify is False


# ─────────────────────────────────────────────────────────────────────────────
# 9. Initial revision metadata
# ─────────────────────────────────────────────────────────────────────────────


class TestRevisionMetadata:
    """Test that initial generation gets correct revision metadata."""

    def test_initial_version_is_1(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.spec.revision.version == 1

    def test_initial_has_no_parent(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.spec.revision.parent_spec_id == ""

    def test_initial_has_valid_spec_id(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert result.spec.revision.spec_id != ""

    def test_forced_version_1_if_model_returns_higher(self):
        """If model returns version > 1, force back to 1 for initial gen."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P"),
            revision=RevisionMetadata(spec_id="s1", version=3, parent_spec_id="old"),
        )
        corrected = _ensure_initial_revision(spec)
        assert corrected.revision.version == 1
        assert corrected.revision.parent_spec_id == ""

    def test_page_ids_are_unique(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        page_ids = [p.id for p in result.spec.pages]
        assert len(page_ids) == len(set(page_ids))

    def test_visual_ids_are_unique_within_page(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        for page in result.spec.pages:
            vis_ids = [v.id for v in page.visuals]
            assert len(vis_ids) == len(set(vis_ids))


# ─────────────────────────────────────────────────────────────────────────────
# 10. Confidence/assumptions preserved in spec
# ─────────────────────────────────────────────────────────────────────────────


class TestConfidencePreserved:
    """Test that LLM-generated confidence evidence flows through to the result."""

    def test_assessments_preserved(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert len(result.spec.confidence.assessments) > 0
        assert result.spec.confidence.assessments[0].dimension == ConfidenceDimension.AUDIENCE_CLARITY

    def test_assumptions_preserved(self):
        provider = MockProvider(response_content=_build_valid_retail_spec_json())
        designer = DashboardDesigner(provider=provider)
        result = designer.design_dashboard("Build a dashboard.")

        assert len(result.spec.confidence.assumptions) > 0
        assert "revenue" in result.spec.confidence.assumptions[0].statement.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Additional unit tests for helper functions
# ─────────────────────────────────────────────────────────────────────────────


class TestJsonExtraction:
    """Test the JSON extraction logic for various model response formats."""

    def test_clean_json(self):
        data = {"key": "value"}
        assert _extract_json(json.dumps(data)) == data

    def test_json_with_whitespace(self):
        data = {"key": "value"}
        assert _extract_json(f"  \n{json.dumps(data)}\n  ") == data

    def test_json_in_code_fence(self):
        data = {"key": "value"}
        text = f"```json\n{json.dumps(data)}\n```"
        assert _extract_json(text) == data

    def test_json_with_surrounding_text(self):
        data = {"key": "value"}
        text = f"Here is the result:\n{json.dumps(data)}\nDone!"
        assert _extract_json(text) == data

    def test_invalid_json_returns_none(self):
        assert _extract_json("not json at all") is None

    def test_empty_string_returns_none(self):
        assert _extract_json("") is None


class TestClarificationGateHelpers:
    """Test helper functions in the clarification module."""

    def test_is_net_negative_true(self):
        assessment = ConfidenceAssessment(
            dimension=ConfidenceDimension.METRIC_DEFINITIONS,
            evidence_for=["One point"],
            evidence_against=["Point 1", "Point 2"],
        )
        assert _is_net_negative(assessment) is True

    def test_is_net_negative_false(self):
        assessment = ConfidenceAssessment(
            dimension=ConfidenceDimension.METRIC_DEFINITIONS,
            evidence_for=["Point 1", "Point 2"],
            evidence_against=["One point"],
        )
        assert _is_net_negative(assessment) is False

    def test_is_critical_assumption_with_keywords(self):
        assert _is_critical_assumption("The entire model would be fundamentally different.") is True
        assert _is_critical_assumption("It would produce a materially different dashboard.") is True
        assert _is_critical_assumption("Would result in the wrong dashboard entirely.") is True

    def test_is_critical_assumption_without_keywords(self):
        assert _is_critical_assumption("Minor formatting change.") is False
        assert _is_critical_assumption("") is False
        assert _is_critical_assumption("Reporting period would shift by a few months.") is False

    def test_high_impact_dimensions_defined(self):
        assert ConfidenceDimension.METRIC_DEFINITIONS in HIGH_IMPACT_DIMENSIONS
        assert ConfidenceDimension.BUSINESS_CONTEXT in HIGH_IMPACT_DIMENSIONS
        assert ConfidenceDimension.VISUAL_CHOICE not in HIGH_IMPACT_DIMENSIONS


class TestPromptBuilder:
    """Test the prompt construction functions."""

    def test_system_prompt_contains_reasoning_order(self):
        schema = get_dashboard_schema()
        prompt = get_system_prompt(schema)
        assert "Reasoning order" in prompt
        assert "Business objective" in prompt
        assert "Analytical questions" in prompt

    def test_system_prompt_contains_schema(self):
        schema = get_dashboard_schema()
        prompt = get_system_prompt(schema)
        assert "DashboardIntent" in prompt or "intent" in prompt

    def test_user_message_contains_requirement(self):
        msg = build_user_message("Build a sales dashboard.")
        assert "Build a sales dashboard." in msg

    def test_dashboard_schema_is_valid_json_schema(self):
        schema = get_dashboard_schema()
        assert "properties" in schema
        assert "title" in schema or "$defs" in schema


class TestDesignResultFactory:
    """Test DesignResult static factory methods."""

    def test_success_factory(self):
        spec = DashboardSpec(
            intent=DashboardIntent(title="T", business_purpose="P")
        )
        result = DesignResult.success(spec)
        assert result.outcome == DesignOutcome.SUCCESS
        assert result.spec == spec

    def test_needs_clarification_factory(self):
        cr = ClarificationRequest(question="Which margin?", dimension="metric_definitions")
        result = DesignResult.needs_clarification(cr)
        assert result.outcome == DesignOutcome.CLARIFICATION_NEEDED
        assert result.clarification == cr

    def test_provider_error_factory(self):
        result = DesignResult.provider_error("Timeout")
        assert result.outcome == DesignOutcome.PROVIDER_ERROR
        assert result.error_message == "Timeout"

    def test_invalid_output_factory(self):
        result = DesignResult.invalid_output("Bad JSON")
        assert result.outcome == DesignOutcome.INVALID_OUTPUT
        assert result.error_message == "Bad JSON"

    def test_validation_error_factory(self):
        issues = [ValidationIssue(category="test", message="broken")]
        result = DesignResult.validation_error("Failed", issues=issues)
        assert result.outcome == DesignOutcome.VALIDATION_ERROR
        assert len(result.diagnostics.validation_errors) == 1
