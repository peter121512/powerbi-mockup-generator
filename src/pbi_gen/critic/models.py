"""Data models for the visual critic loop."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """Severity of a visual critique issue."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueOwner(str, Enum):
    """Which system component owns the fix for an issue."""

    DESIGNER = "designer"
    RENDERER = "renderer"
    THEME = "theme"
    LAYOUT = "layout"
    POWERBI_LIMIT = "powerbi_limit"
    NON_ACTIONABLE = "non_actionable_reference_gap"


class CritiqueIssue(BaseModel):
    """A single issue identified by the visual critic."""

    id: str = Field(description="Short issue identifier")
    severity: IssueSeverity
    dimension: str = Field(description="Which quality dimension this affects")
    page_id: Optional[str] = None
    visual_id: Optional[str] = None
    observed: str = Field(description="What was observed in the actual screenshot")
    desired: str = Field(description="What the desired state would be")
    owner: IssueOwner
    action: str = Field(description="Recommended concrete action")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the recommendation")


class CritiqueDimensions(BaseModel):
    """Scored dimensions of the critique."""

    overall: float = Field(ge=0.0, le=10.0)
    executive_credibility: float = Field(ge=0.0, le=10.0)
    information_hierarchy: float = Field(ge=0.0, le=10.0)
    visual_density: float = Field(ge=0.0, le=10.0)
    whitespace: float = Field(ge=0.0, le=10.0)
    alignment_grid: float = Field(ge=0.0, le=10.0)
    kpi_prominence: float = Field(ge=0.0, le=10.0)
    typography_readability: float = Field(ge=0.0, le=10.0)
    colour_consistency: float = Field(ge=0.0, le=10.0)
    chart_appropriateness: float = Field(ge=0.0, le=10.0)
    chart_legibility: float = Field(ge=0.0, le=10.0)
    filter_placement: float = Field(ge=0.0, le=10.0)
    data_storytelling: float = Field(ge=0.0, le=10.0)
    polish_premium: float = Field(ge=0.0, le=10.0)
    reference_fidelity: float = Field(ge=0.0, le=10.0)
    implementation_feasibility: float = Field(ge=0.0, le=10.0)


class VisualCritique(BaseModel):
    """Structured output from the visual critic."""

    scores: CritiqueDimensions
    issues: list[CritiqueIssue] = Field(default_factory=list)
    summary: str = Field(description="Brief overall assessment")
    reference_rejected_ideas: list[str] = Field(
        default_factory=list,
        description="Ideas from reference image rejected as impractical or non-analytical",
    )


class RevisionAction(BaseModel):
    """A single actionable revision from the plan."""

    id: str
    priority: int = Field(ge=1, description="1=highest priority")
    target: str = Field(description="What to change: spec, renderer, theme, layout")
    description: str
    issue_ids: list[str] = Field(description="Critique issues this addresses")
    estimated_impact: str = Field(description="Expected visual improvement")
    risk: str = Field(description="Risk of breaking something")


class RevisionPlan(BaseModel):
    """Structured revision plan from critique findings."""

    actions: list[RevisionAction] = Field(default_factory=list)
    deferred: list[str] = Field(
        default_factory=list,
        description="Issues deferred as platform-limited or non-actionable",
    )
    rationale: str = Field(description="Why these actions were chosen")


class VisualReferenceResult(BaseModel):
    """Result of generating a visual reference image."""

    success: bool
    output_path: Optional[str] = None
    model: str = ""
    prompt_summary: str = ""
    elapsed_seconds: float = 0.0
    error: Optional[str] = None


class ScreenshotOutcome(str, Enum):
    """Outcome of a screenshot capture attempt."""

    SUCCESS = "success"
    AUTH_FAILURE = "auth_failure"
    EMBED_FAILURE = "embed_failure"
    LOAD_TIMEOUT = "load_timeout"
    RENDER_TIMEOUT = "render_timeout"
    BROWSER_FAILURE = "browser_failure"
    NOT_ATTEMPTED = "not_attempted"


class ScreenshotResult(BaseModel):
    """Result of capturing a report page screenshot."""

    outcome: ScreenshotOutcome
    output_path: Optional[str] = None
    elapsed_seconds: float = 0.0
    error: Optional[str] = None
    console_errors: list[str] = Field(default_factory=list)


class LoopIterationResult(BaseModel):
    """Result of a single critic loop iteration."""

    iteration: int
    critique: Optional[VisualCritique] = None
    revision_plan: Optional[RevisionPlan] = None
    actions_applied: list[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    deployed: bool = False
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    stopped_reason: Optional[str] = None
