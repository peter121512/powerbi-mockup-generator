"""PBIR report generation.

Generates the report-side structure of a PBIP project: pages, visuals,
report config, and metadata files.
"""

from __future__ import annotations

from pbi_gen.models import DashboardSpec, FilterSpec, MeasureSpec, PageSpec, VisualSpec
from pbi_gen.renderer.layout import CanvasPosition, grid_to_canvas, position_to_dict
from pbi_gen.renderer.visuals import (
    build_active_projections,
    build_query_state,
    map_visual_type,
)


# ─────────────────────────────────────────────────────────────────────────────
# Report-level files
# ─────────────────────────────────────────────────────────────────────────────


def generate_report_json() -> dict:
    """Generate the top-level report.json configuration."""
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU06",
                "reportVersionAtImport": "5.61",
                "type": "SharedResources",
            },
            "customTheme": {
                "name": "theme.json",
                "reportVersionAtImport": "5.61",
                "type": "RegisteredResources",
            },
        },
        "layoutOptimization": "None",
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": "CY24SU06",
                        "type": "BaseTheme",
                        "path": "BaseThemes/CY24SU06.json",
                    }
                ],
            },
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": [
                    {
                        "name": "theme.json",
                        "type": "CustomTheme",
                        "path": "theme.json",
                    }
                ],
            },
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultFilterActionIsDataFilter": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "allowInlineExploration": True,
            "useEnhancedTooltips": True,
        },
    }


def generate_version_json() -> dict:
    """Generate version.json."""
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    }


def generate_definition_pbir(project_name: str) -> dict:
    """Generate definition.pbir linking report to semantic model."""
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {
            "byPath": {
                "path": f"../{project_name}.SemanticModel",
            }
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────


def generate_pages_json(pages: list[PageSpec]) -> dict:
    """Generate the pages.json metadata file.

    Args:
        pages: List of page specs, ordered by sort_order.

    Returns:
        The pages metadata dict.
    """
    sorted_pages = sorted(pages, key=lambda p: p.sort_order)
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.id for p in sorted_pages],
        "activePageName": sorted_pages[0].id if sorted_pages else "",
    }


def generate_page_json(page: PageSpec) -> dict:
    """Generate the page.json for a single page.

    Args:
        page: The page specification.

    Returns:
        The page definition dict.
    """
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
        "name": page.id,
        "displayName": page.title,
        "displayOption": "FitToPage",
        "height": page.layout.height,
        "width": page.layout.width,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Visuals
# ─────────────────────────────────────────────────────────────────────────────


def generate_visual_json(
    visual: VisualSpec,
    page: PageSpec,
    *,
    z_index: int = 1000,
    tab_order: int = 0,
    measures: list[MeasureSpec] | None = None,
) -> dict:
    """Generate the visual.json for a single visual.

    Args:
        visual: The visual specification.
        page: The parent page (for layout context).
        z_index: Z-order for the visual.
        tab_order: Tab order for accessibility.
        measures: Available measures for field type resolution.

    Returns:
        The visual definition dict.
    """
    pbi_type, _, _ = map_visual_type(visual)

    # Compute canvas position
    canvas_pos = grid_to_canvas(
        visual.position,
        page.layout,
        z_index=z_index,
        tab_order=tab_order,
    )

    # Build query state
    query_state = build_query_state(visual, pbi_type, measures)
    active_projections = build_active_projections(query_state)

    visual_dict: dict = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": visual.id,
        "position": position_to_dict(canvas_pos),
        "visual": {
            "visualType": pbi_type,
            "query": {
                "queryState": query_state,
            },
            "objects": {},
        },
    }

    return visual_dict


def generate_filter_visual_json(
    filter_spec: FilterSpec,
    page: PageSpec,
    *,
    z_index: int = 500,
    tab_order: int = 0,
    position_index: int = 0,
) -> dict:
    """Generate a slicer visual from a filter spec.

    Filters in the spec are rendered as slicer visuals placed at the top
    of the page.

    Args:
        filter_spec: The filter specification.
        page: The parent page.
        z_index: Z-order.
        tab_order: Tab navigation order.
        position_index: Index for horizontal positioning.

    Returns:
        Visual definition dict for the slicer.
    """
    from pbi_gen.models import VisualPosition
    from pbi_gen.renderer.visuals import build_projection

    # Position slicers at bottom of grid
    grid_rows = page.layout.grid_rows
    slicer_width = max(1, page.layout.grid_columns // max(len(page.filters), 1))
    pos = VisualPosition(
        x=position_index * slicer_width,
        y=grid_rows - 1,
        width=slicer_width,
        height=1,
    )

    canvas_pos = grid_to_canvas(pos, page.layout, z_index=z_index, tab_order=tab_order)

    # Build slicer query
    projection = build_projection(filter_spec.field)
    query_state = {"Values": {"projections": [projection]}}

    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": filter_spec.id,
        "position": position_to_dict(canvas_pos),
        "visual": {
            "visualType": "slicer",
            "query": {
                "queryState": query_state,
            },
            "objects": {},
        },
    }
