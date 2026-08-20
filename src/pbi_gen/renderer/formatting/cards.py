"""PBIR objects builder for Card / KPI visuals.

Generates the `objects` dictionary used in a PBIR visual definition to style
card visuals (callout value, category label, title, background).

The PBIR objects format uses the pattern:
    {"section": [{"properties": {"prop": {"expr": {"Literal": {"Value": "..."}}}}}]}
"""

from __future__ import annotations

from typing import Any

from pbi_gen.models.dashboard_spec import VisualSpec
from pbi_gen.renderer.design_system import EnterpriseDesignSystem


def _literal(value: str) -> dict[str, Any]:
    """Wrap a value in PBIR literal expression format."""
    return {"expr": {"Literal": {"Value": value}}}


def _bool_literal(value: bool) -> dict[str, Any]:
    """Wrap a boolean in PBIR literal format."""
    return _literal("true" if value else "false")


def _string_literal(value: str) -> dict[str, Any]:
    """Wrap a string in PBIR literal format (single-quoted)."""
    return _literal(f"'{value}'")


def _number_literal(value: float | int) -> dict[str, Any]:
    """Wrap a number in PBIR literal format."""
    # PBIR numbers are expressed as string-encoded values with D suffix for decimals
    if isinstance(value, float):
        return _literal(f"{value}D")
    return _literal(str(value))


def _color_literal(hex_color: str) -> dict[str, Any]:
    """Wrap a colour hex value in PBIR solid fill format."""
    return {"solid": {"color": _literal(f"'{hex_color}'")}}


def build_card_objects(
    design_system: EnterpriseDesignSystem,
    visual_spec: VisualSpec,
) -> dict[str, Any]:
    """Build the PBIR `objects` dict for a card/KPI visual.

    Applies conservative enterprise styling using only known-safe PBIR properties:
    - Title: visible with clean text
    - Callout value (labels): large font size for KPI prominence
    - Category label (categoryLabels): show for context

    Args:
        design_system: The resolved EnterpriseDesignSystem instance.
        visual_spec: The VisualSpec for this card visual.

    Returns:
        PBIR objects dict ready for inclusion in the visual definition.
    """
    ds = design_system
    typo = ds.typography

    objects: dict[str, list[dict[str, Any]]] = {}

    # General — title only (known-safe)
    title_text = visual_spec.title or ""
    if title_text:
        objects["general"] = [{"properties": {
            "title": _string_literal(title_text),
        }}]

    # Labels — callout value with large font for KPI prominence
    objects["labels"] = [{"properties": {
        "show": _bool_literal(True),
        "fontSize": _number_literal(typo.kpi_value),
        "labelDisplayUnits": _number_literal(0),
    }}]

    # Category labels — show the field name as context
    objects["categoryLabels"] = [{"properties": {
        "show": _bool_literal(True),
    }}]

    return objects
