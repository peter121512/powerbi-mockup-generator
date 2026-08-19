"""Render the live Stage 02a spec into a PBIP project and produce the manifest."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.models.dashboard_spec import DashboardSpec
from pbi_gen.renderer import render_powerbi_project, RenderOutcome


def main():
    project_root = Path(__file__).parent.parent

    # Load the live spec
    spec_path = project_root / "docs" / "stages" / "02a-live-designer-test" / "LIVE_OUTPUT.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = DashboardSpec.model_validate(json.load(f))

    # Output directory
    output_dir = project_root / "build" / "live_render"

    print(f"Spec: {spec.intent.title}")
    print(f"Pages: {len(spec.pages)}")
    total_visuals = sum(len(p.visuals) for p in spec.pages)
    total_filters = sum(len(p.filters) for p in spec.pages)
    print(f"Total visuals: {total_visuals}")
    print(f"Total filters: {total_filters}")
    print(f"Tables: {len(spec.tables)}")
    print(f"Measures: {len(spec.measures)}")
    print(f"Relationships: {len(spec.relationships)}")
    print(f"Output: {output_dir}")
    print()

    start = time.time()
    result = render_powerbi_project(spec=spec, output_dir=output_dir)
    elapsed = time.time() - start

    print(f"Outcome: {result.outcome.value}")
    print(f"Elapsed: {elapsed:.2f}s")
    print()

    if result.outcome in (RenderOutcome.SUCCESS, RenderOutcome.PARTIAL):
        print(f"Output path: {result.output_path}")
        print(f"Project name: {result.project_name}")
        print()

        # Fidelity
        fm = result.fidelity
        print("=== FIDELITY ===")
        print(f"Pages: {fm.rendered_pages}/{fm.total_pages}")
        print(f"Visuals: {fm.rendered_visuals}/{fm.total_visuals}")
        print(f"Fallbacks: {fm.fallback_visuals}")
        print(f"All rendered: {fm.all_rendered}")
        print(f"No fallbacks: {fm.no_fallbacks}")
        if fm.warnings:
            print(f"Warnings ({len(fm.warnings)}):")
            for w in fm.warnings:
                print(f"  - {w}")
        print()

        # Visual details
        fallbacks = [v for v in fm.visual_details if v.is_fallback]
        if fallbacks:
            print(f"Visuals with fallback ({len(fallbacks)}):")
            for v in fallbacks:
                print(f"  {v.visual_id}: {v.visual_type} -> {v.rendered_type} ({v.fallback_reason})")
            print()

        # Validation
        vr = result.validation
        passed = sum(1 for c in vr.checks if c.passed)
        failed = sum(1 for c in vr.checks if not c.passed)
        print(f"=== VALIDATION ===")
        print(f"Overall: {'PASSED' if vr.passed else 'FAILED'} ({passed} passed, {failed} failed)")
        if vr.failed_checks:
            for c in vr.failed_checks:
                print(f"  [FAIL] {c.name}: {c.message}")
        print()

        # Produce render manifest
        manifest = {
            "renderer_version": "stage-04",
            "spec_source": "docs/stages/02a-live-designer-test/LIVE_OUTPUT.json",
            "output_path": str(Path(result.output_path).relative_to(project_root)),
            "project_name": result.project_name,
            "elapsed_seconds": round(elapsed, 2),
            "fidelity": {
                "pages_total": fm.total_pages,
                "pages_rendered": fm.rendered_pages,
                "visuals_total": fm.total_visuals,
                "visuals_rendered": fm.rendered_visuals,
                "visuals_with_fallback": fm.fallback_visuals,
                "all_rendered": fm.all_rendered,
                "no_fallbacks": fm.no_fallbacks,
                "visual_types": {},
                "warnings": fm.warnings,
            },
            "validation": {
                "passed": vr.passed,
                "total_checks": len(vr.checks),
                "passed_count": passed,
                "failed_count": failed,
                "failed_checks": [{"name": c.name, "message": c.message} for c in vr.failed_checks],
            },
        }

        # Count visual types
        type_counts: dict[str, int] = {}
        for v in fm.visual_details:
            type_counts[v.rendered_type] = type_counts.get(v.rendered_type, 0) + 1
        manifest["fidelity"]["visual_types"] = type_counts

        manifest_path = project_root / "docs" / "stages" / "04-pbip-renderer" / "LIVE_RENDER_MANIFEST.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved: {manifest_path}")

    else:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    main()
