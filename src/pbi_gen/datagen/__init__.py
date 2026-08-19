"""Synthetic data generation engine for Power BI mockups.

Public API:
    generate_synthetic_data  — Main entry point
    DataGenResult            — Structured result
    DataGenOutcome           — Outcome enum
    DataGenDiagnostics       — Generation diagnostics
    VerificationResult       — Pattern verification results
    VerificationCheck        — Single verification check
    TableManifest            — Table metadata
    build_generation_plan    — Plan generation (for inspection/testing)
    GenerationPlan           — Plan model
    TableRole                — Table classification enum
"""

from pbi_gen.datagen.planner import (
    GenerationPlan,
    TableRole,
    build_generation_plan,
)
from pbi_gen.datagen.result import (
    DataGenDiagnostics,
    DataGenOutcome,
    DataGenResult,
    TableManifest,
    VerificationCheck,
    VerificationResult,
)
from pbi_gen.datagen.service import generate_synthetic_data

__all__ = [
    "generate_synthetic_data",
    "DataGenResult",
    "DataGenOutcome",
    "DataGenDiagnostics",
    "VerificationResult",
    "VerificationCheck",
    "TableManifest",
    "build_generation_plan",
    "GenerationPlan",
    "TableRole",
]
