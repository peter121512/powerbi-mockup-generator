"""Canonical DashboardSpec — the structured contract between designer, data-generation,
rendering, deployment, critique, and revision components.

This module replaces the shallow legacy schema with a rich specification capable of
supporting enterprise-grade Power BI dashboard generation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class PageRole(str, Enum):
    """The functional role of a report page."""

    EXECUTIVE_OVERVIEW = "executive_overview"
    DIAGNOSTIC = "diagnostic"
    DETAIL = "detail"
    DRILL_THROUGH = "drill_through"
    TOOLTIP = "tooltip"
    NAVIGATION = "navigation"


class VisualType(str, Enum):
    """Supported Power BI visual types.

    This enum covers the most common types. The string value matches Power BI
    internal identifiers where practical.  Additional types can be added without
    breaking existing specs.
    """

    BAR_CHART = "barChart"
    CLUSTERED_BAR = "clusteredBarChart"
    STACKED_BAR = "stackedBarChart"
    COLUMN_CHART = "columnChart"
    CLUSTERED_COLUMN = "clusteredColumnChart"
    STACKED_COLUMN = "stackedColumnChart"
    LINE_CHART = "lineChart"
    AREA_CHART = "areaChart"
    COMBO_CHART = "comboChart"
    CARD = "card"
    MULTI_ROW_CARD = "multiRowCard"
    KPI = "kpi"
    TABLE = "table"
    MATRIX = "matrix"
    DONUT_CHART = "donutChart"
    PIE_CHART = "pieChart"
    FUNNEL = "funnel"
    TREEMAP = "treemap"
    MAP = "map"
    FILLED_MAP = "filledMap"
    SCATTER = "scatterChart"
    WATERFALL = "waterfall"
    GAUGE = "gauge"
    SLICER = "slicer"
    RIBBON = "ribbonChart"
    DECOMPOSITION_TREE = "decompositionTree"
    KEY_INFLUENCERS = "keyInfluencers"
    SHAPE_MAP = "shapeMap"
    TEXT_BOX = "textBox"
    IMAGE = "image"
    BUTTON = "button"


class AggregationType(str, Enum):
    """Standard DAX aggregation functions."""

    SUM = "Sum"
    COUNT = "Count"
    COUNT_DISTINCT = "CountDistinct"
    AVERAGE = "Average"
    MIN = "Min"
    MAX = "Max"
    NONE = "None"


class RelationshipCardinality(str, Enum):
    """Cardinality options for table relationships."""

    ONE_TO_MANY = "oneToMany"
    MANY_TO_ONE = "manyToOne"
    ONE_TO_ONE = "oneToOne"
    MANY_TO_MANY = "manyToMany"


class CrossFilterDirection(str, Enum):
    """Cross-filter direction for relationships."""

    SINGLE = "single"
    BOTH = "both"


class FilterType(str, Enum):
    """Types of filters / slicers in the report."""

    SLICER = "slicer"
    PAGE_FILTER = "page_filter"
    REPORT_FILTER = "report_filter"
    VISUAL_FILTER = "visual_filter"
    DRILL_THROUGH_FILTER = "drill_through_filter"


class InteractionType(str, Enum):
    """Cross-visual interaction behaviour."""

    CROSS_FILTER = "cross_filter"
    CROSS_HIGHLIGHT = "cross_highlight"
    NONE = "none"


class DataPatternType(str, Enum):
    """Types of analytical patterns for mock data generation.

    These describe the business story the data should tell, not random distributions.
    """

    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    SEASONAL = "seasonal"
    CYCLICAL = "cyclical"
    VARIANCE_HIGH = "variance_high"
    VARIANCE_LOW = "variance_low"
    OUTLIER_POSITIVE = "outlier_positive"
    OUTLIER_NEGATIVE = "outlier_negative"
    TARGET_MISS = "target_miss"
    TARGET_HIT = "target_hit"
    CONCENTRATION = "concentration"
    EVEN_DISTRIBUTION = "even_distribution"
    RANKING_CLEAR = "ranking_clear"
    FUNNEL_PROGRESSION = "funnel_progression"
    YOY_GROWTH = "yoy_growth"
    YOY_DECLINE = "yoy_decline"
    PARETO = "pareto"
    FLAT = "flat"


class PresentationMode(str, Enum):
    """High-level presentation mode."""

    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"


class DensityPreference(str, Enum):
    """Information density preference."""

    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


class ConfidenceDimension(str, Enum):
    """Dimensions along which the system may be uncertain about a spec decision."""

    AUDIENCE_CLARITY = "audience_clarity"
    METRIC_DEFINITIONS = "metric_definitions"
    DATA_AVAILABILITY = "data_availability"
    VISUAL_CHOICE = "visual_choice"
    LAYOUT_DECISION = "layout_decision"
    FILTER_REQUIREMENTS = "filter_requirements"
    BUSINESS_CONTEXT = "business_context"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


# ─────────────────────────────────────────────────────────────────────────────
# Confidence and Assumptions
# ─────────────────────────────────────────────────────────────────────────────


class Assumption(BaseModel):
    """A single assumption made during spec generation."""

    statement: str = Field(..., description="What was assumed.")
    reasoning: str = Field("", description="Why this assumption was made.")
    impact: str = Field(
        "", description="What would change if this assumption were wrong."
    )
    clarification_question: str = Field(
        "",
        description="Question to ask the user if this assumption should be validated.",
    )


class ConfidenceAssessment(BaseModel):
    """Structured confidence/uncertainty for a spec decision.

    Rather than an arbitrary percentage, this captures the *evidence* for
    confidence along specific dimensions so a deterministic gate can later
    derive a go/no-go decision.
    """

    dimension: ConfidenceDimension
    evidence_for: list[str] = Field(
        default_factory=list,
        description="Evidence supporting the current decision.",
    )
    evidence_against: list[str] = Field(
        default_factory=list,
        description="Evidence or gaps suggesting the decision may be wrong.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved questions that would improve confidence.",
    )


class SpecConfidence(BaseModel):
    """Top-level confidence container for the full spec."""

    assessments: list[ConfidenceAssessment] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    requires_clarification: bool = Field(
        False,
        description="True if any assumption is critical enough to warrant user input before proceeding.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────────────────────────────────────


class ColumnSpec(BaseModel):
    """Specification for a table column."""

    name: str
    data_type: str = Field(
        ..., description="Data type: TEXT, INTEGER, REAL, DATE, DATETIME, BOOLEAN"
    )
    description: str = ""
    is_key: bool = False
    sample_values: list[str] = Field(
        default_factory=list,
        description="Example values to guide realistic data generation.",
    )


class TableSpec(BaseModel):
    """Specification for a semantic model table."""

    name: str
    description: str = ""
    columns: list[ColumnSpec] = Field(default_factory=list)
    row_count_hint: int = Field(
        50, description="Suggested number of rows for mock data generation."
    )


class Relationship(BaseModel):
    """A relationship between two tables in the semantic model."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: RelationshipCardinality = RelationshipCardinality.MANY_TO_ONE
    cross_filter_direction: CrossFilterDirection = CrossFilterDirection.SINGLE
    is_active: bool = True


class MeasureSpec(BaseModel):
    """A DAX measure definition."""

    name: str
    expression: str = Field(..., description="DAX expression.")
    table: str = Field("", description="Home table for the measure.")
    format_string: str = Field("", description="DAX format string, e.g. '#,0'.")
    description: str = ""


class FieldRef(BaseModel):
    """Reference to a table column or measure for use in visual bindings."""

    table: str
    column: str = Field("", description="Column name. Empty if referencing a measure.")
    measure: str = Field("", description="Measure name. Empty if referencing a column.")
    aggregation: AggregationType = AggregationType.NONE

    @model_validator(mode="after")
    def _column_or_measure(self) -> "FieldRef":
        if not self.column and not self.measure:
            raise ValueError("FieldRef must specify either column or measure.")
        if self.column and self.measure:
            raise ValueError("FieldRef must specify column OR measure, not both.")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Mock Data Narrative
# ─────────────────────────────────────────────────────────────────────────────


class DataPattern(BaseModel):
    """A required analytical pattern that mock data must exhibit."""

    pattern_type: DataPatternType
    description: str = Field(
        "", description="Narrative explanation of the pattern for data generation."
    )
    applies_to: list[FieldRef] = Field(
        default_factory=list,
        description="Fields/measures that should exhibit this pattern.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Pattern-specific parameters, e.g. growth_rate, outlier_magnitude.",
    )


class MockDataNarrative(BaseModel):
    """Describes the business story that mock data should tell.

    This drives coherent, story-driven data generation rather than arbitrary
    random values.
    """

    scenario_description: str = Field(
        ...,
        description="High-level description of the business scenario the data represents.",
    )
    time_period: str = Field(
        "", description="Time period the data covers, e.g. 'FY2023-FY2024'."
    )
    patterns: list[DataPattern] = Field(default_factory=list)
    key_insights: list[str] = Field(
        default_factory=list,
        description="Insights that should be discoverable in the generated data.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Hard constraints, e.g. 'margins must be positive', 'total must reconcile'.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Theme / Design System
# ─────────────────────────────────────────────────────────────────────────────


class ColourRole(BaseModel):
    """A semantic colour assignment rather than a fixed hex value."""

    role: str = Field(
        ..., description="Semantic role, e.g. 'primary', 'accent', 'positive', 'negative', 'neutral'."
    )
    intent: str = Field(
        "", description="What this colour communicates, e.g. 'growth / success'."
    )
    hex_value: str = Field(
        "",
        description="Optional explicit colour. If empty, the renderer chooses from the style family.",
    )


class TypographySpec(BaseModel):
    """Typography hierarchy preferences."""

    heading_font: str = Field("", description="Font family for headings.")
    body_font: str = Field("", description="Font family for body/data text.")
    base_size_pt: float = Field(
        0, description="Base font size in points. 0 = renderer default."
    )


class ThemeSpec(BaseModel):
    """Structured design intent for the dashboard's visual system."""

    presentation_mode: PresentationMode = PresentationMode.LIGHT
    style_family: str = Field(
        "",
        description="Named enterprise style, e.g. 'corporate_restrained', 'modern_bold', 'editorial'.",
    )
    colour_roles: list[ColourRole] = Field(default_factory=list)
    typography: TypographySpec = Field(default_factory=TypographySpec)
    density: DensityPreference = DensityPreference.COMFORTABLE
    whitespace_emphasis: str = Field(
        "",
        description="Guidance on whitespace treatment, e.g. 'generous padding between cards'.",
    )
    card_style: str = Field(
        "",
        description="Card/surface treatment, e.g. 'subtle shadow', 'flat with border', 'elevated'.",
    )
    emphasis_rules: list[str] = Field(
        default_factory=list,
        description="Rules for visual emphasis, e.g. 'KPIs are largest', 'negative variance in red'.",
    )
    design_tone: str = Field(
        "",
        description="Overall design tone, e.g. 'premium and restrained', 'vibrant and data-dense'.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Visuals
# ─────────────────────────────────────────────────────────────────────────────


class ConditionalFormat(BaseModel):
    """Conditional formatting intent for a visual."""

    target_field: FieldRef
    rule_description: str = Field(
        ..., description="Human-readable rule, e.g. 'Red if < 0, green if >= target'."
    )
    colour_positive: str = Field("", description="Colour for positive/good values.")
    colour_negative: str = Field("", description="Colour for negative/bad values.")


class SortSpec(BaseModel):
    """Sort intent for a visual."""

    field: FieldRef
    descending: bool = True


class TooltipSpec(BaseModel):
    """Tooltip configuration for a visual."""

    fields: list[FieldRef] = Field(default_factory=list)
    tooltip_page_id: str = Field(
        "",
        description="ID of a tooltip page to use as enhanced tooltip.",
    )


class VisualPosition(BaseModel):
    """Position and size of a visual within the page grid.

    Uses a 12-column grid system by default (column-based) with row positions.
    """

    x: int = Field(0, description="Grid column start (0-based).")
    y: int = Field(0, description="Grid row start (0-based).")
    width: int = Field(4, description="Width in grid columns.")
    height: int = Field(4, description="Height in grid rows.")


class VisualSpec(BaseModel):
    """Rich specification for a single report visual."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable visual identifier. Persists across revisions.",
    )
    visual_type: VisualType
    title: str
    subtitle: str = ""
    analytical_purpose: str = Field(
        "",
        description="The analytical question this visual answers.",
    )
    # Field bindings
    category_fields: list[FieldRef] = Field(default_factory=list)
    value_fields: list[FieldRef] = Field(default_factory=list)
    series_field: FieldRef | None = None
    # Layout
    position: VisualPosition = Field(default_factory=VisualPosition)
    priority: int = Field(
        5,
        description="Visual hierarchy priority (1=highest). Influences size/placement.",
    )
    # Formatting
    formatting_intent: str = Field(
        "",
        description="Design intent for formatting, e.g. 'no data labels, emphasize trend'.",
    )
    conditional_formats: list[ConditionalFormat] = Field(default_factory=list)
    sort: SortSpec | None = None
    tooltip: TooltipSpec = Field(default_factory=TooltipSpec)
    # Interaction
    interaction_type: InteractionType = InteractionType.CROSS_HIGHLIGHT
    drill_through_target: str = Field(
        "", description="Page ID for drill-through navigation."
    )
    # Accessibility
    alt_description: str = Field(
        "",
        description="Accessibility description for screen readers.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Filters and Interactions
# ─────────────────────────────────────────────────────────────────────────────


class FilterSpec(BaseModel):
    """A filter or slicer specification."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    filter_type: FilterType
    field: FieldRef
    label: str = ""
    default_value: Any = Field(
        None, description="Default filter value if applicable."
    )
    multi_select: bool = True
    visual_style: str = Field(
        "", description="Slicer visual style, e.g. 'dropdown', 'list', 'slider', 'between'."
    )


class DrillThroughConfig(BaseModel):
    """Drill-through configuration between pages."""

    source_page_id: str
    target_page_id: str
    filter_fields: list[FieldRef] = Field(default_factory=list)
    description: str = ""


class NavigationButton(BaseModel):
    """Page navigation button specification."""

    label: str
    target_page_id: str
    style: str = Field("", description="Button visual style.")


class InteractionConfig(BaseModel):
    """Report-level interaction and navigation configuration."""

    drill_throughs: list[DrillThroughConfig] = Field(default_factory=list)
    navigation_buttons: list[NavigationButton] = Field(default_factory=list)
    default_interaction: InteractionType = InteractionType.CROSS_HIGHLIGHT
    tooltip_pages: list[str] = Field(
        default_factory=list, description="Page IDs designated as tooltip pages."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────


class PageLayout(BaseModel):
    """Page layout configuration."""

    width: int = Field(1280, description="Page width in pixels.")
    height: int = Field(720, description="Page height in pixels.")
    grid_columns: int = Field(12, description="Number of grid columns for layout.")
    grid_rows: int = Field(8, description="Number of grid rows for layout.")


class PageSpec(BaseModel):
    """A single report page specification."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable page identifier. Persists across revisions.",
    )
    title: str
    purpose: str = Field("", description="What this page helps the user understand.")
    role: PageRole = PageRole.EXECUTIVE_OVERVIEW
    layout: PageLayout = Field(default_factory=PageLayout)
    visuals: list[VisualSpec] = Field(default_factory=list)
    filters: list[FilterSpec] = Field(default_factory=list)
    navigation: list[NavigationButton] = Field(default_factory=list)
    sort_order: int = Field(
        0, description="Page display order within the report."
    )

    @model_validator(mode="after")
    def _unique_visual_ids(self) -> "PageSpec":
        ids = [v.id for v in self.visuals]
        duplicates = [x for x in ids if ids.count(x) > 1]
        if duplicates:
            raise ValueError(
                f"Duplicate visual IDs on page '{self.title}': {set(duplicates)}"
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard-Level Intent
# ─────────────────────────────────────────────────────────────────────────────


class DashboardIntent(BaseModel):
    """High-level intent and context for the dashboard."""

    title: str
    business_purpose: str = Field(
        ..., description="The analytical objective this dashboard serves."
    )
    intended_audience: str = Field(
        "", description="Who will use this dashboard, e.g. 'CEO and CFO'."
    )
    business_domain: str = Field(
        "", description="Inferred business domain, e.g. 'retail', 'healthcare', 'finance'."
    )
    design_tone: str = Field(
        "",
        description="Desired visual tone, e.g. 'premium and boardroom-ready'.",
    )
    key_questions: list[str] = Field(
        default_factory=list,
        description="The key analytical questions this dashboard answers.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Revision Metadata
# ─────────────────────────────────────────────────────────────────────────────


class RevisionMetadata(BaseModel):
    """Metadata for tracking specification versions and conversational iteration."""

    spec_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this specification instance.",
    )
    version: int = Field(1, description="Monotonically increasing version number.")
    parent_spec_id: str = Field(
        "",
        description="spec_id of the previous version. Empty for first generation.",
    )
    created_at: datetime = Field(default_factory=datetime.now)
    amendment_summary: str = Field(
        "",
        description="What changed in this revision relative to the parent.",
    )
    revision_reason: str = Field(
        "",
        description="Why this revision was made, e.g. 'user requested more filters'.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Top-Level DashboardSpec
# ─────────────────────────────────────────────────────────────────────────────


class DashboardSpec(BaseModel):
    """Complete canonical dashboard specification.

    This is the single structured contract that flows between all pipeline
    components: designer → data-generator → renderer → deployer → critic → reviser.
    """

    # Intent and identity
    intent: DashboardIntent
    revision: RevisionMetadata = Field(default_factory=RevisionMetadata)

    # Structure
    pages: list[PageSpec] = Field(default_factory=list)

    # Interactions
    interactions: InteractionConfig = Field(default_factory=InteractionConfig)

    # Design system
    theme: ThemeSpec = Field(default_factory=ThemeSpec)

    # Data model
    tables: list[TableSpec] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    measures: list[MeasureSpec] = Field(default_factory=list)

    # Mock data story
    mock_data_narrative: MockDataNarrative | None = None

    # Confidence and assumptions
    confidence: SpecConfidence = Field(default_factory=SpecConfidence)

    @model_validator(mode="after")
    def _unique_page_ids(self) -> "DashboardSpec":
        ids = [p.id for p in self.pages]
        duplicates = [x for x in ids if ids.count(x) > 1]
        if duplicates:
            raise ValueError(f"Duplicate page IDs: {set(duplicates)}")
        return self
