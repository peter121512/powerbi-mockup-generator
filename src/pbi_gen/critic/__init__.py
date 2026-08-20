"""Visual reference generation, critique, and revision loop."""

from pbi_gen.critic.models import (
    VisualCritique,
    CritiqueIssue,
    IssueSeverity,
    IssueOwner,
    RevisionPlan,
    RevisionAction,
    VisualReferenceResult,
    ScreenshotResult,
    ScreenshotOutcome,
    LoopIterationResult,
)
from pbi_gen.critic.reference import generate_visual_reference
from pbi_gen.critic.critic import critique_visuals
from pbi_gen.critic.screenshot import capture_report_page
from pbi_gen.critic.planner import create_revision_plan
from pbi_gen.critic.loop import run_critic_loop

__all__ = [
    "VisualCritique",
    "CritiqueIssue",
    "IssueSeverity",
    "IssueOwner",
    "RevisionPlan",
    "RevisionAction",
    "VisualReferenceResult",
    "ScreenshotResult",
    "ScreenshotOutcome",
    "LoopIterationResult",
    "generate_visual_reference",
    "critique_visuals",
    "capture_report_page",
    "create_revision_plan",
    "run_critic_loop",
]
