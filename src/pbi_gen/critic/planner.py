"""Revision planner — converts visual critique into actionable changes."""

from __future__ import annotations

from pbi_gen.critic.models import (
    CritiqueIssue,
    IssueOwner,
    IssueSeverity,
    RevisionAction,
    RevisionPlan,
    VisualCritique,
)


def create_revision_plan(critique: VisualCritique, *, max_actions: int = 5) -> RevisionPlan:
    """Convert a VisualCritique into a structured RevisionPlan.

    Prioritizes high-impact, low-risk, actionable changes.
    Defers platform-limited and non-actionable issues.

    Args:
        critique: The structured visual critique.
        max_actions: Maximum actions to include in the plan.

    Returns:
        RevisionPlan with ordered actions and deferred items.
    """
    actionable = []
    deferred = []

    for issue in critique.issues:
        if issue.owner in (IssueOwner.POWERBI_LIMIT, IssueOwner.NON_ACTIONABLE):
            deferred.append(f"{issue.id}: {issue.observed} ({issue.owner.value})")
            continue

        # Score for prioritization: severity * confidence
        severity_weight = {
            IssueSeverity.CRITICAL: 5,
            IssueSeverity.HIGH: 4,
            IssueSeverity.MEDIUM: 3,
            IssueSeverity.LOW: 2,
            IssueSeverity.INFO: 1,
        }
        score = severity_weight.get(issue.severity, 1) * issue.confidence
        actionable.append((score, issue))

    # Sort by priority score (highest first)
    actionable.sort(key=lambda x: x[0], reverse=True)

    # Convert top issues into actions
    actions = []
    for idx, (score, issue) in enumerate(actionable[:max_actions]):
        # Map owner to target
        target_map = {
            IssueOwner.DESIGNER: "spec",
            IssueOwner.RENDERER: "renderer",
            IssueOwner.THEME: "theme",
            IssueOwner.LAYOUT: "layout",
        }
        target = target_map.get(issue.owner, "renderer")

        # Assess risk based on target
        risk_map = {
            "spec": "Medium — may change analytical content",
            "renderer": "Low — formatting only",
            "theme": "Low — visual styling only",
            "layout": "Low-Medium — may affect visual positioning",
        }

        actions.append(RevisionAction(
            id=f"rev-{idx + 1}",
            priority=idx + 1,
            target=target,
            description=issue.action,
            issue_ids=[issue.id],
            estimated_impact=issue.desired,
            risk=risk_map.get(target, "Low"),
        ))

    # Build rationale
    if actions:
        rationale = (
            f"Selected {len(actions)} highest-impact actionable issues from "
            f"{len(critique.issues)} total. "
            f"Deferred {len(deferred)} platform-limited/non-actionable items."
        )
    else:
        rationale = "No actionable issues found — all gaps are platform-limited or non-actionable."

    return RevisionPlan(
        actions=actions,
        deferred=deferred,
        rationale=rationale,
    )


def should_stop(
    critique: VisualCritique,
    iteration: int,
    *,
    max_iterations: int = 3,
    min_score: float = 7.0,
    min_improvement: float = 0.3,
    previous_score: float | None = None,
) -> tuple[bool, str]:
    """Determine whether the critic loop should stop.

    Args:
        critique: Current iteration's critique.
        iteration: Current iteration number (1-based).
        max_iterations: Maximum allowed iterations.
        min_score: Score above which we consider "good enough".
        min_improvement: Minimum score improvement to justify continuing.
        previous_score: Previous iteration's overall score.

    Returns:
        Tuple of (should_stop, reason).
    """
    # Check iteration limit
    if iteration >= max_iterations:
        return True, f"Maximum iterations reached ({max_iterations})"

    # Check if score is already good
    if critique.scores.overall >= min_score:
        return True, f"Score {critique.scores.overall:.1f} meets minimum threshold {min_score}"

    # Check for no critical/high actionable issues
    actionable_severe = [
        i for i in critique.issues
        if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)
        and i.owner not in (IssueOwner.POWERBI_LIMIT, IssueOwner.NON_ACTIONABLE)
    ]
    if not actionable_severe:
        return True, "No critical/high-severity actionable issues remain"

    # Check improvement stall
    if previous_score is not None:
        improvement = critique.scores.overall - previous_score
        if improvement < min_improvement:
            return True, f"Improvement ({improvement:.2f}) below threshold ({min_improvement})"

    return False, ""
