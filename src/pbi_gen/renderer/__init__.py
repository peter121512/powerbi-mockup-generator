"""PBIP/PBIR Renderer — Stage 04.

Transforms a DashboardSpec into a complete Power BI Project (PBIP) on disk,
including the semantic model (TMDL), report definition (PBIR), theme, and
all supporting metadata.

Public API:
    render_powerbi_project(spec, output_dir) -> RenderResult
"""

from pbi_gen.renderer.layout import (
    CanvasPosition,
    grid_to_canvas,
    position_to_dict,
)
from pbi_gen.renderer.result import (
    FidelityManifest,
    RenderOutcome,
    RenderResult,
    ValidationCheck,
    ValidationResult,
    VisualFidelity,
)
from pbi_gen.renderer.service import render_powerbi_project
from pbi_gen.renderer.visuals import (
    VISUAL_TYPE_MAP,
    build_field_ref,
    build_query_ref,
    build_query_state,
    map_visual_type,
)

__all__ = [
    "render_powerbi_project",
    "RenderResult",
    "RenderOutcome",
    "FidelityManifest",
    "VisualFidelity",
    "ValidationResult",
    "ValidationCheck",
    "CanvasPosition",
    "grid_to_canvas",
    "position_to_dict",
    "VISUAL_TYPE_MAP",
    "build_field_ref",
    "build_query_ref",
    "build_query_state",
    "map_visual_type",
]
