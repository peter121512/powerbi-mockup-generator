"""Main PBIP render orchestration service.

Provides the top-level render_powerbi_project() function that takes a
DashboardSpec and produces a complete PBIP project on disk.
"""

from __future__ import annotations

from pathlib import Path

from pbi_gen.models import DashboardSpec
from pbi_gen.renderer.project import write_pbip_project
from pbi_gen.renderer.result import RenderOutcome, RenderResult
from pbi_gen.renderer.validator import validate_pbip_project


def render_powerbi_project(
    spec: DashboardSpec,
    output_dir: Path,
    *,
    project_name: str | None = None,
    validate: bool = True,
) -> RenderResult:
    """Render a DashboardSpec into a complete PBIP project on disk.

    This is the primary public API for Stage 04. It orchestrates:
    1. Spec validation (basic)
    2. PBIP project writing (semantic model + report + theme)
    3. Fidelity tracking (no silent visual loss)
    4. Structural validation of the output

    Args:
        spec: Complete dashboard specification.
        output_dir: Directory to write the project into.
        project_name: Override project directory name.
        validate: Whether to run post-render validation.

    Returns:
        RenderResult with outcome, fidelity manifest, and validation.
    """
    # Basic spec validation
    if not spec.pages:
        return RenderResult.invalid_spec("Spec has no pages")
    if not spec.tables:
        return RenderResult.invalid_spec("Spec has no tables")

    # Resolve project name
    resolved_name = project_name
    if resolved_name is None:
        resolved_name = _sanitize_project_name(spec.intent.title)

    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        project_root, fidelity = write_pbip_project(
            spec, output_dir, project_name=resolved_name
        )
    except Exception as e:
        return RenderResult.render_failure(str(e))

    # Post-render validation
    validation = None
    if validate:
        validation = validate_pbip_project(project_root, resolved_name)

    # Determine outcome
    if not fidelity.all_rendered:
        return RenderResult.partial(
            output_path=project_root,
            project_name=resolved_name,
            reason=f"Only {fidelity.rendered_visuals}/{fidelity.total_visuals} visuals rendered",
            fidelity=fidelity,
        )

    if validation and not validation.passed:
        failed = [c.name for c in validation.failed_checks]
        return RenderResult(
            outcome=RenderOutcome.VALIDATION_FAILURE,
            message=f"Structural validation failed: {failed}",
            output_path=project_root,
            project_name=resolved_name,
            fidelity=fidelity,
            validation=validation,
        )

    return RenderResult.ok(
        output_path=project_root,
        project_name=resolved_name,
        fidelity=fidelity,
        validation=validation,
    )


def _sanitize_project_name(title: str) -> str:
    """Convert a dashboard title into a safe project directory name."""
    clean = "".join(c for c in title if c.isalnum() or c in " _-")
    parts = clean.split()
    if not parts:
        return "Dashboard"
    return "".join(parts)
