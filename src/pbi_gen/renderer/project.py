"""PBIP project skeleton writer.

Creates the directory structure and writes all files for a complete
Power BI Project (PBIP) that can be opened in Power BI Desktop or
deployed via fabric-cicd.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pbi_gen.models import DashboardSpec
from pbi_gen.renderer.layout import grid_to_canvas, position_to_dict
from pbi_gen.renderer.report import (
    generate_definition_pbir,
    generate_filter_visual_json,
    generate_page_json,
    generate_pages_json,
    generate_report_json,
    generate_version_json,
    generate_visual_json,
)
from pbi_gen.renderer.result import FidelityManifest, VisualFidelity
from pbi_gen.renderer.semantic_model import (
    generate_definition_pbism,
    generate_model_tmdl,
    generate_relationships_tmdl,
    generate_table_tmdl,
)
from pbi_gen.renderer.theme import generate_theme
from pbi_gen.renderer.visuals import make_visual_fidelity, map_visual_type


def _sanitize_project_name(title: str) -> str:
    """Convert a dashboard title into a safe project directory name."""
    # Remove problematic characters, keep alphanumeric and spaces
    clean = "".join(c for c in title if c.isalnum() or c in " _-")
    # Convert spaces to camelCase-ish
    parts = clean.split()
    if not parts:
        return "Dashboard"
    return "".join(parts)


def _write_json(path: Path, data: dict) -> None:
    """Write a dict as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    """Write text content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _generate_platform_file(item_type: str, display_name: str) -> dict:
    """Generate a .platform file for a PBIP item."""
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": item_type,
            "displayName": display_name,
        },
        "config": {
            "version": "2.0",
            "logicalId": str(uuid4()),
        },
    }


def _generate_pbip_file(project_name: str) -> dict:
    """Generate the .pbip root file."""
    return {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": f"{project_name}.Report",
                }
            }
        ],
        "settings": {
            "enableAutoRecovery": True,
        },
    }


def _generate_gitignore() -> str:
    """Generate .gitignore content for the PBIP project."""
    return (
        "*.pbicache\n"
        ".pbi/\n"
        "*.pbix\n"
        "localSettings.json\n"
    )


def write_pbip_project(
    spec: DashboardSpec,
    output_dir: Path,
    *,
    project_name: str | None = None,
    partition_sources: dict[str, str] | None = None,
) -> tuple[Path, FidelityManifest]:
    """Write a complete PBIP project to disk.

    Args:
        spec: The complete dashboard specification.
        output_dir: Parent directory to write the project into.
        project_name: Override project name. Defaults to sanitized title.
        partition_sources: Optional mapping of {table_name: m_expression}
            for real data partition sources instead of placeholders.

    Returns:
        Tuple of (project_root_path, fidelity_manifest).
    """
    if project_name is None:
        project_name = _sanitize_project_name(spec.intent.title)

    project_root = output_dir / project_name
    project_root.mkdir(parents=True, exist_ok=True)

    # Track fidelity
    fidelity = FidelityManifest(
        total_pages=len(spec.pages),
        total_visuals=sum(len(p.visuals) for p in spec.pages),
    )

    # ── Root files ──────────────────────────────────────────────────────
    _write_json(project_root / f"{project_name}.pbip", _generate_pbip_file(project_name))
    _write_text(project_root / ".gitignore", _generate_gitignore())

    # ── Semantic Model ──────────────────────────────────────────────────
    sm_root = project_root / f"{project_name}.SemanticModel"
    sm_def = sm_root / "definition"

    # model.tmdl
    _write_text(sm_def / "model.tmdl", generate_model_tmdl())

    # tables/
    tables_dir = sm_def / "tables"
    for table in spec.tables:
        tmdl = generate_table_tmdl(table, spec.measures, partition_sources)
        _write_text(tables_dir / f"{table.name}.tmdl", tmdl)

    # relationships.tmdl
    if spec.relationships:
        _write_text(sm_def / "relationships.tmdl", generate_relationships_tmdl(spec.relationships))

    # definition.pbism
    _write_json(sm_root / "definition.pbism", generate_definition_pbism())

    # .platform
    _write_json(sm_root / ".platform", _generate_platform_file("SemanticModel", project_name))

    # ── Report ──────────────────────────────────────────────────────────
    rpt_root = project_root / f"{project_name}.Report"
    rpt_def = rpt_root / "definition"

    # report.json
    _write_json(rpt_def / "report.json", generate_report_json())

    # version.json
    _write_json(rpt_def / "version.json", generate_version_json())

    # definition.pbir
    _write_json(rpt_root / "definition.pbir", generate_definition_pbir(project_name))

    # .platform
    _write_json(rpt_root / ".platform", _generate_platform_file("Report", project_name))

    # pages/pages.json
    pages_dir = rpt_def / "pages"
    _write_json(pages_dir / "pages.json", generate_pages_json(spec.pages))

    # Each page
    rendered_pages = 0
    rendered_visuals = 0

    for page in sorted(spec.pages, key=lambda p: p.sort_order):
        page_dir = pages_dir / page.id
        _write_json(page_dir / "page.json", generate_page_json(page))

        # Visuals
        visuals_dir = page_dir / "visuals"
        for idx, visual in enumerate(page.visuals):
            pbi_type, is_fallback, reason = map_visual_type(visual)

            visual_json = generate_visual_json(
                visual,
                page,
                z_index=1000 + idx,
                tab_order=idx,
                measures=spec.measures,
            )

            visual_dir = visuals_dir / visual.id
            _write_json(visual_dir / "visual.json", visual_json)
            rendered_visuals += 1

            fidelity.visual_details.append(
                make_visual_fidelity(visual, pbi_type, is_fallback, reason)
            )
            if is_fallback:
                fidelity.fallback_visuals += 1

        # Filter slicers
        for f_idx, filter_spec in enumerate(page.filters):
            filter_json = generate_filter_visual_json(
                filter_spec,
                page,
                z_index=500 + f_idx,
                tab_order=len(page.visuals) + f_idx,
                position_index=f_idx,
            )
            filter_dir = visuals_dir / filter_spec.id
            _write_json(filter_dir / "visual.json", filter_json)
            # Filters rendered as visuals but not counted in spec visual total

        rendered_pages += 1

    fidelity.rendered_pages = rendered_pages
    fidelity.rendered_visuals = rendered_visuals

    # ── Theme ───────────────────────────────────────────────────────────
    theme_dir = rpt_root / "StaticResources" / "RegisteredResources"
    _write_json(theme_dir / "theme.json", generate_theme(spec.theme))

    return project_root, fidelity
