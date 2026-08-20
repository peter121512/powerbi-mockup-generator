"""Design language module — page archetypes and composition regions.

Provides the structural foundation for placing visuals on Power BI report
pages according to enterprise design principles.
"""

from pbi_gen.renderer.design_language.archetypes import (
    CompositionRegion,
    PageArchetype,
    VisualPlacement,
    assign_visuals_to_regions,
    select_archetype,
)

__all__ = [
    "CompositionRegion",
    "PageArchetype",
    "VisualPlacement",
    "assign_visuals_to_regions",
    "select_archetype",
]
