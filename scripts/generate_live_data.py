"""Generate data from the live Stage 02a spec and produce LIVE_DATA_MANIFEST.json."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.models.dashboard_spec import DashboardSpec
from pbi_gen.datagen import generate_synthetic_data, DataGenOutcome


def main():
    project_root = Path(__file__).parent.parent

    # Load the live spec
    spec_path = project_root / "docs" / "stages" / "02a-live-designer-test" / "LIVE_OUTPUT.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = DashboardSpec.model_validate(json.load(f))

    print(f"Loaded spec: {spec.intent.title}")
    print(f"Tables: {len(spec.tables)}")
    print(f"Narrative patterns: {len(spec.mock_data_narrative.patterns)}")
    print()

    # Generate
    output_dir = project_root / "build" / "live_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "retail_dashboard.db"

    print(f"Generating to: {db_path}")
    start = time.time()
    result = generate_synthetic_data(spec, output_path=db_path, seed=42)
    elapsed = time.time() - start

    print(f"Outcome: {result.outcome.value}")
    print(f"Elapsed: {elapsed:.2f}s")
    print()

    if result.outcome == DataGenOutcome.SUCCESS:
        diag = result.diagnostics
        print(f"Seed: {diag.seed}")
        print(f"Tables generated: {len(diag.tables)}")
        for t in diag.tables:
            print(f"  {t.table_name}: {t.row_count} rows, {len(t.columns)} columns")
        print()

        print(f"Patterns applied: {len(diag.patterns_applied)}")
        for p in diag.patterns_applied:
            print(f"  - {p}")
        print()

        vr = diag.verification_results
        print(f"Verification: {vr.pass_count} passed, {vr.fail_count} failed")
        for c in vr.checks:
            status = "PASS" if c.passed else "FAIL"
            print(f"  [{status}] {c.name}: expected={c.expected}, actual={c.actual}")
        print()

        if diag.warnings:
            print(f"Warnings: {len(diag.warnings)}")
            for w in diag.warnings:
                print(f"  - {w}")
            print()

        # Produce manifest
        manifest = {
            "generator_version": "stage-03",
            "seed": diag.seed,
            "output_path": str(db_path.relative_to(project_root)),
            "spec_source": "docs/stages/02a-live-designer-test/LIVE_OUTPUT.json",
            "tables": [
                {"name": t.table_name, "row_count": t.row_count, "columns": t.columns}
                for t in diag.tables
            ],
            "total_rows": sum(t.row_count for t in diag.tables),
            "patterns_applied": diag.patterns_applied,
            "verification": {
                "total_checks": len(vr.checks),
                "passed": vr.pass_count,
                "failed": vr.fail_count,
                "checks": [
                    {
                        "name": c.name,
                        "passed": c.passed,
                        "expected": c.expected,
                        "actual": c.actual,
                        "tolerance": c.tolerance if c.tolerance else None,
                    }
                    for c in vr.checks
                ],
            },
            "warnings": diag.warnings,
            "elapsed_seconds": round(elapsed, 2),
        }

        manifest_path = project_root / "docs" / "stages" / "03-synthetic-data" / "LIVE_DATA_MANIFEST.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved: {manifest_path}")

    else:
        print(f"Error: {result.error_message}")
        if result.diagnostics and result.diagnostics.warnings:
            for w in result.diagnostics.warnings:
                print(f"  Warning: {w}")


if __name__ == "__main__":
    main()
