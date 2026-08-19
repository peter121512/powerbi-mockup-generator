"""Main orchestration service for synthetic data generation.

Coordinates the full pipeline: plan → generate → apply patterns → write → verify.
"""

from __future__ import annotations

import time
from pathlib import Path

from pbi_gen.datagen.generators import generate_all_tables
from pbi_gen.datagen.patterns import apply_patterns
from pbi_gen.datagen.planner import build_generation_plan
from pbi_gen.datagen.result import (
    DataGenDiagnostics,
    DataGenOutcome,
    DataGenResult,
    TableManifest,
    VerificationResult,
)
from pbi_gen.datagen.verifier import verify_data
from pbi_gen.datagen.writer import write_sqlite
from pbi_gen.models.dashboard_spec import DashboardSpec


def generate_synthetic_data(
    spec: DashboardSpec,
    output_path: Path,
    seed: int = 42,
) -> DataGenResult:
    """Generate synthetic data from a DashboardSpec.

    Orchestrates the complete pipeline:
    1. Validate spec
    2. Build generation plan
    3. Generate dimension tables
    4. Generate fact tables
    5. Apply narrative patterns
    6. Write to SQLite
    7. Verify patterns

    Args:
        spec: A valid DashboardSpec with tables and optional mock_data_narrative.
        output_path: Path for the output .sqlite file.
        seed: Random seed for reproducible generation.

    Returns:
        DataGenResult with outcome, diagnostics, and any errors.
    """
    start_time = time.time()
    warnings: list[str] = []

    # 1. Validate spec has tables
    if not spec.tables:
        return DataGenResult.invalid_spec("Spec has no tables defined.")

    try:
        # 2. Build generation plan
        plan = build_generation_plan(spec)

        if not plan.tables:
            return DataGenResult.invalid_spec("No tables in generation plan.")

        # 3 & 4. Generate all tables (dimensions first, then facts)
        tables = generate_all_tables(plan, seed=seed)

        # 5. Apply narrative patterns
        patterns_applied: list[str] = []
        if spec.mock_data_narrative:
            patterns_applied = apply_patterns(
                tables, spec.mock_data_narrative, seed=seed
            )

        # 6. Write to SQLite
        write_sqlite(output_path, tables, plan)

        # 7. Verify patterns
        verification = verify_data(tables, spec.mock_data_narrative)

        # Build diagnostics
        elapsed = time.time() - start_time
        table_manifests = [
            TableManifest(
                table_name=name,
                row_count=len(rows),
                columns=list(rows[0].keys()) if rows else [],
            )
            for name, rows in tables.items()
        ]

        row_counts = {name: len(rows) for name, rows in tables.items()}

        diagnostics = DataGenDiagnostics(
            seed=seed,
            output_path=str(output_path),
            tables=table_manifests,
            row_counts=row_counts,
            patterns_applied=patterns_applied,
            verification_results=verification,
            warnings=warnings,
            elapsed_seconds=elapsed,
        )

        # Check verification
        if verification.failed:
            failed_checks = [
                c.name for c in verification.checks if not c.passed
            ]
            return DataGenResult.verification_failure(
                reason=f"Failed checks: {', '.join(failed_checks)}",
                diagnostics=diagnostics,
            )

        return DataGenResult.ok(
            message=f"Generated {sum(row_counts.values())} rows across {len(tables)} tables in {elapsed:.2f}s.",
            diagnostics=diagnostics,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        return DataGenResult.generation_failure(str(e))
