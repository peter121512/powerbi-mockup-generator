"""Typed result models for synthetic data generation.

Provides structured outcome reporting for the data generation pipeline,
including diagnostics, verification results, and table manifests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DataGenOutcome(str, Enum):
    """Outcome status for a data generation run."""

    SUCCESS = "success"
    INVALID_SPEC = "invalid_spec"
    GENERATION_FAILURE = "generation_failure"
    VERIFICATION_FAILURE = "verification_failure"


@dataclass
class TableManifest:
    """Manifest for a single generated table."""

    table_name: str
    row_count: int
    columns: list[str]


@dataclass
class VerificationCheck:
    """Result of a single verification check."""

    name: str
    passed: bool
    expected: str
    actual: str
    tolerance: str = ""


@dataclass
class VerificationResult:
    """Aggregate verification result for generated data."""

    checks: list[VerificationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def failed(self) -> bool:
        """True if any check failed."""
        return not self.passed

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


@dataclass
class DataGenDiagnostics:
    """Diagnostics for a data generation run."""

    seed: int
    output_path: str
    tables: list[TableManifest] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    patterns_applied: list[str] = field(default_factory=list)
    verification_results: VerificationResult = field(default_factory=VerificationResult)
    warnings: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class DataGenResult:
    """Result of a synthetic data generation run."""

    outcome: DataGenOutcome
    message: str
    diagnostics: DataGenDiagnostics | None = None
    error: str = ""

    @property
    def success(self) -> bool:
        return self.outcome == DataGenOutcome.SUCCESS

    @classmethod
    def ok(
        cls,
        message: str = "Data generation completed successfully.",
        diagnostics: DataGenDiagnostics | None = None,
    ) -> DataGenResult:
        """Factory for a successful result."""
        return cls(
            outcome=DataGenOutcome.SUCCESS,
            message=message,
            diagnostics=diagnostics,
        )

    @classmethod
    def invalid_spec(cls, reason: str) -> DataGenResult:
        """Factory for an invalid spec failure."""
        return cls(
            outcome=DataGenOutcome.INVALID_SPEC,
            message=f"Spec validation failed: {reason}",
            error=reason,
        )

    @classmethod
    def generation_failure(cls, reason: str) -> DataGenResult:
        """Factory for a generation failure."""
        return cls(
            outcome=DataGenOutcome.GENERATION_FAILURE,
            message=f"Data generation failed: {reason}",
            error=reason,
        )

    @classmethod
    def verification_failure(
        cls,
        reason: str,
        diagnostics: DataGenDiagnostics | None = None,
    ) -> DataGenResult:
        """Factory for a verification failure (data generated but didn't verify)."""
        return cls(
            outcome=DataGenOutcome.VERIFICATION_FAILURE,
            message=f"Verification failed: {reason}",
            diagnostics=diagnostics,
            error=reason,
        )
