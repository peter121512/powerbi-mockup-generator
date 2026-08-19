"""Post-render structural validation for PBIP projects.

Validates that a rendered PBIP project has the expected directory structure,
required files, and valid JSON content.
"""

from __future__ import annotations

import json
from pathlib import Path

from pbi_gen.renderer.result import ValidationCheck, ValidationResult


def validate_pbip_project(project_root: Path, project_name: str) -> ValidationResult:
    """Validate the structural integrity of a rendered PBIP project.

    Args:
        project_root: Path to the project root directory.
        project_name: The project name used in directory naming.

    Returns:
        ValidationResult with all checks performed.
    """
    checks: list[ValidationCheck] = []

    # Check root exists
    checks.append(ValidationCheck(
        name="project_root_exists",
        passed=project_root.is_dir(),
        message=f"Project root: {project_root}",
    ))

    # .pbip file
    pbip_file = project_root / f"{project_name}.pbip"
    checks.append(ValidationCheck(
        name="pbip_file_exists",
        passed=pbip_file.is_file(),
        message=str(pbip_file),
    ))

    # .gitignore
    gitignore = project_root / ".gitignore"
    checks.append(ValidationCheck(
        name="gitignore_exists",
        passed=gitignore.is_file(),
        message=str(gitignore),
    ))

    # Semantic Model structure
    sm_root = project_root / f"{project_name}.SemanticModel"
    checks.append(ValidationCheck(
        name="semantic_model_dir_exists",
        passed=sm_root.is_dir(),
        message=str(sm_root),
    ))

    sm_def = sm_root / "definition"
    checks.append(ValidationCheck(
        name="sm_definition_dir_exists",
        passed=sm_def.is_dir(),
        message=str(sm_def),
    ))

    model_tmdl = sm_def / "model.tmdl"
    checks.append(ValidationCheck(
        name="model_tmdl_exists",
        passed=model_tmdl.is_file(),
        message=str(model_tmdl),
    ))

    tables_dir = sm_def / "tables"
    checks.append(ValidationCheck(
        name="tables_dir_exists",
        passed=tables_dir.is_dir(),
        message=str(tables_dir),
    ))

    # Check at least one table file exists
    table_files = list(tables_dir.glob("*.tmdl")) if tables_dir.is_dir() else []
    checks.append(ValidationCheck(
        name="at_least_one_table",
        passed=len(table_files) > 0,
        message=f"Found {len(table_files)} table TMDL files",
    ))

    # definition.pbism
    pbism = sm_root / "definition.pbism"
    checks.append(ValidationCheck(
        name="definition_pbism_exists",
        passed=pbism.is_file(),
        message=str(pbism),
    ))
    if pbism.is_file():
        checks.append(_validate_json_file(pbism, "definition_pbism_valid_json"))

    # .platform (semantic model)
    sm_platform = sm_root / ".platform"
    checks.append(ValidationCheck(
        name="sm_platform_exists",
        passed=sm_platform.is_file(),
        message=str(sm_platform),
    ))

    # Report structure
    rpt_root = project_root / f"{project_name}.Report"
    checks.append(ValidationCheck(
        name="report_dir_exists",
        passed=rpt_root.is_dir(),
        message=str(rpt_root),
    ))

    rpt_def = rpt_root / "definition"
    checks.append(ValidationCheck(
        name="rpt_definition_dir_exists",
        passed=rpt_def.is_dir(),
        message=str(rpt_def),
    ))

    # report.json
    report_json = rpt_def / "report.json"
    checks.append(ValidationCheck(
        name="report_json_exists",
        passed=report_json.is_file(),
        message=str(report_json),
    ))
    if report_json.is_file():
        checks.append(_validate_json_file(report_json, "report_json_valid"))

    # version.json
    version_json = rpt_def / "version.json"
    checks.append(ValidationCheck(
        name="version_json_exists",
        passed=version_json.is_file(),
        message=str(version_json),
    ))

    # definition.pbir
    pbir = rpt_root / "definition.pbir"
    checks.append(ValidationCheck(
        name="definition_pbir_exists",
        passed=pbir.is_file(),
        message=str(pbir),
    ))
    if pbir.is_file():
        checks.append(_validate_json_file(pbir, "definition_pbir_valid_json"))

    # .platform (report)
    rpt_platform = rpt_root / ".platform"
    checks.append(ValidationCheck(
        name="rpt_platform_exists",
        passed=rpt_platform.is_file(),
        message=str(rpt_platform),
    ))

    # pages/pages.json
    pages_json = rpt_def / "pages" / "pages.json"
    checks.append(ValidationCheck(
        name="pages_json_exists",
        passed=pages_json.is_file(),
        message=str(pages_json),
    ))
    if pages_json.is_file():
        checks.append(_validate_json_file(pages_json, "pages_json_valid"))

    # Theme
    theme_path = rpt_root / "StaticResources" / "RegisteredResources" / "theme.json"
    checks.append(ValidationCheck(
        name="theme_json_exists",
        passed=theme_path.is_file(),
        message=str(theme_path),
    ))
    if theme_path.is_file():
        checks.append(_validate_json_file(theme_path, "theme_json_valid"))

    # Check page directories exist
    pages_dir = rpt_def / "pages"
    if pages_json.is_file():
        try:
            pages_meta = json.loads(pages_json.read_text(encoding="utf-8"))
            page_order = pages_meta.get("pageOrder", [])
            for page_id in page_order:
                page_dir = pages_dir / page_id
                page_json = page_dir / "page.json"
                checks.append(ValidationCheck(
                    name=f"page_{page_id}_exists",
                    passed=page_json.is_file(),
                    message=str(page_json),
                ))
                # Check at least one visual
                visuals_dir = page_dir / "visuals"
                if visuals_dir.is_dir():
                    visual_dirs = [d for d in visuals_dir.iterdir() if d.is_dir()]
                    checks.append(ValidationCheck(
                        name=f"page_{page_id}_has_visuals",
                        passed=len(visual_dirs) > 0,
                        message=f"Found {len(visual_dirs)} visuals",
                    ))
        except (json.JSONDecodeError, KeyError):
            checks.append(ValidationCheck(
                name="pages_meta_parseable",
                passed=False,
                message="Failed to parse pages.json for page validation",
            ))

    return ValidationResult(checks=checks)


def _validate_json_file(path: Path, check_name: str) -> ValidationCheck:
    """Validate that a file contains valid JSON."""
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return ValidationCheck(name=check_name, passed=True, message="Valid JSON")
    except json.JSONDecodeError as e:
        return ValidationCheck(name=check_name, passed=False, message=f"Invalid JSON: {e}")
