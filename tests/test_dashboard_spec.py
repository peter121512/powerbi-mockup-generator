"""Comprehensive tests for the DashboardSpec schema.

These tests validate:
1. Construction of a realistic multi-page executive dashboard spec.
2. JSON serialization and round-trip deserialization.
3. Validation failure for invalid specs (duplicate IDs, bad field refs).
4. Revision metadata preserving stable page/visual IDs.
5. Confidence / uncertainty representation.
6. Interaction/filter structures.
7. Mock-data narrative / pattern requirements.
"""

import json
from copy import deepcopy
from datetime import datetime

import pytest

from pbi_gen.models import (
    AggregationType,
    Assumption,
    ColourRole,
    ColumnSpec,
    ConditionalFormat,
    ConfidenceAssessment,
    ConfidenceDimension,
    CrossFilterDirection,
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


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Realistic UK retail executive dashboard
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def retail_tables() -> list[TableSpec]:
    """Realistic table specs for a UK retail analytics model."""
    return [
        TableSpec(
            name="Sales",
            description="Fact table of daily sales transactions.",
            columns=[
                ColumnSpec(name="SaleID", data_type="INTEGER", is_key=True),
                ColumnSpec(name="Date", data_type="DATE"),
                ColumnSpec(name="StoreID", data_type="INTEGER"),
                ColumnSpec(name="ProductID", data_type="INTEGER"),
                ColumnSpec(name="Revenue", data_type="REAL"),
                ColumnSpec(name="COGS", data_type="REAL"),
                ColumnSpec(name="Quantity", data_type="INTEGER"),
            ],
            row_count_hint=500,
        ),
        TableSpec(
            name="Store",
            description="Dimension table for store locations.",
            columns=[
                ColumnSpec(name="StoreID", data_type="INTEGER", is_key=True),
                ColumnSpec(
                    name="Region",
                    data_type="TEXT",
                    sample_values=["London", "South East", "North West", "Midlands", "Scotland"],
                ),
                ColumnSpec(name="StoreName", data_type="TEXT"),
                ColumnSpec(name="OpenDate", data_type="DATE"),
            ],
            row_count_hint=20,
        ),
        TableSpec(
            name="Product",
            description="Dimension table for products and categories.",
            columns=[
                ColumnSpec(name="ProductID", data_type="INTEGER", is_key=True),
                ColumnSpec(
                    name="Category",
                    data_type="TEXT",
                    sample_values=["Food & Drink", "Clothing", "Electronics", "Home", "Health"],
                ),
                ColumnSpec(name="ProductName", data_type="TEXT"),
                ColumnSpec(name="UnitCost", data_type="REAL"),
            ],
            row_count_hint=50,
        ),
        TableSpec(
            name="Calendar",
            description="Date dimension.",
            columns=[
                ColumnSpec(name="Date", data_type="DATE", is_key=True),
                ColumnSpec(name="Year", data_type="INTEGER"),
                ColumnSpec(name="Quarter", data_type="TEXT"),
                ColumnSpec(name="Month", data_type="TEXT"),
                ColumnSpec(name="MonthNum", data_type="INTEGER"),
            ],
            row_count_hint=730,
        ),
    ]


@pytest.fixture
def retail_relationships() -> list[Relationship]:
    return [
        Relationship(
            from_table="Sales",
            from_column="StoreID",
            to_table="Store",
            to_column="StoreID",
            cardinality=RelationshipCardinality.MANY_TO_ONE,
        ),
        Relationship(
            from_table="Sales",
            from_column="ProductID",
            to_table="Product",
            to_column="ProductID",
            cardinality=RelationshipCardinality.MANY_TO_ONE,
        ),
        Relationship(
            from_table="Sales",
            from_column="Date",
            to_table="Calendar",
            to_column="Date",
            cardinality=RelationshipCardinality.MANY_TO_ONE,
        ),
    ]


@pytest.fixture
def retail_measures() -> list[MeasureSpec]:
    return [
        MeasureSpec(
            name="Total Revenue",
            expression="SUM(Sales[Revenue])",
            table="Sales",
            format_string="£#,0",
        ),
        MeasureSpec(
            name="Gross Margin",
            expression="SUM(Sales[Revenue]) - SUM(Sales[COGS])",
            table="Sales",
            format_string="£#,0",
        ),
        MeasureSpec(
            name="Gross Margin %",
            expression="DIVIDE([Gross Margin], [Total Revenue], 0)",
            table="Sales",
            format_string="0.0%",
        ),
        MeasureSpec(
            name="YoY Growth",
            expression="DIVIDE([Total Revenue] - CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Calendar[Date])), CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Calendar[Date])), 0)",
            table="Sales",
            format_string="0.0%",
            description="Year-over-year revenue growth rate.",
        ),
    ]


@pytest.fixture
def executive_page() -> PageSpec:
    """Executive overview page with KPIs, trends, and regional breakdown."""
    return PageSpec(
        id="page-exec-overview",
        title="Executive Overview",
        purpose="Provide C-suite with at-a-glance performance metrics and key trends.",
        role=PageRole.EXECUTIVE_OVERVIEW,
        layout=PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8),
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
                id="vis-yoy-card",
                visual_type=VisualType.CARD,
                title="YoY Growth",
                analytical_purpose="Show year-over-year revenue growth.",
                value_fields=[FieldRef(table="Sales", measure="YoY Growth")],
                position=VisualPosition(x=6, y=0, width=3, height=2),
                priority=1,
                conditional_formats=[
                    ConditionalFormat(
                        target_field=FieldRef(table="Sales", measure="YoY Growth"),
                        rule_description="Green if positive, red if negative.",
                        colour_positive="#2E7D32",
                        colour_negative="#C62828",
                    )
                ],
            ),
            VisualSpec(
                id="vis-revenue-trend",
                visual_type=VisualType.LINE_CHART,
                title="Revenue Trend",
                subtitle="Monthly, last 24 months",
                analytical_purpose="Show revenue trend over time to identify growth patterns.",
                category_fields=[FieldRef(table="Calendar", column="Date")],
                value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                position=VisualPosition(x=0, y=2, width=8, height=3),
                priority=2,
                sort=SortSpec(
                    field=FieldRef(table="Calendar", column="Date"), descending=False
                ),
            ),
            VisualSpec(
                id="vis-regional-bar",
                visual_type=VisualType.BAR_CHART,
                title="Revenue by Region",
                analytical_purpose="Compare regional performance to identify under/over-performers.",
                category_fields=[FieldRef(table="Store", column="Region")],
                value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                position=VisualPosition(x=8, y=2, width=4, height=3),
                priority=3,
                sort=SortSpec(
                    field=FieldRef(table="Sales", measure="Total Revenue"),
                    descending=True,
                ),
            ),
            VisualSpec(
                id="vis-category-donut",
                visual_type=VisualType.DONUT_CHART,
                title="Revenue by Category",
                analytical_purpose="Show revenue distribution across product categories.",
                category_fields=[FieldRef(table="Product", column="Category")],
                value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                position=VisualPosition(x=0, y=5, width=4, height=3),
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
                multi_select=True,
            ),
        ],
    )


@pytest.fixture
def detail_page() -> PageSpec:
    """Product performance detail page."""
    return PageSpec(
        id="page-product-detail",
        title="Product Performance",
        purpose="Deep-dive into product and category performance metrics.",
        role=PageRole.DETAIL,
        layout=PageLayout(width=1280, height=720),
        visuals=[
            VisualSpec(
                id="vis-product-table",
                visual_type=VisualType.TABLE,
                title="Product Performance Table",
                analytical_purpose="Detailed product-level metrics for operational review.",
                category_fields=[
                    FieldRef(table="Product", column="Category"),
                    FieldRef(table="Product", column="ProductName"),
                ],
                value_fields=[
                    FieldRef(table="Sales", measure="Total Revenue"),
                    FieldRef(table="Sales", measure="Gross Margin %"),
                    FieldRef(table="Sales", measure="YoY Growth"),
                ],
                position=VisualPosition(x=0, y=0, width=12, height=5),
                priority=1,
                conditional_formats=[
                    ConditionalFormat(
                        target_field=FieldRef(table="Sales", measure="YoY Growth"),
                        rule_description="Red background if negative growth, green if > 10%.",
                    ),
                ],
            ),
            VisualSpec(
                id="vis-category-trend",
                visual_type=VisualType.LINE_CHART,
                title="Category Revenue Trend",
                analytical_purpose="Compare category trends over time.",
                category_fields=[FieldRef(table="Calendar", column="Date")],
                value_fields=[FieldRef(table="Sales", measure="Total Revenue")],
                series_field=FieldRef(table="Product", column="Category"),
                position=VisualPosition(x=0, y=5, width=12, height=3),
                priority=2,
            ),
        ],
        filters=[
            FilterSpec(
                id="filter-category",
                filter_type=FilterType.SLICER,
                field=FieldRef(table="Product", column="Category"),
                label="Category",
                visual_style="list",
            ),
        ],
    )


@pytest.fixture
def retail_theme() -> ThemeSpec:
    return ThemeSpec(
        presentation_mode=PresentationMode.LIGHT,
        style_family="corporate_restrained",
        colour_roles=[
            ColourRole(role="primary", intent="Brand identity", hex_value="#1B365D"),
            ColourRole(role="accent", intent="Highlights and call-to-action"),
            ColourRole(role="positive", intent="Growth / success", hex_value="#2E7D32"),
            ColourRole(role="negative", intent="Decline / risk", hex_value="#C62828"),
            ColourRole(role="neutral", intent="Supporting / background"),
        ],
        typography=TypographySpec(
            heading_font="Segoe UI Semibold",
            body_font="Segoe UI",
            base_size_pt=10,
        ),
        density=DensityPreference.COMFORTABLE,
        whitespace_emphasis="Generous padding between cards, clear section separation.",
        card_style="subtle shadow with rounded corners",
        emphasis_rules=[
            "KPI cards are the largest visuals on the page.",
            "Negative variances always shown in red.",
            "Trends use the primary colour for the main line.",
        ],
        design_tone="Premium, restrained and boardroom-ready.",
    )


@pytest.fixture
def retail_narrative() -> MockDataNarrative:
    return MockDataNarrative(
        scenario_description=(
            "A mid-size UK retailer experiencing moderate overall growth but with "
            "significant regional variation. London and South East are strong performers "
            "while North West underperforms. Electronics category is growing rapidly "
            "but Food & Drink shows seasonal patterns. One quarter shows a notable dip "
            "due to supply chain issues."
        ),
        time_period="FY2023-FY2024",
        patterns=[
            DataPattern(
                pattern_type=DataPatternType.YOY_GROWTH,
                description="Overall revenue growing at ~8% YoY.",
                applies_to=[FieldRef(table="Sales", measure="Total Revenue")],
                parameters={"growth_rate": 0.08},
            ),
            DataPattern(
                pattern_type=DataPatternType.SEASONAL,
                description="Clear Q4 peak in Food & Drink due to Christmas.",
                applies_to=[FieldRef(table="Sales", column="Revenue")],
                parameters={"peak_quarter": "Q4", "category": "Food & Drink"},
            ),
            DataPattern(
                pattern_type=DataPatternType.CONCENTRATION,
                description="Top 3 regions account for 70% of revenue (Pareto-like).",
                applies_to=[FieldRef(table="Store", column="Region")],
                parameters={"top_n": 3, "share": 0.7},
            ),
            DataPattern(
                pattern_type=DataPatternType.OUTLIER_NEGATIVE,
                description="Q2 FY2024 shows a notable dip due to supply chain disruption.",
                applies_to=[FieldRef(table="Sales", measure="Total Revenue")],
                parameters={"quarter": "Q2", "magnitude": -0.15},
            ),
            DataPattern(
                pattern_type=DataPatternType.TREND_UP,
                description="Electronics category growing fastest at ~20% YoY.",
                applies_to=[FieldRef(table="Sales", column="Revenue")],
                parameters={"category": "Electronics", "growth_rate": 0.20},
            ),
        ],
        key_insights=[
            "London is the dominant revenue region but growth is plateauing.",
            "North West underperforms targets by ~12%.",
            "Electronics category is the growth engine.",
            "Gross margin is under pressure from COGS increases in Q2.",
        ],
        constraints=[
            "All margins must be positive.",
            "Regional totals must sum to the overall total.",
            "Calendar table must cover full FY2023-FY2024 range.",
        ],
    )


@pytest.fixture
def retail_confidence() -> SpecConfidence:
    return SpecConfidence(
        assessments=[
            ConfidenceAssessment(
                dimension=ConfidenceDimension.AUDIENCE_CLARITY,
                evidence_for=["User explicitly stated CEO and CFO audience."],
                evidence_against=[],
                open_questions=[],
            ),
            ConfidenceAssessment(
                dimension=ConfidenceDimension.METRIC_DEFINITIONS,
                evidence_for=[
                    "Revenue, margin and YoY growth are standard retail KPIs."
                ],
                evidence_against=[
                    "User did not specify whether revenue is net or gross."
                ],
                open_questions=[
                    "Is revenue net of returns?",
                    "Should growth be calendar year or fiscal year?",
                ],
            ),
            ConfidenceAssessment(
                dimension=ConfidenceDimension.VISUAL_CHOICE,
                evidence_for=[
                    "KPI cards for headline numbers is standard executive pattern.",
                    "Line chart for trends is well-established.",
                ],
                evidence_against=[
                    "Donut chart for category mix may not be optimal for many categories.",
                ],
                open_questions=[],
            ),
        ],
        assumptions=[
            Assumption(
                statement="Revenue is gross revenue before returns.",
                reasoning="Most retail dashboards report gross unless specified.",
                impact="If net, the COGS calculation and margin figures would differ.",
                clarification_question="Should revenue figures be net of returns and discounts?",
            ),
            Assumption(
                statement="Fiscal year aligns with calendar year (Jan-Dec).",
                reasoning="No fiscal year start month was specified.",
                impact="YoY calculations would be offset if fiscal year starts differently.",
                clarification_question="When does your fiscal year start?",
            ),
        ],
        requires_clarification=False,
    )


@pytest.fixture
def full_retail_spec(
    retail_tables,
    retail_relationships,
    retail_measures,
    executive_page,
    detail_page,
    retail_theme,
    retail_narrative,
    retail_confidence,
) -> DashboardSpec:
    """Complete multi-page executive retail dashboard spec."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="UK Retail Performance Dashboard",
            business_purpose=(
                "Provide the CEO and CFO with a comprehensive view of retail "
                "performance including revenue, margins, growth trends, regional "
                "comparison and product category analysis."
            ),
            intended_audience="CEO and CFO",
            business_domain="retail",
            design_tone="Premium, restrained and boardroom-ready.",
            key_questions=[
                "What is our current revenue and how does it compare to last year?",
                "Which regions are performing well and which are underperforming?",
                "What are our margin trends and are they sustainable?",
                "Which product categories drive growth?",
                "Are there risks we should be aware of?",
            ],
        ),
        revision=RevisionMetadata(
            spec_id="spec-retail-v1",
            version=1,
            created_at=datetime(2024, 8, 1, 10, 0, 0),
        ),
        pages=[executive_page, detail_page],
        interactions=InteractionConfig(
            drill_throughs=[
                DrillThroughConfig(
                    source_page_id="page-exec-overview",
                    target_page_id="page-product-detail",
                    filter_fields=[FieldRef(table="Product", column="Category")],
                    description="Drill from category donut to product detail page.",
                ),
            ],
            navigation_buttons=[
                NavigationButton(
                    label="View Product Detail",
                    target_page_id="page-product-detail",
                    style="outline",
                ),
            ],
            default_interaction=InteractionType.CROSS_HIGHLIGHT,
        ),
        theme=retail_theme,
        tables=retail_tables,
        relationships=retail_relationships,
        measures=retail_measures,
        mock_data_narrative=retail_narrative,
        confidence=retail_confidence,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Construction of realistic multi-page spec
# ─────────────────────────────────────────────────────────────────────────────


class TestRealisticConstruction:
    """Test that a full realistic spec can be constructed and accessed."""

    def test_full_spec_constructs(self, full_retail_spec: DashboardSpec):
        spec = full_retail_spec
        assert spec.intent.title == "UK Retail Performance Dashboard"
        assert spec.intent.business_domain == "retail"
        assert len(spec.pages) == 2
        assert len(spec.tables) == 4
        assert len(spec.measures) == 4

    def test_pages_have_correct_roles(self, full_retail_spec: DashboardSpec):
        spec = full_retail_spec
        assert spec.pages[0].role == PageRole.EXECUTIVE_OVERVIEW
        assert spec.pages[1].role == PageRole.DETAIL

    def test_executive_page_has_visuals_and_filters(self, executive_page: PageSpec):
        assert len(executive_page.visuals) == 6
        assert len(executive_page.filters) == 2
        # Check visual types span various categories
        types = {v.visual_type for v in executive_page.visuals}
        assert VisualType.CARD in types
        assert VisualType.LINE_CHART in types
        assert VisualType.BAR_CHART in types
        assert VisualType.DONUT_CHART in types

    def test_visual_field_bindings(self, executive_page: PageSpec):
        revenue_card = next(
            v for v in executive_page.visuals if v.id == "vis-revenue-card"
        )
        assert len(revenue_card.value_fields) == 1
        assert revenue_card.value_fields[0].measure == "Total Revenue"
        assert revenue_card.value_fields[0].table == "Sales"

    def test_visual_positioning(self, executive_page: PageSpec):
        card = next(v for v in executive_page.visuals if v.id == "vis-revenue-card")
        assert card.position.x == 0
        assert card.position.y == 0
        assert card.position.width == 3
        assert card.position.height == 2

    def test_visual_priority_ordering(self, executive_page: PageSpec):
        # KPI cards should have highest priority (1)
        cards = [v for v in executive_page.visuals if v.visual_type == VisualType.CARD]
        for card in cards:
            assert card.priority == 1

    def test_relationships_are_typed(self, retail_relationships):
        for rel in retail_relationships:
            assert rel.cardinality == RelationshipCardinality.MANY_TO_ONE
            assert rel.cross_filter_direction == CrossFilterDirection.SINGLE

    def test_measures_have_expressions(self, retail_measures):
        yoy = next(m for m in retail_measures if m.name == "YoY Growth")
        assert "SAMEPERIODLASTYEAR" in yoy.expression
        assert yoy.format_string == "0.0%"


# ─────────────────────────────────────────────────────────────────────────────
# 2. JSON serialization and round-trip
# ─────────────────────────────────────────────────────────────────────────────


class TestSerialization:
    """Test JSON serialization and deserialization round-trip."""

    def test_serialize_to_json(self, full_retail_spec: DashboardSpec):
        json_str = full_retail_spec.model_dump_json(indent=2)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["intent"]["title"] == "UK Retail Performance Dashboard"

    def test_round_trip_preserves_data(self, full_retail_spec: DashboardSpec):
        json_str = full_retail_spec.model_dump_json()
        restored = DashboardSpec.model_validate_json(json_str)

        assert restored.intent.title == full_retail_spec.intent.title
        assert restored.intent.business_purpose == full_retail_spec.intent.business_purpose
        assert len(restored.pages) == len(full_retail_spec.pages)
        assert len(restored.tables) == len(full_retail_spec.tables)
        assert len(restored.measures) == len(full_retail_spec.measures)

    def test_round_trip_preserves_page_ids(self, full_retail_spec: DashboardSpec):
        json_str = full_retail_spec.model_dump_json()
        restored = DashboardSpec.model_validate_json(json_str)

        for orig_page, restored_page in zip(
            full_retail_spec.pages, restored.pages, strict=True
        ):
            assert orig_page.id == restored_page.id
            assert orig_page.title == restored_page.title

    def test_round_trip_preserves_visual_ids(self, full_retail_spec: DashboardSpec):
        json_str = full_retail_spec.model_dump_json()
        restored = DashboardSpec.model_validate_json(json_str)

        orig_visuals = full_retail_spec.pages[0].visuals
        restored_visuals = restored.pages[0].visuals
        for orig, rest in zip(orig_visuals, restored_visuals, strict=True):
            assert orig.id == rest.id

    def test_round_trip_preserves_enums(self, full_retail_spec: DashboardSpec):
        json_str = full_retail_spec.model_dump_json()
        restored = DashboardSpec.model_validate_json(json_str)

        assert restored.pages[0].role == PageRole.EXECUTIVE_OVERVIEW
        assert restored.theme.presentation_mode == PresentationMode.LIGHT
        assert restored.theme.density == DensityPreference.COMFORTABLE

    def test_round_trip_preserves_nested_objects(self, full_retail_spec: DashboardSpec):
        json_str = full_retail_spec.model_dump_json()
        restored = DashboardSpec.model_validate_json(json_str)

        # Check conditional formats
        yoy_card = next(
            v for v in restored.pages[0].visuals if v.id == "vis-yoy-card"
        )
        assert len(yoy_card.conditional_formats) == 1
        assert yoy_card.conditional_formats[0].colour_positive == "#2E7D32"

    def test_model_dump_dict(self, full_retail_spec: DashboardSpec):
        data = full_retail_spec.model_dump()
        assert isinstance(data, dict)
        assert data["intent"]["title"] == "UK Retail Performance Dashboard"
        # Enums serialize as their values
        assert data["pages"][0]["role"] == "executive_overview"

    def test_from_dict(self, full_retail_spec: DashboardSpec):
        data = full_retail_spec.model_dump()
        restored = DashboardSpec.model_validate(data)
        assert restored.intent.title == full_retail_spec.intent.title


# ─────────────────────────────────────────────────────────────────────────────
# 3. Validation failures
# ─────────────────────────────────────────────────────────────────────────────


class TestValidation:
    """Test that invalid specs are rejected with clear errors."""

    def test_duplicate_page_ids_rejected(self):
        page = PageSpec(id="same-id", title="Page 1", role=PageRole.EXECUTIVE_OVERVIEW)
        page2 = PageSpec(id="same-id", title="Page 2", role=PageRole.DETAIL)
        with pytest.raises(Exception) as exc_info:
            DashboardSpec(
                intent=DashboardIntent(
                    title="Test", business_purpose="Test"
                ),
                pages=[page, page2],
            )
        assert "Duplicate page IDs" in str(exc_info.value)

    def test_duplicate_visual_ids_rejected(self):
        vis1 = VisualSpec(
            id="dup-vis",
            visual_type=VisualType.CARD,
            title="A",
            value_fields=[FieldRef(table="T", measure="M")],
        )
        vis2 = VisualSpec(
            id="dup-vis",
            visual_type=VisualType.CARD,
            title="B",
            value_fields=[FieldRef(table="T", measure="M")],
        )
        with pytest.raises(Exception) as exc_info:
            PageSpec(
                title="Test Page",
                role=PageRole.EXECUTIVE_OVERVIEW,
                visuals=[vis1, vis2],
            )
        assert "Duplicate visual IDs" in str(exc_info.value)

    def test_field_ref_requires_column_or_measure(self):
        with pytest.raises(Exception) as exc_info:
            FieldRef(table="Sales")
        assert "column or measure" in str(exc_info.value).lower()

    def test_field_ref_rejects_both_column_and_measure(self):
        with pytest.raises(Exception) as exc_info:
            FieldRef(table="Sales", column="Revenue", measure="Total Revenue")
        assert "column OR measure" in str(exc_info.value)

    def test_dashboard_intent_requires_business_purpose(self):
        with pytest.raises(Exception):
            DashboardIntent(title="Test")  # type: ignore[call-arg]

    def test_measure_requires_expression(self):
        with pytest.raises(Exception):
            MeasureSpec(name="Broken")  # type: ignore[call-arg]

    def test_column_spec_requires_data_type(self):
        with pytest.raises(Exception):
            ColumnSpec(name="Col")  # type: ignore[call-arg]

    def test_mock_narrative_requires_scenario(self):
        with pytest.raises(Exception):
            MockDataNarrative()  # type: ignore[call-arg]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Revision metadata and stable IDs
# ─────────────────────────────────────────────────────────────────────────────


class TestRevisionMetadata:
    """Test that revision metadata supports conversational iteration."""

    def test_revision_version_tracking(self, full_retail_spec: DashboardSpec):
        assert full_retail_spec.revision.version == 1
        assert full_retail_spec.revision.spec_id == "spec-retail-v1"
        assert full_retail_spec.revision.parent_spec_id == ""

    def test_revision_creates_linked_version(self, full_retail_spec: DashboardSpec):
        """Simulate a user amendment creating version 2."""
        v1_data = full_retail_spec.model_dump()

        # Create v2 with an amendment
        v2_data = deepcopy(v1_data)
        v2_data["revision"] = {
            "spec_id": "spec-retail-v2",
            "version": 2,
            "parent_spec_id": "spec-retail-v1",
            "amendment_summary": "Added category filter to executive page.",
            "revision_reason": "User requested easier category filtering.",
            "created_at": datetime(2024, 8, 2, 14, 0, 0).isoformat(),
        }

        v2 = DashboardSpec.model_validate(v2_data)
        assert v2.revision.version == 2
        assert v2.revision.parent_spec_id == "spec-retail-v1"
        assert "category filter" in v2.revision.amendment_summary

    def test_stable_page_ids_across_revisions(self, full_retail_spec: DashboardSpec):
        """Page IDs must remain stable when creating a new revision."""
        v1_page_ids = [p.id for p in full_retail_spec.pages]

        # Simulate revision: serialize, modify, deserialize
        v2_data = full_retail_spec.model_dump()
        v2_data["revision"]["version"] = 2
        v2_data["revision"]["spec_id"] = "spec-retail-v2"
        v2_data["revision"]["parent_spec_id"] = "spec-retail-v1"

        v2 = DashboardSpec.model_validate(v2_data)
        v2_page_ids = [p.id for p in v2.pages]

        assert v1_page_ids == v2_page_ids

    def test_stable_visual_ids_across_revisions(self, full_retail_spec: DashboardSpec):
        """Visual IDs must remain stable when creating a new revision."""
        v1_visual_ids = [v.id for p in full_retail_spec.pages for v in p.visuals]

        v2_data = full_retail_spec.model_dump()
        v2_data["revision"]["version"] = 2
        v2 = DashboardSpec.model_validate(v2_data)
        v2_visual_ids = [v.id for p in v2.pages for v in p.visuals]

        assert v1_visual_ids == v2_visual_ids

    def test_revision_timestamp(self, full_retail_spec: DashboardSpec):
        assert full_retail_spec.revision.created_at == datetime(2024, 8, 1, 10, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Confidence and uncertainty
# ─────────────────────────────────────────────────────────────────────────────


class TestConfidence:
    """Test confidence/uncertainty modelling."""

    def test_confidence_assessments(self, retail_confidence: SpecConfidence):
        assert len(retail_confidence.assessments) == 3
        audience = retail_confidence.assessments[0]
        assert audience.dimension == ConfidenceDimension.AUDIENCE_CLARITY
        assert len(audience.evidence_for) == 1
        assert len(audience.evidence_against) == 0

    def test_confidence_with_uncertainty(self, retail_confidence: SpecConfidence):
        metrics = retail_confidence.assessments[1]
        assert metrics.dimension == ConfidenceDimension.METRIC_DEFINITIONS
        assert len(metrics.evidence_against) > 0
        assert len(metrics.open_questions) > 0

    def test_assumptions_are_structured(self, retail_confidence: SpecConfidence):
        assert len(retail_confidence.assumptions) == 2
        first = retail_confidence.assumptions[0]
        assert first.statement != ""
        assert first.reasoning != ""
        assert first.impact != ""
        assert first.clarification_question != ""

    def test_requires_clarification_flag(self, retail_confidence: SpecConfidence):
        assert retail_confidence.requires_clarification is False

    def test_high_uncertainty_scenario(self):
        """A spec where clarification IS required."""
        conf = SpecConfidence(
            assessments=[
                ConfidenceAssessment(
                    dimension=ConfidenceDimension.DATA_AVAILABILITY,
                    evidence_for=[],
                    evidence_against=[
                        "User mentioned data exists but gave no details.",
                        "No column names or data types provided.",
                    ],
                    open_questions=[
                        "What tables are available?",
                        "What time granularity does the data support?",
                    ],
                ),
            ],
            assumptions=[
                Assumption(
                    statement="Standard star schema is available.",
                    reasoning="Most retail analytics use star schemas.",
                    impact="If not available, the entire model design changes.",
                    clarification_question="Can you describe your data structure?",
                ),
            ],
            requires_clarification=True,
        )
        assert conf.requires_clarification is True
        assert len(conf.assessments[0].evidence_against) == 2

    def test_empty_confidence_valid(self):
        """A spec can have no confidence info (e.g. user provided full detail)."""
        conf = SpecConfidence()
        assert conf.assessments == []
        assert conf.assumptions == []
        assert conf.requires_clarification is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. Interaction and filter structures
# ─────────────────────────────────────────────────────────────────────────────


class TestInteractionsAndFilters:
    """Test filter/slicer and interaction configuration."""

    def test_page_level_filters(self, executive_page: PageSpec):
        assert len(executive_page.filters) == 2
        period_filter = next(
            f for f in executive_page.filters if f.id == "filter-period"
        )
        assert period_filter.filter_type == FilterType.SLICER
        assert period_filter.field.table == "Calendar"
        assert period_filter.field.column == "Quarter"
        assert period_filter.visual_style == "dropdown"

    def test_drill_through_config(self, full_retail_spec: DashboardSpec):
        dts = full_retail_spec.interactions.drill_throughs
        assert len(dts) == 1
        dt = dts[0]
        assert dt.source_page_id == "page-exec-overview"
        assert dt.target_page_id == "page-product-detail"
        assert len(dt.filter_fields) == 1
        assert dt.filter_fields[0].column == "Category"

    def test_navigation_buttons(self, full_retail_spec: DashboardSpec):
        navs = full_retail_spec.interactions.navigation_buttons
        assert len(navs) == 1
        assert navs[0].target_page_id == "page-product-detail"

    def test_default_interaction_type(self, full_retail_spec: DashboardSpec):
        assert (
            full_retail_spec.interactions.default_interaction
            == InteractionType.CROSS_HIGHLIGHT
        )

    def test_visual_interaction_override(self):
        """A visual can override the default interaction type."""
        vis = VisualSpec(
            visual_type=VisualType.SLICER,
            title="Region Filter",
            category_fields=[FieldRef(table="Store", column="Region")],
            interaction_type=InteractionType.CROSS_FILTER,
        )
        assert vis.interaction_type == InteractionType.CROSS_FILTER

    def test_filter_types_enum(self):
        """All filter types can be used."""
        for ft in FilterType:
            f = FilterSpec(
                filter_type=ft,
                field=FieldRef(table="T", column="C"),
            )
            assert f.filter_type == ft

    def test_report_level_filter(self):
        f = FilterSpec(
            filter_type=FilterType.REPORT_FILTER,
            field=FieldRef(table="Calendar", column="Year"),
            label="Year",
            default_value=2024,
            multi_select=False,
        )
        assert f.filter_type == FilterType.REPORT_FILTER
        assert f.default_value == 2024
        assert f.multi_select is False

    def test_tooltip_page_reference(self):
        """Interaction config can reference tooltip pages."""
        config = InteractionConfig(
            tooltip_pages=["page-tooltip-kpi"],
        )
        assert "page-tooltip-kpi" in config.tooltip_pages


# ─────────────────────────────────────────────────────────────────────────────
# 7. Mock data narrative and patterns
# ─────────────────────────────────────────────────────────────────────────────


class TestMockDataNarrative:
    """Test mock data narrative / pattern specification."""

    def test_narrative_scenario(self, retail_narrative: MockDataNarrative):
        assert "UK retailer" in retail_narrative.scenario_description
        assert retail_narrative.time_period == "FY2023-FY2024"

    def test_narrative_patterns(self, retail_narrative: MockDataNarrative):
        assert len(retail_narrative.patterns) == 5
        types = {p.pattern_type for p in retail_narrative.patterns}
        assert DataPatternType.YOY_GROWTH in types
        assert DataPatternType.SEASONAL in types
        assert DataPatternType.CONCENTRATION in types
        assert DataPatternType.OUTLIER_NEGATIVE in types
        assert DataPatternType.TREND_UP in types

    def test_pattern_parameters(self, retail_narrative: MockDataNarrative):
        yoy = next(
            p for p in retail_narrative.patterns
            if p.pattern_type == DataPatternType.YOY_GROWTH
        )
        assert yoy.parameters["growth_rate"] == 0.08

    def test_pattern_field_references(self, retail_narrative: MockDataNarrative):
        yoy = next(
            p for p in retail_narrative.patterns
            if p.pattern_type == DataPatternType.YOY_GROWTH
        )
        assert len(yoy.applies_to) == 1
        assert yoy.applies_to[0].measure == "Total Revenue"

    def test_key_insights(self, retail_narrative: MockDataNarrative):
        assert len(retail_narrative.key_insights) == 4
        assert any("London" in insight for insight in retail_narrative.key_insights)

    def test_constraints(self, retail_narrative: MockDataNarrative):
        assert len(retail_narrative.constraints) == 3
        assert any("positive" in c for c in retail_narrative.constraints)

    def test_all_pattern_types_constructable(self):
        """Every DataPatternType can be used in a DataPattern."""
        for pt in DataPatternType:
            pattern = DataPattern(
                pattern_type=pt,
                description=f"Test {pt.value}",
            )
            assert pattern.pattern_type == pt

    def test_narrative_in_full_spec(self, full_retail_spec: DashboardSpec):
        assert full_retail_spec.mock_data_narrative is not None
        assert len(full_retail_spec.mock_data_narrative.patterns) > 0

    def test_narrative_optional(self):
        """A spec without a mock data narrative is valid."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="Minimal", business_purpose="Test"),
        )
        assert spec.mock_data_narrative is None


# ─────────────────────────────────────────────────────────────────────────────
# Additional coverage: theme and design system
# ─────────────────────────────────────────────────────────────────────────────


class TestThemeDesignSystem:
    """Test theme/design system representation."""

    def test_theme_structure(self, retail_theme: ThemeSpec):
        assert retail_theme.presentation_mode == PresentationMode.LIGHT
        assert retail_theme.style_family == "corporate_restrained"
        assert len(retail_theme.colour_roles) == 5
        assert retail_theme.density == DensityPreference.COMFORTABLE

    def test_colour_roles(self, retail_theme: ThemeSpec):
        primary = next(c for c in retail_theme.colour_roles if c.role == "primary")
        assert primary.hex_value == "#1B365D"
        # Some roles leave hex_value for renderer to decide
        accent = next(c for c in retail_theme.colour_roles if c.role == "accent")
        assert accent.hex_value == ""

    def test_typography(self, retail_theme: ThemeSpec):
        assert retail_theme.typography.heading_font == "Segoe UI Semibold"
        assert retail_theme.typography.body_font == "Segoe UI"
        assert retail_theme.typography.base_size_pt == 10

    def test_emphasis_rules(self, retail_theme: ThemeSpec):
        assert len(retail_theme.emphasis_rules) == 3

    def test_dark_mode(self):
        theme = ThemeSpec(presentation_mode=PresentationMode.DARK)
        assert theme.presentation_mode == PresentationMode.DARK

    def test_minimal_theme_valid(self):
        """A theme with all defaults is valid."""
        theme = ThemeSpec()
        assert theme.presentation_mode == PresentationMode.LIGHT
        assert theme.density == DensityPreference.COMFORTABLE


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases and minimal specs."""

    def test_minimal_valid_spec(self):
        """The absolute minimum valid spec."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="Minimal", business_purpose="Test"),
        )
        assert spec.intent.title == "Minimal"
        assert spec.pages == []
        assert spec.tables == []
        assert spec.revision.version == 1

    def test_auto_generated_ids(self):
        """IDs are auto-generated if not provided."""
        page = PageSpec(title="Auto ID", role=PageRole.DETAIL)
        assert page.id != ""
        assert len(page.id) > 10  # UUID-style

        vis = VisualSpec(
            visual_type=VisualType.CARD,
            title="Auto",
            value_fields=[FieldRef(table="T", measure="M")],
        )
        assert vis.id != ""

    def test_unique_auto_generated_ids(self):
        """Auto-generated IDs are unique."""
        pages = [PageSpec(title=f"Page {i}", role=PageRole.DETAIL) for i in range(10)]
        ids = [p.id for p in pages]
        assert len(set(ids)) == 10

    def test_field_ref_column_only(self):
        ref = FieldRef(table="Sales", column="Revenue")
        assert ref.column == "Revenue"
        assert ref.measure == ""

    def test_field_ref_measure_only(self):
        ref = FieldRef(table="Sales", measure="Total Revenue")
        assert ref.measure == "Total Revenue"
        assert ref.column == ""

    def test_large_spec_serializes(self):
        """A spec with many pages/visuals serializes correctly."""
        pages = []
        for i in range(10):
            visuals = [
                VisualSpec(
                    id=f"vis-{i}-{j}",
                    visual_type=VisualType.CARD,
                    title=f"Card {j}",
                    value_fields=[FieldRef(table="T", measure="M")],
                )
                for j in range(20)
            ]
            pages.append(
                PageSpec(id=f"page-{i}", title=f"Page {i}", visuals=visuals)
            )

        spec = DashboardSpec(
            intent=DashboardIntent(title="Large", business_purpose="Scale test"),
            pages=pages,
        )
        json_str = spec.model_dump_json()
        restored = DashboardSpec.model_validate_json(json_str)
        assert len(restored.pages) == 10
        assert len(restored.pages[0].visuals) == 20
