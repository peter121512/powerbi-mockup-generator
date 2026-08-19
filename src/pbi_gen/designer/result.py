"""Typed result/error model for designer execution.

Callers receive explicit outcomes without needing to infer state from
exception strings or None checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pbi_gen.models.dashboard_spec import DashboardSpec, ConfidenceAssessment


class DesignOutcome(str, Enum):
    """Discriminator for DesignResult variants."""

    SUCCESS = "success"
    CLARIFICATION_NEEDED = "clarification_needed"
    PROVIDER_ERROR = "provider_error"
    INVALID_OUTPUT = "invalid_output"
    VALIDATION_ERROR = "validation_error"


@dataclass(frozen=True)
class ClarificationRequest:
    """A compact question to present to the user before proceeding."""

    question: str
    dimension: str  # which ConfidenceDimension triggered this
    context: str = ""  # additional context for the user
    triggered_by: list[str] = field(default_factory=list)  # evidence that triggered it


@dataclass(frozen=True)
class ValidationIssue:
    """A single semantic validation problem found in a generated spec."""

    category: str  # e.g. "missing_field_ref", "missing_page_ref"
    message: str
    path: str = ""  # e.g. "pages[0].visuals[2].value_fields[0]"


@dataclass(frozen=True)
class DesignDiagnostics:
    """Development diagnostics for understanding design outcomes."""

    provider: str = ""
    model: str = ""
    validation_errors: list[ValidationIssue] = field(default_factory=list)
    clarification_dimensions: list[str] = field(default_factory=list)
    assumptions_made: list[str] = field(default_factory=list)
    raw_response: str = ""  # only populated in debug mode


@dataclass(frozen=True)
class DesignResult:
    """Typed outcome of a design_dashboard() call.

    Use `outcome` to discriminate, then access the relevant field:
    - SUCCESS → spec is populated
    - CLARIFICATION_NEEDED → clarification is populated
    - PROVIDER_ERROR → error_message describes the failure
    - INVALID_OUTPUT → error_message + diagnostics.validation_errors
    - VALIDATION_ERROR → error_message + diagnostics.validation_errors
    """

    outcome: DesignOutcome
    spec: DashboardSpec | None = None
    clarification: ClarificationRequest | None = None
    error_message: str = ""
    diagnostics: DesignDiagnostics = field(default_factory=DesignDiagnostics)

    @staticmethod
    def success(
        spec: DashboardSpec, diagnostics: DesignDiagnostics | None = None
    ) -> "DesignResult":
        """Create a successful result."""
        return DesignResult(
            outcome=DesignOutcome.SUCCESS,
            spec=spec,
            diagnostics=diagnostics or DesignDiagnostics(),
        )

    @staticmethod
    def needs_clarification(
        clarification: ClarificationRequest,
        diagnostics: DesignDiagnostics | None = None,
    ) -> "DesignResult":
        """Create a clarification-needed result."""
        return DesignResult(
            outcome=DesignOutcome.CLARIFICATION_NEEDED,
            clarification=clarification,
            diagnostics=diagnostics or DesignDiagnostics(),
        )

    @staticmethod
    def provider_error(
        message: str, diagnostics: DesignDiagnostics | None = None
    ) -> "DesignResult":
        """Create a provider failure result."""
        return DesignResult(
            outcome=DesignOutcome.PROVIDER_ERROR,
            error_message=message,
            diagnostics=diagnostics or DesignDiagnostics(),
        )

    @staticmethod
    def invalid_output(
        message: str, diagnostics: DesignDiagnostics | None = None
    ) -> "DesignResult":
        """Create an invalid/malformed output result."""
        return DesignResult(
            outcome=DesignOutcome.INVALID_OUTPUT,
            error_message=message,
            diagnostics=diagnostics or DesignDiagnostics(),
        )

    @staticmethod
    def validation_error(
        message: str,
        issues: list[ValidationIssue] | None = None,
        diagnostics: DesignDiagnostics | None = None,
    ) -> "DesignResult":
        """Create a semantic validation failure result."""
        diag = diagnostics or DesignDiagnostics()
        if issues:
            diag = DesignDiagnostics(
                provider=diag.provider,
                model=diag.model,
                validation_errors=issues,
                clarification_dimensions=diag.clarification_dimensions,
                assumptions_made=diag.assumptions_made,
                raw_response=diag.raw_response,
            )
        return DesignResult(
            outcome=DesignOutcome.VALIDATION_ERROR,
            error_message=message,
            diagnostics=diag,
        )
