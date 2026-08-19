"""Deterministic clarification gate.

This module decides whether a generated DashboardSpec should proceed to the
caller or whether a clarification question should be asked first.

The decision is derived from structured evidence in the spec's confidence
model — NOT from an LLM-generated confidence percentage.

GATE POLICY (tunable independently of the designer prompt):

A spec triggers clarification when ANY of the following are true:

1. A high-impact dimension has more evidence_against than evidence_for
   AND has at least one open_question.

2. A critical assumption (one whose impact would materially change the
   dashboard architecture, metrics, or audience interpretation) exists
   with a non-empty clarification_question.

3. The LLM itself flagged requires_clarification AND there is at least
   one open question or critical assumption to surface.

High-impact dimensions (where being wrong matters most):
- METRIC_DEFINITIONS
- BUSINESS_CONTEXT
- AUDIENCE_CLARITY
- DATA_AVAILABILITY

Routine design dimensions (where reasonable inference is fine):
- VISUAL_CHOICE
- LAYOUT_DECISION
- FILTER_REQUIREMENTS
- DOMAIN_KNOWLEDGE
"""

from __future__ import annotations

from dataclasses import dataclass

from pbi_gen.models.dashboard_spec import (
    ConfidenceAssessment,
    ConfidenceDimension,
    DashboardSpec,
    SpecConfidence,
)
from pbi_gen.designer.result import ClarificationRequest


# Dimensions where ambiguity materially affects the dashboard
HIGH_IMPACT_DIMENSIONS: frozenset[ConfidenceDimension] = frozenset({
    ConfidenceDimension.METRIC_DEFINITIONS,
    ConfidenceDimension.BUSINESS_CONTEXT,
    ConfidenceDimension.AUDIENCE_CLARITY,
    ConfidenceDimension.DATA_AVAILABILITY,
})

# Keywords indicating an assumption has high structural impact
CRITICAL_IMPACT_KEYWORDS: list[str] = [
    "materially",
    "entirely different",
    "fundamentally",
    "architecture",
    "wrong dashboard",
    "different report",
    "different metrics",
    "different model",
    "cannot determine",
    "contradictory",
]


@dataclass(frozen=True)
class GateDecision:
    """Result of the clarification gate evaluation."""

    should_clarify: bool
    clarification: ClarificationRequest | None = None
    triggered_rules: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.triggered_rules is None:
            object.__setattr__(self, "triggered_rules", [])


def evaluate_clarification_gate(spec: DashboardSpec) -> GateDecision:
    """Evaluate whether the spec should proceed or needs clarification.

    This is the ONLY place the clarification decision is made. The LLM
    populates evidence; this function owns the decision.

    Returns:
        GateDecision indicating whether to proceed or clarify.
    """
    confidence = spec.confidence
    triggered_rules: list[str] = []
    candidate_questions: list[tuple[str, str, list[str]]] = []  # (question, dimension, evidence)

    # Rule 1: High-impact dimension with net-negative evidence + open questions
    for assessment in confidence.assessments:
        if assessment.dimension in HIGH_IMPACT_DIMENSIONS:
            if _is_net_negative(assessment) and assessment.open_questions:
                question = assessment.open_questions[0]
                triggered_rules.append(
                    f"rule_1:high_impact_negative:{assessment.dimension.value}"
                )
                candidate_questions.append((
                    question,
                    assessment.dimension.value,
                    assessment.evidence_against,
                ))

    # Rule 2: Critical assumptions with material impact
    for assumption in confidence.assumptions:
        if _is_critical_assumption(assumption.impact):
            if assumption.clarification_question:
                triggered_rules.append(
                    f"rule_2:critical_assumption:{assumption.statement[:50]}"
                )
                candidate_questions.append((
                    assumption.clarification_question,
                    "critical_assumption",
                    [assumption.impact],
                ))

    # Rule 3: LLM flagged + evidence exists
    if confidence.requires_clarification:
        # Only honour if there's actually something concrete to ask
        if candidate_questions:
            triggered_rules.append("rule_3:llm_flagged_with_evidence")
        elif _has_any_open_question(confidence):
            # LLM flagged but we didn't trigger rules 1/2 — look for anything
            question = _find_best_question(confidence)
            if question:
                triggered_rules.append("rule_3:llm_flagged_fallback")
                candidate_questions.append((
                    question,
                    "llm_flagged",
                    [],
                ))

    # Decision
    if not triggered_rules or not candidate_questions:
        return GateDecision(should_clarify=False)

    # Pick the single most important question
    best_question, dimension, evidence = candidate_questions[0]

    return GateDecision(
        should_clarify=True,
        clarification=ClarificationRequest(
            question=best_question,
            dimension=dimension,
            context=_build_context(candidate_questions),
            triggered_by=evidence,
        ),
        triggered_rules=triggered_rules,
    )


def _is_net_negative(assessment: ConfidenceAssessment) -> bool:
    """Check if evidence_against outweighs evidence_for."""
    return len(assessment.evidence_against) > len(assessment.evidence_for)


def _is_critical_assumption(impact: str) -> bool:
    """Check if an assumption's impact description suggests high criticality."""
    if not impact:
        return False
    impact_lower = impact.lower()
    return any(keyword in impact_lower for keyword in CRITICAL_IMPACT_KEYWORDS)


def _has_any_open_question(confidence: SpecConfidence) -> bool:
    """Check if there's any open question anywhere in the confidence model."""
    for assessment in confidence.assessments:
        if assessment.open_questions:
            return True
    for assumption in confidence.assumptions:
        if assumption.clarification_question:
            return True
    return False


def _find_best_question(confidence: SpecConfidence) -> str:
    """Find the best question to ask from anywhere in the confidence model."""
    # Prefer high-impact dimension questions
    for assessment in confidence.assessments:
        if assessment.dimension in HIGH_IMPACT_DIMENSIONS and assessment.open_questions:
            return assessment.open_questions[0]

    # Fall back to any dimension
    for assessment in confidence.assessments:
        if assessment.open_questions:
            return assessment.open_questions[0]

    # Fall back to assumption questions
    for assumption in confidence.assumptions:
        if assumption.clarification_question:
            return assumption.clarification_question

    return ""


def _build_context(
    candidates: list[tuple[str, str, list[str]]]
) -> str:
    """Build a brief context string for the clarification request."""
    if len(candidates) == 1:
        return ""
    # Mention there are multiple uncertainties but we're asking the most important one
    return f"({len(candidates)} uncertainties identified; asking the most critical one.)"
