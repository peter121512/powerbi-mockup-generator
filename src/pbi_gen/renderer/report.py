"""PBIR report generation.

Generates the report-side structure of a PBIP project: pages, visuals,
report config, and metadata files.
"""

from __future__ import annotations

from pbi_gen.models import DashboardSpec, FilterSpec, MeasureSpec, PageSpec, VisualSpec
from pbi_gen.renderer.layout import (
    CanvasPosition,
    DEFAULT_FILTER_ROW_HEIGHT,
    GUTTER,
    PAGE_MARGIN,
    grid_to_canvas,
    position_to_dict,
)
from pbi_gen.renderer.visuals import (
    build_active_projections,
    build_query_state,
    map_visual_type,
)


# ─────────────────────────────────────────────────────────────────────────────
# Filter row constants
# ─────────────────────────────────────────────────────────────────────────────

# Fixed pixel height for the filter/slicer row at the top of a page.
FILTER_ROW_HEIGHT = DEFAULT_FILTER_ROW_HEIGHT

# Minimum slicer width in pixels so they remain usable.
MIN_SLICER_WIDTH_PX = 120


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
    page_dict = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
        "name": page.id,
        "displayName": page.title,
        "displayOption": "FitToPage",
        "height": page.layout.height,
        "width": page.layout.width,
    }

    # Add subtle page background for enterprise polish
    page_dict["objects"] = {
        "background": [
            {
                "properties": {
                    "color": {
                        "solid": {
                            "color": {
                                "expr": {
                                    "Literal": {"Value": "'#F5F6F8'"}
                                }
                            }
                        }
                    },
                    "transparency": {
                        "expr": {
                            "Literal": {"Value": "0D"}
                        }
                    },
                }
            }
        ]
    }

    return page_dict


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
    filter_row_height: int = 0,
    design_system=None,
) -> dict:
    """Generate the visual.json for a single visual.

    Args:
        visual: The visual specification.
        page: The parent page (for layout context).
        z_index: Z-order for the visual.
        tab_order: Tab order for accessibility.
        measures: Available measures for field type resolution.
        filter_row_height: Pixel height reserved for the filter row at the
            top of the page.  When > 0 the grid origin is shifted downward
            so visuals don't overlap slicers.

    Returns:
        The visual definition dict.
    """
    pbi_type, _, _ = map_visual_type(visual)

    # Determine filter row offset — if the page has filters, reserve space
    effective_filter_height = filter_row_height
    if effective_filter_height == 0 and page.filters:
        effective_filter_height = FILTER_ROW_HEIGHT

    # Compute canvas position
    canvas_pos = grid_to_canvas(
        visual.position,
        page.layout,
        z_index=z_index,
        tab_order=tab_order,
        filter_row_height=effective_filter_height,
    )

    # Build query state
    query_state = build_query_state(visual, pbi_type, measures)
    active_projections = build_active_projections(query_state)

    # Apply design system formatting
    from pbi_gen.renderer.design_system import EnterpriseDesignSystem
    from pbi_gen.renderer.formatting.cards import build_card_objects
    from pbi_gen.renderer.formatting.charts import build_chart_objects
    from pbi_gen.renderer.formatting.tables import build_table_objects

    objects = {}
    if pbi_type == "card" or pbi_type == "multiRowCard":
        # Cards: proven-safe properties (title, labels fontSize/color, categoryLabels)
        if design_system and visual.title:
            ds = design_system
            objects = {
                "general": [{"properties": {
                    "title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}},
                }}],
                "labels": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "fontSize": {"expr": {"Literal": {"Value": f"{min(ds.typography.kpi_value, 22)}D"}}},
                    "color": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{ds.colours.primary_series_color}'"}}}}},
                    "labelDisplayUnits": {"expr": {"Literal": {"Value": "0"}}},
                }}],
                "categoryLabels": [{"properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                }}],
            }
        elif visual.title:
            objects = {"general": [{"properties": {"title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}}}}]}
    elif pbi_type in ("clusteredBarChart", "clusteredColumnChart", "barChart",
                       "stackedBarChart", "stackedColumnChart", "lineChart",
                       "areaChart", "lineClusteredColumnComboChart"):
        # Charts: proven-safe axis/gridline properties
        chart_objects = {}
        if visual.title:
            chart_objects["general"] = [{"properties": {"title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}}}}]
        if design_system:
            chart_objects["categoryAxis"] = [{"properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}},
                "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
            }}]
            chart_objects["valueAxis"] = [{"properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}},
                "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
                "gridlineShow": {"expr": {"Literal": {"Value": "true"}}},
            }}]
        objects = chart_objects
    elif pbi_type in ("tableEx", "pivotTable"):
        # Tables: title only (safe)
        if visual.title:
            objects = {"general": [{"properties": {"title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}}}}]}
    elif visual.title:
        # All other visuals: title only
        objects = {"general": [{"properties": {"title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}}}}]}

    # Fallback
    if not objects and visual.title:
        objects = {"general": [{"properties": {"title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}}}}]}

    visual_dict: dict = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": visual.id,
        "position": position_to_dict(canvas_pos),
        "visual": {
            "visualType": pbi_type,
            "query": {
                "queryState": query_state,
            },
            "objects": objects,
            "drillFilterOtherVisuals": True,
        },
    }

    return visual_dict

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
            "drillFilterOtherVisuals": True,
        },
    }

    # Add title via visual header if visual has a title
    if visual.title:
        visual_dict["visual"]["objects"] = {
            "general": [
                {
                    "properties": {
                        "title": {
                            "expr": {
                                "Literal": {"Value": f"'{visual.title}'"}
                            }
                        }
                    }
                }
            ]
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

    Filters are rendered as slicer visuals placed in a dedicated row at the
    TOP of the page, inside page margins, distributed horizontally with
    proper spacing.

    Args:
        filter_spec: The filter specification.
        page: The parent page.
        z_index: Z-order.
        tab_order: Tab navigation order.
        position_index: Index for horizontal positioning among sibling slicers.

    Returns:
        Visual definition dict for the slicer.
    """
    from pbi_gen.renderer.visuals import build_projection

    # Determine how many slicers share this row
    num_slicers = max(len(page.filters), 1)

    # Usable horizontal space inside page margins
    usable_width = page.layout.width - 2 * PAGE_MARGIN

    # Distribute slicers evenly with gutters between them
    total_gutter_space = (num_slicers - 1) * GUTTER
    slicer_width = (usable_width - total_gutter_space) / num_slicers

    # Enforce minimum width — if too narrow, let them overflow off-screen
    # gracefully (but typically 12 columns / few slicers is fine)
    slicer_width = max(slicer_width, MIN_SLICER_WIDTH_PX)

    # Compute x position for this slicer
    x_px = PAGE_MARGIN + position_index * (slicer_width + GUTTER)

    # Clamp width so slicer doesn't exceed right margin
    max_right = page.layout.width - PAGE_MARGIN
    if x_px + slicer_width > max_right:
        slicer_width = max(max_right - x_px, 0)

    # Y position: inside top margin
    y_px = PAGE_MARGIN

    # Build canvas position directly (no grid translation needed)
    canvas_pos = CanvasPosition(
        x=round(x_px, 2),
        y=round(y_px, 2),
        z=z_index,
        width=round(slicer_width, 2),
        height=float(FILTER_ROW_HEIGHT),
        tab_order=tab_order,
    )

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
