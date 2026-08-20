"""Tests for the visual critic module — unit tests (no live API calls)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pbi_gen.critic.models import (
    CritiqueDimensions,
    CritiqueIssue,
    IssueOwner,
    IssueSeverity,
    LoopIterationResult,
    RevisionAction,
    RevisionPlan,
    ScreenshotOutcome,
    ScreenshotResult,
    VisualCritique,
    VisualReferenceResult,
)
from pbi_gen.critic.planner import create_revision_plan, should_stop
from pbi_gen.critic.reference import _build_reference_prompt


# ─────────────────────────────────────────────────────────────────────────────
# Model tests
# ─────────────────────────────────────────────────────────────────────────────


def test_visual_reference_result_success():
    r = VisualReferenceResult(success=True, output_path="/tmp/ref.png", model="gpt-image-2", elapsed_seconds=10.5)
    assert r.success
    assert r.model == "gpt-image-2"


def test_visual_reference_result_failure():
    r = VisualReferenceResult(success=False, error="API error", model="gpt-image-2")
    assert not r.success
    assert "API error" in r.error


def test_screenshot_result_outcomes():
    for outcome in ScreenshotOutcome:
        r = ScreenshotResult(outcome=outcome)
        assert r.outcome == outcome


def test_critique_dimensions_valid_range():
    dims = CritiqueDimensions(
        overall=7.5, executive_credibility=8.0, information_hierarchy=6.5,
        visual_density=7.0, whitespace=7.5, alignment_grid=8.0,
        kpi_prominence=9.0, typography_readability=7.5, colour_consistency=8.0,
        chart_appropriateness=7.0, chart_legibility=6.5, filter_placement=5.0,
        data_storytelling=7.0, polish_premium=6.5, reference_fidelity=5.5,
        implementation_feasibility=9.0,
    )
    assert dims.overall == 7.5
    assert dims.implementation_feasibility == 9.0


def test_critique_issue_model():
    issue = CritiqueIssue(
        id="test-1",
        severity=IssueSeverity.HIGH,
        dimension="kpi_prominence",
        observed="Cards have no labels",
        desired="Cards should have descriptive titles",
        owner=IssueOwner.RENDERER,
        action="Add title property to card visuals",
        confidence=0.95,
    )
    assert issue.severity == IssueSeverity.HIGH
    assert issue.owner == IssueOwner.RENDERER
    assert issue.confidence == 0.95


def test_visual_critique_full():
    critique = VisualCritique(
        scores=CritiqueDimensions(
            overall=5.0, executive_credibility=5.0, information_hierarchy=5.0,
            visual_density=5.0, whitespace=5.0, alignment_grid=5.0,
            kpi_prominence=5.0, typography_readability=5.0, colour_consistency=5.0,
            chart_appropriateness=5.0, chart_legibility=5.0, filter_placement=5.0,
            data_storytelling=5.0, polish_premium=5.0, reference_fidelity=5.0,
            implementation_feasibility=5.0,
        ),
        issues=[
            CritiqueIssue(
                id="i1", severity=IssueSeverity.HIGH, dimension="kpi_prominence",
                observed="no titles", desired="titles visible",
                owner=IssueOwner.RENDERER, action="add titles", confidence=0.9,
            ),
        ],
        summary="Mediocre dashboard",
        reference_rejected_ideas=["3D effects"],
    )
    assert critique.scores.overall == 5.0
    assert len(critique.issues) == 1
    assert critique.reference_rejected_ideas == ["3D effects"]


# ─────────────────────────────────────────────────────────────────────────────
# Planner tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_critique(issues: list[CritiqueIssue], overall: float = 5.0) -> VisualCritique:
    return VisualCritique(
        scores=CritiqueDimensions(
            overall=overall, executive_credibility=5.0, information_hierarchy=5.0,
            visual_density=5.0, whitespace=5.0, alignment_grid=5.0,
            kpi_prominence=5.0, typography_readability=5.0, colour_consistency=5.0,
            chart_appropriateness=5.0, chart_legibility=5.0, filter_placement=5.0,
            data_storytelling=5.0, polish_premium=5.0, reference_fidelity=5.0,
            implementation_feasibility=5.0,
        ),
        issues=issues,
        summary="test",
    )


def test_revision_plan_prioritizes_by_severity():
    issues = [
        CritiqueIssue(id="low1", severity=IssueSeverity.LOW, dimension="a",
                      observed="x", desired="y", owner=IssueOwner.RENDERER,
                      action="do low", confidence=0.5),
        CritiqueIssue(id="crit1", severity=IssueSeverity.CRITICAL, dimension="b",
                      observed="x", desired="y", owner=IssueOwner.RENDERER,
                      action="do critical", confidence=1.0),
    ]
    plan = create_revision_plan(_make_critique(issues))
    assert plan.actions[0].issue_ids == ["crit1"]
    assert plan.actions[0].priority == 1


def test_revision_plan_defers_platform_limited():
    issues = [
        CritiqueIssue(id="pbi1", severity=IssueSeverity.HIGH, dimension="a",
                      observed="x", desired="y", owner=IssueOwner.POWERBI_LIMIT,
                      action="impossible", confidence=0.9),
        CritiqueIssue(id="fix1", severity=IssueSeverity.MEDIUM, dimension="b",
                      observed="x", desired="y", owner=IssueOwner.THEME,
                      action="fix theme", confidence=0.8),
    ]
    plan = create_revision_plan(_make_critique(issues))
    assert len(plan.actions) == 1
    assert plan.actions[0].issue_ids == ["fix1"]
    assert len(plan.deferred) == 1
    assert "pbi1" in plan.deferred[0]


def test_revision_plan_max_actions():
    issues = [
        CritiqueIssue(id=f"i{i}", severity=IssueSeverity.HIGH, dimension="a",
                      observed="x", desired="y", owner=IssueOwner.RENDERER,
                      action=f"fix {i}", confidence=0.9)
        for i in range(10)
    ]
    plan = create_revision_plan(_make_critique(issues), max_actions=3)
    assert len(plan.actions) == 3


def test_revision_plan_empty_issues():
    plan = create_revision_plan(_make_critique([]))
    assert len(plan.actions) == 0
    assert "No actionable" in plan.rationale


# ─────────────────────────────────────────────────────────────────────────────
# Stopping policy tests
# ─────────────────────────────────────────────────────────────────────────────


def test_stop_at_max_iterations():
    critique = _make_critique([], overall=5.0)
    stop, reason = should_stop(critique, iteration=3, max_iterations=3)
    assert stop
    assert "Maximum" in reason


def test_stop_when_score_high():
    critique = _make_critique([], overall=8.0)
    stop, reason = should_stop(critique, iteration=1, min_score=7.0)
    assert stop
    assert "meets minimum" in reason


def test_stop_when_no_actionable_severe_issues():
    issues = [
        CritiqueIssue(id="pbi1", severity=IssueSeverity.HIGH, dimension="a",
                      observed="x", desired="y", owner=IssueOwner.POWERBI_LIMIT,
                      action="impossible", confidence=0.9),
        CritiqueIssue(id="low1", severity=IssueSeverity.LOW, dimension="b",
                      observed="x", desired="y", owner=IssueOwner.RENDERER,
                      action="minor", confidence=0.5),
    ]
    critique = _make_critique(issues, overall=4.0)
    stop, reason = should_stop(critique, iteration=1)
    assert stop
    assert "No critical/high" in reason


def test_stop_when_improvement_stalls():
    critique = _make_critique(
        [CritiqueIssue(id="x", severity=IssueSeverity.HIGH, dimension="a",
                       observed="x", desired="y", owner=IssueOwner.RENDERER,
                       action="fix", confidence=0.9)],
        overall=4.1,
    )
    stop, reason = should_stop(critique, iteration=2, previous_score=4.0, min_improvement=0.3)
    assert stop
    assert "below threshold" in reason


def test_continue_when_improving():
    critique = _make_critique(
        [CritiqueIssue(id="x", severity=IssueSeverity.HIGH, dimension="a",
                       observed="x", desired="y", owner=IssueOwner.RENDERER,
                       action="fix", confidence=0.9)],
        overall=5.0,
    )
    stop, reason = should_stop(critique, iteration=1, previous_score=3.0)
    assert not stop


# ─────────────────────────────────────────────────────────────────────────────
# Reference prompt tests
# ─────────────────────────────────────────────────────────────────────────────


def test_reference_prompt_includes_page_info():
    """Reference prompt should include page title and visual descriptions."""
    from pbi_gen.models.dashboard_spec import (
        DashboardSpec, DashboardIntent, PageSpec, PageRole, PageLayout,
        VisualSpec, VisualType, VisualPosition, FieldRef, TableSpec, ColumnSpec,
        RevisionMetadata, ThemeSpec,
    )

    spec = DashboardSpec(
        intent=DashboardIntent(title="Test", business_purpose="Test purpose"),
        revision=RevisionMetadata(spec_id="t1", version=1),
        pages=[PageSpec(
            id="p1", title="Overview", role=PageRole.EXECUTIVE_OVERVIEW,
            layout=PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8),
            visuals=[VisualSpec(
                id="v1", visual_type=VisualType.CARD, title="Revenue",
                value_fields=[FieldRef(table="Sales", measure="Total")],
                position=VisualPosition(x=0, y=0, width=4, height=2),
            )],
        )],
        tables=[TableSpec(name="Sales", columns=[ColumnSpec(name="Amount", data_type="REAL")])],
        theme=ThemeSpec(),
    )

    prompt = _build_reference_prompt("Test requirement", spec, spec.pages[0])
    assert "Overview" in prompt
    assert "Revenue" in prompt
    assert "card" in prompt
    assert "Total" in prompt
    assert "DO NOT" in prompt
    assert "executive" in prompt.lower()


def test_reference_prompt_no_crash_on_empty_theme():
    """Should handle empty theme gracefully."""
    from pbi_gen.models.dashboard_spec import (
        DashboardSpec, DashboardIntent, PageSpec, PageRole, PageLayout,
        RevisionMetadata, ThemeSpec,
    )

    spec = DashboardSpec(
        intent=DashboardIntent(title="Test", business_purpose="Test"),
        revision=RevisionMetadata(spec_id="t1", version=1),
        pages=[PageSpec(
            id="p1", title="Page", role=PageRole.EXECUTIVE_OVERVIEW,
            layout=PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8),
            visuals=[],
        )],
        tables=[],
        theme=ThemeSpec(),
    )

    prompt = _build_reference_prompt("req", spec, spec.pages[0])
    assert "Page" in prompt
