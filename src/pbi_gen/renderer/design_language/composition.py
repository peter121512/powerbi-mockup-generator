"""Composition engine — bridges page archetypes to PBIR visual generation.

Takes a PageSpec, selects an archetype, assigns visuals to regions,
adds structural primitives, and produces positioned visual dicts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pbi_gen.models.dashboard_spec import (
    DashboardSpec,
    FilterSpec,
    MeasureSpec,
    PageSpec,
    VisualSpec,
)
from pbi_gen.renderer.design_language.archetypes import (
    PageArchetype,
    VisualPlacement,
    assign_visuals_to_regions,
    select_archetype,
)
from pbi_gen.renderer.design_language.primitives import (
    make_divider,
    make_header_band,
    make_kpi_band_background,
    make_section_band,
)
from pbi_gen.renderer.design_language.variants import (
    DesignLanguageVariant,
    get_variant,
    select_variant_from_theme,
)
from pbi_gen.renderer.visuals import build_query_state, map_visual_type


def compose_page(
    page: PageSpec,
    spec: DashboardSpec,
    variant: Optional[DesignLanguageVariant] = None,
) -> list[dict]:
    """Compose a page using archetype-based placement and structural primitives.

    Args:
        page: The page specification.
        spec: Full dashboard spec (for measures, theme).
        variant: Design language variant to use. Defaults based on theme.

    Returns:
        List of all visual.json dicts (structural primitives + data visuals).
    """
    if variant is None:
        variant = select_variant_from_theme(spec.theme) if spec.theme else get_variant("executive_light")

    archetype = select_archetype(page)
    canvas_w = page.layout.width
    canvas_h = page.layout.height

    # Assign visuals to regions
    placements = assign_visuals_to_regions(
        page.visuals, page.filters, archetype, canvas_w, canvas_h
    )

    all_visuals: list[dict] = []

    # 1. Add minimal structural primitives (only those proven to help)
    # Skip header band and dividers — they consume canvas space without
    # materially improving scores. Focus on placement hierarchy instead.

    # KPI band background — subtle section grouping for cards
    kpi_region = next((r for r in archetype.regions if r.name == "kpi_band"), None)
    if kpi_region and "kpi_band" in placements and placements["kpi_band"]:
        kpi_y = int(kpi_region.y_start_pct * canvas_h)
        kpi_h = int((kpi_region.y_end_pct - kpi_region.y_start_pct) * canvas_h)
        kpi_bg = make_kpi_band_background(variant, y=kpi_y, height=kpi_h, canvas_width=canvas_w)
        all_visuals.append(kpi_bg)

    # 2. Generate data visuals with archetype-driven positioning
    z_base = 1000
    tab_order = 0

    from pbi_gen.renderer.design_language.composites import (
        build_composite_kpi,
        build_composite_chart,
    )

    for region_name, region_placements in placements.items():
        for placement in region_placements:
            # Find the original visual spec
            visual = next((v for v in page.visuals if v.id == placement.visual_id), None)
            if visual is None:
                # Must be a filter — handle separately
                filter_spec = next((f for f in page.filters if f.id == placement.visual_id), None)
                if filter_spec:
                    all_visuals.append(_build_filter_visual(
                        filter_spec, placement, variant, z_base, tab_order
                    ))
                    tab_order += 1
                    z_base += 1
                continue

            pbi_type, _, _ = map_visual_type(visual)
            query_state = build_query_state(visual, pbi_type, spec.measures)

            # Use composite components for cards and charts
            if pbi_type in ("card", "multiRowCard") and placement.is_kpi:
                parts = build_composite_kpi(
                    visual_id=visual.id,
                    title=visual.title or visual.id,
                    query_state=query_state,
                    variant=variant,
                    x=placement.x, y=placement.y,
                    width=placement.width, height=placement.height,
                    z_base=z_base,
                )
                all_visuals.extend(parts)
            elif pbi_type in ("clusteredBarChart", "clusteredColumnChart", "barChart",
                              "stackedBarChart", "stackedColumnChart", "lineChart",
                              "areaChart", "lineClusteredColumnComboChart",
                              "donutChart", "pieChart", "scatterChart"):
                parts = build_composite_chart(
                    visual_id=visual.id,
                    title=visual.title or visual.id,
                    pbi_type=pbi_type,
                    query_state=query_state,
                    variant=variant,
                    x=placement.x, y=placement.y,
                    width=placement.width, height=placement.height,
                    z_base=z_base,
                    is_hero=placement.is_hero,
                )
                all_visuals.extend(parts)
            else:
                # Fallback: plain visual with title
                visual_dict = _build_data_visual(
                    visual, placement, variant, spec.measures, z_base, tab_order
                )
                all_visuals.append(visual_dict)

            tab_order += 1
            z_base += 1

    return all_visuals


def _build_data_visual(
    visual: VisualSpec,
    placement: VisualPlacement,
    variant: DesignLanguageVariant,
    measures: list[MeasureSpec],
    z_index: int,
    tab_order: int,
) -> dict:
    """Build a PBIR visual dict with archetype-driven position and formatting."""
    pbi_type, _, _ = map_visual_type(visual)
    query_state = build_query_state(visual, pbi_type, measures)

    # Build formatting objects based on visual type
    objects = _build_visual_objects(visual, pbi_type, variant, placement)

    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": visual.id,
        "position": {
            "x": round(placement.x, 2),
            "y": round(placement.y, 2),
            "z": z_index,
            "width": round(placement.width, 2),
            "height": round(placement.height, 2),
            "tabOrder": tab_order,
        },
        "visual": {
            "visualType": pbi_type,
            "query": {"queryState": query_state},
            "objects": objects,
            "drillFilterOtherVisuals": True,
        },
    }


def _build_visual_objects(
    visual: VisualSpec,
    pbi_type: str,
    variant: DesignLanguageVariant,
    placement: VisualPlacement,
) -> dict:
    """Build formatting objects using proven-safe capabilities."""
    objects: dict = {}

    if pbi_type in ("card", "multiRowCard"):
        # Cards: just title and white background for surface contrast
        objects["general"] = [{"properties": {
            "title": {"expr": {"Literal": {"Value": f"'{visual.title or ''}'"}}},
            "background": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{variant.card_background}'"}}}}},
            "backgroundTransparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}]
        objects["categoryLabels"] = [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
        }}]

    elif pbi_type in ("clusteredBarChart", "clusteredColumnChart", "barChart",
                       "stackedBarChart", "stackedColumnChart", "lineChart",
                       "areaChart", "lineClusteredColumnComboChart"):
        # Charts: title + axis control + white background for contrast
        objects["general"] = [{"properties": {
            "title": {"expr": {"Literal": {"Value": f"'{visual.title or ''}'"}}},
            "background": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{variant.card_background}'"}}}}},
            "backgroundTransparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}]
        objects["categoryAxis"] = [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
        }}]
        objects["valueAxis"] = [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
            "gridlineShow": {"expr": {"Literal": {"Value": "true"}}},
        }}]

    elif visual.title:
        # All other visuals: title + white background
        objects["general"] = [{"properties": {
            "title": {"expr": {"Literal": {"Value": f"'{visual.title}'"}}},
            "background": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{variant.card_background}'"}}}}},
            "backgroundTransparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}]

    return objects


def _build_filter_visual(
    filter_spec: FilterSpec,
    placement: VisualPlacement,
    variant: DesignLanguageVariant,
    z_index: int,
    tab_order: int,
) -> dict:
    """Build a slicer visual from filter spec with archetype positioning."""
    from pbi_gen.renderer.visuals import build_projection

    projection = build_projection(filter_spec.field)
    query_state = {"Values": {"projections": [projection]}}

    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": filter_spec.id,
        "position": {
            "x": round(placement.x, 2),
            "y": round(placement.y, 2),
            "z": z_index,
            "width": round(placement.width, 2),
            "height": round(placement.height, 2),
            "tabOrder": tab_order,
        },
        "visual": {
            "visualType": "slicer",
            "query": {"queryState": query_state},
            "objects": {},
            "drillFilterOtherVisuals": True,
        },
    }
