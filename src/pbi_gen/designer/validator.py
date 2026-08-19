"""Semantic validation for generated DashboardSpec instances.

This module performs cross-reference validation that goes beyond Pydantic's
structural validation. It catches broken references that the LLM may
generate: missing tables, columns, measures, pages, and impossible layouts.
"""

from __future__ import annotations

from pbi_gen.models.dashboard_spec import DashboardSpec, FieldRef, PageSpec
from pbi_gen.designer.result import ValidationIssue


def validate_spec(spec: DashboardSpec) -> list[ValidationIssue]:
    """Run all semantic validation checks on a DashboardSpec.

    Returns a list of issues found. Empty list means the spec is valid.
    """
    issues: list[ValidationIssue] = []

    # Build lookup sets
    table_names = {t.name for t in spec.tables}
    column_lookup: dict[str, set[str]] = {}
    for table in spec.tables:
        column_lookup[table.name] = {c.name for c in table.columns}

    measure_lookup: dict[str, set[str]] = {}
    for m in spec.measures:
        table_key = m.table or "_measures"
        if table_key not in measure_lookup:
            measure_lookup[table_key] = set()
        measure_lookup[table_key].add(m.name)

    # All measure names regardless of table
    all_measure_names = {m.name for m in spec.measures}

    page_ids = {p.id for p in spec.pages}

    # Run checks
    issues.extend(_validate_field_refs(spec, table_names, column_lookup, all_measure_names))
    issues.extend(_validate_page_refs(spec, page_ids))
    issues.extend(_validate_relationships(spec, table_names, column_lookup))
    issues.extend(_validate_visual_positions(spec))
    issues.extend(_validate_filter_refs(spec, table_names, column_lookup, all_measure_names))

    return issues


def _validate_field_ref(
    ref: FieldRef,
    path: str,
    table_names: set[str],
    column_lookup: dict[str, set[str]],
    all_measure_names: set[str],
) -> list[ValidationIssue]:
    """Validate a single FieldRef against the spec's data model."""
    issues = []

    if ref.table not in table_names:
        # Check if it's a valid table for measures
        if ref.measure and ref.measure in all_measure_names:
            # Table might not exist as a data table but the measure is valid
            pass
        else:
            issues.append(
                ValidationIssue(
                    category="missing_table_ref",
                    message=f"FieldRef references table '{ref.table}' which does not exist.",
                    path=path,
                )
            )
            return issues  # Can't check further without the table

    if ref.column:
        table_cols = column_lookup.get(ref.table, set())
        if table_cols and ref.column not in table_cols:
            issues.append(
                ValidationIssue(
                    category="missing_column_ref",
                    message=f"FieldRef references column '{ref.table}.{ref.column}' which does not exist.",
                    path=path,
                )
            )

    if ref.measure:
        if ref.measure not in all_measure_names:
            issues.append(
                ValidationIssue(
                    category="missing_measure_ref",
                    message=f"FieldRef references measure '{ref.measure}' which does not exist.",
                    path=path,
                )
            )

    return issues


def _validate_field_refs(
    spec: DashboardSpec,
    table_names: set[str],
    column_lookup: dict[str, set[str]],
    all_measure_names: set[str],
) -> list[ValidationIssue]:
    """Validate all FieldRef instances across pages/visuals."""
    issues = []

    for pi, page in enumerate(spec.pages):
        for vi, visual in enumerate(page.visuals):
            prefix = f"pages[{pi}].visuals[{vi}]"

            for fi, field_ref in enumerate(visual.category_fields):
                issues.extend(
                    _validate_field_ref(
                        field_ref,
                        f"{prefix}.category_fields[{fi}]",
                        table_names,
                        column_lookup,
                        all_measure_names,
                    )
                )

            for fi, field_ref in enumerate(visual.value_fields):
                issues.extend(
                    _validate_field_ref(
                        field_ref,
                        f"{prefix}.value_fields[{fi}]",
                        table_names,
                        column_lookup,
                        all_measure_names,
                    )
                )

            if visual.series_field:
                issues.extend(
                    _validate_field_ref(
                        visual.series_field,
                        f"{prefix}.series_field",
                        table_names,
                        column_lookup,
                        all_measure_names,
                    )
                )

            if visual.sort:
                issues.extend(
                    _validate_field_ref(
                        visual.sort.field,
                        f"{prefix}.sort.field",
                        table_names,
                        column_lookup,
                        all_measure_names,
                    )
                )

            for ci, cf in enumerate(visual.conditional_formats):
                issues.extend(
                    _validate_field_ref(
                        cf.target_field,
                        f"{prefix}.conditional_formats[{ci}].target_field",
                        table_names,
                        column_lookup,
                        all_measure_names,
                    )
                )

    return issues


def _validate_page_refs(
    spec: DashboardSpec, page_ids: set[str]
) -> list[ValidationIssue]:
    """Validate page references in drill-through, navigation, tooltips."""
    issues = []

    # Drill-through configs
    for i, dt in enumerate(spec.interactions.drill_throughs):
        if dt.source_page_id not in page_ids:
            issues.append(
                ValidationIssue(
                    category="missing_page_ref",
                    message=f"Drill-through source page '{dt.source_page_id}' not found.",
                    path=f"interactions.drill_throughs[{i}].source_page_id",
                )
            )
        if dt.target_page_id not in page_ids:
            issues.append(
                ValidationIssue(
                    category="missing_page_ref",
                    message=f"Drill-through target page '{dt.target_page_id}' not found.",
                    path=f"interactions.drill_throughs[{i}].target_page_id",
                )
            )

    # Navigation buttons at report level
    for i, nav in enumerate(spec.interactions.navigation_buttons):
        if nav.target_page_id not in page_ids:
            issues.append(
                ValidationIssue(
                    category="missing_page_ref",
                    message=f"Navigation target page '{nav.target_page_id}' not found.",
                    path=f"interactions.navigation_buttons[{i}].target_page_id",
                )
            )

    # Tooltip page refs
    for i, tp_id in enumerate(spec.interactions.tooltip_pages):
        if tp_id not in page_ids:
            issues.append(
                ValidationIssue(
                    category="missing_page_ref",
                    message=f"Tooltip page '{tp_id}' not found.",
                    path=f"interactions.tooltip_pages[{i}]",
                )
            )

    # Page-level navigation buttons
    for pi, page in enumerate(spec.pages):
        for ni, nav in enumerate(page.navigation):
            if nav.target_page_id not in page_ids:
                issues.append(
                    ValidationIssue(
                        category="missing_page_ref",
                        message=f"Page navigation target '{nav.target_page_id}' not found.",
                        path=f"pages[{pi}].navigation[{ni}].target_page_id",
                    )
                )

    # Visual drill-through targets
    for pi, page in enumerate(spec.pages):
        for vi, visual in enumerate(page.visuals):
            if visual.drill_through_target and visual.drill_through_target not in page_ids:
                issues.append(
                    ValidationIssue(
                        category="missing_page_ref",
                        message=f"Visual drill-through target '{visual.drill_through_target}' not found.",
                        path=f"pages[{pi}].visuals[{vi}].drill_through_target",
                    )
                )

    return issues


def _validate_relationships(
    spec: DashboardSpec,
    table_names: set[str],
    column_lookup: dict[str, set[str]],
) -> list[ValidationIssue]:
    """Validate that relationships reference existing tables and columns."""
    issues = []

    for i, rel in enumerate(spec.relationships):
        prefix = f"relationships[{i}]"

        if rel.from_table not in table_names:
            issues.append(
                ValidationIssue(
                    category="missing_table_ref",
                    message=f"Relationship from_table '{rel.from_table}' not found.",
                    path=f"{prefix}.from_table",
                )
            )
        elif rel.from_column not in column_lookup.get(rel.from_table, set()):
            issues.append(
                ValidationIssue(
                    category="missing_column_ref",
                    message=f"Relationship from_column '{rel.from_table}.{rel.from_column}' not found.",
                    path=f"{prefix}.from_column",
                )
            )

        if rel.to_table not in table_names:
            issues.append(
                ValidationIssue(
                    category="missing_table_ref",
                    message=f"Relationship to_table '{rel.to_table}' not found.",
                    path=f"{prefix}.to_table",
                )
            )
        elif rel.to_column not in column_lookup.get(rel.to_table, set()):
            issues.append(
                ValidationIssue(
                    category="missing_column_ref",
                    message=f"Relationship to_column '{rel.to_table}.{rel.to_column}' not found.",
                    path=f"{prefix}.to_column",
                )
            )

    return issues


def _validate_visual_positions(spec: DashboardSpec) -> list[ValidationIssue]:
    """Validate visual positions are within page grid bounds."""
    issues = []

    for pi, page in enumerate(spec.pages):
        grid_cols = page.layout.grid_columns
        grid_rows = page.layout.grid_rows

        for vi, visual in enumerate(page.visuals):
            pos = visual.position
            prefix = f"pages[{pi}].visuals[{vi}].position"

            if pos.x < 0:
                issues.append(
                    ValidationIssue(
                        category="invalid_position",
                        message=f"Visual x position ({pos.x}) is negative.",
                        path=prefix,
                    )
                )
            if pos.y < 0:
                issues.append(
                    ValidationIssue(
                        category="invalid_position",
                        message=f"Visual y position ({pos.y}) is negative.",
                        path=prefix,
                    )
                )
            if pos.width <= 0:
                issues.append(
                    ValidationIssue(
                        category="invalid_position",
                        message=f"Visual width ({pos.width}) must be positive.",
                        path=prefix,
                    )
                )
            if pos.height <= 0:
                issues.append(
                    ValidationIssue(
                        category="invalid_position",
                        message=f"Visual height ({pos.height}) must be positive.",
                        path=prefix,
                    )
                )
            if pos.x + pos.width > grid_cols:
                issues.append(
                    ValidationIssue(
                        category="out_of_bounds",
                        message=f"Visual exceeds grid columns: x({pos.x}) + width({pos.width}) > {grid_cols}.",
                        path=prefix,
                    )
                )
            if pos.y + pos.height > grid_rows:
                issues.append(
                    ValidationIssue(
                        category="out_of_bounds",
                        message=f"Visual exceeds grid rows: y({pos.y}) + height({pos.height}) > {grid_rows}.",
                        path=prefix,
                    )
                )

    return issues


def _validate_filter_refs(
    spec: DashboardSpec,
    table_names: set[str],
    column_lookup: dict[str, set[str]],
    all_measure_names: set[str],
) -> list[ValidationIssue]:
    """Validate filter field references."""
    issues = []

    for pi, page in enumerate(spec.pages):
        for fi, filt in enumerate(page.filters):
            issues.extend(
                _validate_field_ref(
                    filt.field,
                    f"pages[{pi}].filters[{fi}].field",
                    table_names,
                    column_lookup,
                    all_measure_names,
                )
            )

    return issues
