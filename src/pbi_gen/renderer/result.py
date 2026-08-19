"""Typed result models for the PBIP renderer.

Provides structured outcome reporting for the rendering pipeline,
including fidelity tracking and validation diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RenderOutcome(str, Enum):
    """Outcome status for a render run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    INVALID_SPEC = "invalid_spec"
    RENDER_FAILURE = "render_failure"
    VALIDATION_FAILURE = "validation_failure"


@dataclass
class VisualFidelity:
    """Fidelity record for a single visual."""

    visual_id: str
    visual_type: str
    rendered_type: str
    is_fallback: bool = False
    fallback_reason: str = ""


@dataclass
class FidelityManifest:
    """Tracks how faithfully the spec was rendered."""

    total_pages: int = 0
    rendered_pages: int = 0
    total_visuals: int = 0
    rendered_visuals: int = 0
    fallback_visuals: int = 0
    visual_details: list[VisualFidelity] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def all_rendered(self) -> bool:
        """True if no visuals were silently dropped."""
        return self.total_visuals == self.rendered_visuals

    @property
    def no_fallbacks(self) -> bool:
        """True if no visuals required a fallback type."""
        return self.fallback_visuals == 0


@dataclass
class ValidationCheck:
    """Result of a single structural validation check."""

    name: str
    passed: bool
    message: str = ""


@dataclass
class ValidationResult:
    """Aggregate validation result for the rendered project."""

    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[ValidationCheck]:
        return [c for c in self.checks if not c.passed]


@dataclass
class RenderResult:
    """Result of a PBIP render run."""

    outcome: RenderOutcome
    message: str
    output_path: Path | None = None
    project_name: str = ""
    fidelity: FidelityManifest = field(default_factory=FidelityManifest)
    validation: ValidationResult = field(default_factory=ValidationResult)
    error: str = ""

    @property
    def success(self) -> bool:
        return self.outcome == RenderOutcome.SUCCESS

    @classmethod
    def ok(
        cls,
        output_path: Path,
        project_name: str,
        fidelity: FidelityManifest | None = None,
        validation: ValidationResult | None = None,
    ) -> RenderResult:
        return cls(
            outcome=RenderOutcome.SUCCESS,
            message="PBIP project rendered successfully.",
            output_path=output_path,
            project_name=project_name,
            fidelity=fidelity or FidelityManifest(),
            validation=validation or ValidationResult(),
        )

    @classmethod
    def partial(
        cls,
        output_path: Path,
        project_name: str,
        reason: str,
        fidelity: FidelityManifest | None = None,
    ) -> RenderResult:
        return cls(
            outcome=RenderOutcome.PARTIAL,
            message=f"PBIP project rendered with issues: {reason}",
            output_path=output_path,
            project_name=project_name,
            fidelity=fidelity or FidelityManifest(),
        )

    @classmethod
    def invalid_spec(cls, reason: str) -> RenderResult:
        return cls(
            outcome=RenderOutcome.INVALID_SPEC,
            message=f"Spec validation failed: {reason}",
            error=reason,
        )

    @classmethod
    def render_failure(cls, reason: str) -> RenderResult:
        return cls(
            outcome=RenderOutcome.RENDER_FAILURE,
            message=f"Render failed: {reason}",
            error=reason,
        )
