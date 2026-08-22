"""Premium template registry for Power BI PBIP/PBIR generation.

Provides reusable visual templates, design tokens, and a page builder that
generates complete PBIR definition parts from configuration rather than
hard-coded visual JSON.

Key classes:
    DesignTokens — centralised dark-premium colour, spacing, typography tokens
    DataRole — data role slot definition within a visual template
    FieldRef — reference to a semantic model column or measure
    VisualTemplate — reusable visual template definition
    VisualBinding — concrete binding of a template to data + position
    PageShell — page chrome definition (nav, title, slicers)
    TemplateRegistry — registry of available templates with lookup
    PageBuilder — builds complete PBIR parts from shell + bindings
"""

from __future__ import annotations

from pbi_gen.renderer.templates.builder import PageBuilder, PbipPart
from pbi_gen.renderer.templates.registry import (
    CUSTOM_VISUAL_GUIDS,
    DataRole,
    DesignTokens,
    FieldRef,
    PageShell,
    TemplateRegistry,
    VisualBinding,
    VisualTemplate,
)

__all__ = [
    "CUSTOM_VISUAL_GUIDS",
    "DataRole",
    "DesignTokens",
    "FieldRef",
    "PageBuilder",
    "PageShell",
    "PbipPart",
    "TemplateRegistry",
    "VisualBinding",
    "VisualTemplate",
]
