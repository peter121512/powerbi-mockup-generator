"""Main orchestration service for synthetic data generation.

Coordinates the full pipeline: plan → generate → apply patterns → write → verify.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pbi_gen.datagen.generators import generate_all_tables
from pbi_gen.datagen.patterns import apply_patterns
from pbi_gen.datagen.planner import build_generation_plan, GenerationPlan
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


def validate_key_integrity(
    tables: dict[str, list[dict[str, Any]]],
    plan: GenerationPlan,
) -> list[str]:
    """Validate data integrity constraints required for Power BI refresh.

    Checks:
    - No NULL/empty values in primary key columns.
    - All primary key values are unique within their table.
    - No NULL/empty values in foreign key columns (used in relationships).

    Args:
        tables: Generated table data.
        plan: The generation plan containing table schemas.

    Returns:
        List of error messages. Empty list means all checks passed.
    """
    errors: list[str] = []

    for table_plan in plan.ordered_tables:
        table_name = table_plan.table_name
        rows = tables.get(table_name, [])
        if not rows:
            continue

        # Check primary key columns
        for col in table_plan.columns:
            if col.is_key:
                # Check for None/empty values
                bad_indices = []
                seen_values: set[Any] = set()
                duplicates: list[Any] = []

                for i, row in enumerate(rows):
                    val = row.get(col.name)
                    if val is None or val == "":
                        bad_indices.append(i)
                    else:
                        if val in seen_values:
                            duplicates.append(val)
                        seen_values.add(val)

                if bad_indices:
                    errors.append(
                        f"{table_name}.{col.name} (PK): "
                        f"{len(bad_indices)} NULL/empty values at rows {bad_indices[:5]}"
                    )
                if duplicates:
                    errors.append(
                        f"{table_name}.{col.name} (PK): "
                        f"{len(duplicates)} duplicate values, e.g. {duplicates[:3]}"
                    )

        # Check foreign key columns
        for fk in table_plan.foreign_keys:
            col_name = fk.from_column
            null_count = 0
            for row in rows:
                val = row.get(col_name)
                if val is None or val == "":
                    null_count += 1

            if null_count > 0:
                errors.append(
                    f"{table_name}.{col_name} (FK→{fk.to_table}.{fk.to_column}): "
                    f"{null_count} NULL/empty values"
                )

    return errors


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

        # 5b. Validate key/FK integrity (required for Power BI refresh)
        integrity_errors = validate_key_integrity(tables, plan)
        if integrity_errors:
            return DataGenResult.generation_failure(
                f"Key integrity validation failed: {'; '.join(integrity_errors)}"
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
