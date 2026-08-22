"""Page builder for generating PBIP/PBIR definition parts from templates.

Translates a PageShell + VisualBindings + DesignTokens into the full list of
PBIP definition parts (base64 payloads) matching the structure expected by
Fabric REST API createReport.
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field

from pbi_gen.renderer.templates.registry import (
    DesignTokens,
    FieldRef,
    PageShell,
    TemplateRegistry,
    VisualBinding,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper types
# ─────────────────────────────────────────────────────────────────────────────


class PbipPart(BaseModel):
    """A single PBIP definition part (path + payload)."""

    path: str
    payload: str  # base64-encoded JSON or binary
    payload_type: str = "InlineBase64"

    def to_api_dict(self) -> dict:
        """Serialise for Fabric REST API."""
        return {
            "path": self.path,
            "payload": self.payload,
            "payloadType": self.payload_type,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Visual JSON generators
# ─────────────────────────────────────────────────────────────────────────────


def _literal(value: str) -> dict:
    """Wrap a value in PBI Literal expression."""
    return {"expr": {"Literal": {"Value": value}}}


def _solid_color_expr(hex_color: str) -> dict:
    """Wrap a colour in PBI solid color expression."""
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hex_color}'"}}}}}


def _vis_container(name: str, x: int, y: int, w: int, h: int, z: int) -> dict:
    """Create a visual container scaffold."""
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
    }


def _build_field_expr(field: FieldRef) -> dict:
    """Build the Power BI field expression for a FieldRef."""
    if field.is_measure:
        return {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": field.entity}},
                "Property": field.property,
            }
        }
    return {
        "Column": {
            "Expression": {"SourceRef": {"Entity": field.entity}},
            "Property": field.property,
        }
    }


def _build_projection(field: FieldRef) -> dict:
    """Build a query projection for a single field."""
    return {
        "field": _build_field_expr(field),
        "queryRef": field.resolved_query_ref,
        "nativeQueryRef": field.property,
    }


# Native Power BI visuals use specific capitalized query state key names.
# Map from our template data-role names to native PBI query state keys.
_NATIVE_QUERY_STATE_KEYS: dict[str, dict[str, str]] = {
    "barChart": {"category": "Category", "values": "Y"},
    "donutChart": {"category": "Category", "values": "Y"},
    "columnChart": {"category": "Category", "values": "Y"},
    "lineChart": {"category": "Category", "values": "Y"},
    "tableEx": {"columns": "Values", "values": "Values"},
}


def _build_query_state(binding: VisualBinding, registry: TemplateRegistry) -> dict:
    """Build the queryState for a visual based on template data roles and bindings."""
    template = registry.get(binding.template_id)
    query_state: dict[str, Any] = {}

    # Determine key mapping for native visuals
    key_map = _NATIVE_QUERY_STATE_KEYS.get(template.visual_type, {})

    for role in template.data_roles:
        fields = binding.data_bindings.get(role.name, [])
        if not fields:
            continue
        projections = [_build_projection(f) for f in fields]
        # Use native key name if available, otherwise use role name
        state_key = key_map.get(role.name, role.name)
        if state_key in query_state:
            # Merge projections if multiple roles map to same key (e.g. tableEx)
            query_state[state_key]["projections"].extend(projections)
        else:
            query_state[state_key] = {"projections": projections}

    return query_state


def _build_visual_container_objects(
    binding: VisualBinding,
    tokens: DesignTokens,
    template_id: str,
) -> dict:
    """Build visualContainerObjects (title, background, border, padding)."""
    objs: dict[str, Any] = {}

    # Title
    show_title = binding.title != ""
    title_props: dict[str, Any] = {"show": _literal("true" if show_title else "false")}
    if show_title:
        title_props["text"] = _literal(f"'{binding.title}'")
        title_props["fontColor"] = _solid_color_expr(tokens.text_secondary)
        title_props["fontSize"] = _literal(f"{tokens.section_size}D")
    objs["title"] = [{"properties": title_props}]

    # Background — custom visuals get transparent; native visuals get surface card
    is_custom = len(template_id) > 20 or template_id.startswith("premium")
    template_visual_type = template_id  # fallback
    # Determine if the actual visual type is custom (GUID-length)
    overrides = binding.config_overrides

    show_bg = overrides.get("show_background", not _is_custom_visual_type(template_id))
    if show_bg:
        objs["background"] = [{"properties": {
            "show": _literal("true"),
            "color": _solid_color_expr(tokens.surface),
            "transparency": _literal("0D"),
        }}]
    else:
        objs["background"] = [{"properties": {"show": _literal("false")}}]

    # Border
    show_border = overrides.get("show_border", show_bg)
    if show_border:
        objs["border"] = [{"properties": {
            "show": _literal("true"),
            "color": _solid_color_expr(tokens.border),
        }}]
    else:
        objs["border"] = [{"properties": {"show": _literal("false")}}]

    # Padding (custom visuals use zero padding)
    if not show_bg:
        objs["padding"] = [{"properties": {
            "top": _literal("0D"),
            "bottom": _literal("0D"),
            "left": _literal("0D"),
            "right": _literal("0D"),
        }}]

    return objs


def _is_custom_visual_type(visual_type: str) -> bool:
    """Determine if a visual type string is a custom-visual GUID."""
    return len(visual_type) > 20


def _build_native_objects(
    binding: VisualBinding,
    tokens: DesignTokens,
    visual_type: str,
) -> dict:
    """Build inner 'objects' for native visuals (labels, axes, etc.)."""
    objects: dict[str, Any] = {}

    if visual_type == "barChart":
        objects["labels"] = [{"properties": {
            "show": _literal("true"),
            "color": _solid_color_expr(tokens.text_secondary),
            "fontSize": _literal(f"{tokens.axis_size}D"),
        }}]
        objects["categoryAxis"] = [{"properties": {
            "showAxisTitle": _literal("false"),
            "labelColor": _solid_color_expr(tokens.text_muted),
        }}]
        objects["valueAxis"] = [{"properties": {
            "showAxisTitle": _literal("false"),
            "labelColor": _solid_color_expr(tokens.text_subtle),
            "gridlineColor": _solid_color_expr(tokens.border),
        }}]

    elif visual_type == "donutChart":
        objects["legend"] = [{"properties": {
            "showTitle": _literal("false"),
            "labelColor": _solid_color_expr(tokens.text_muted),
        }}]
        objects["labels"] = [{"properties": {
            "color": _solid_color_expr(tokens.text_muted),
        }}]

    elif visual_type == "tableEx":
        objects["grid"] = [{"properties": {
            "gridVertical": _literal("false"),
            "gridHorizontal": _literal("true"),
            "gridHorizontalColor": _solid_color_expr(tokens.border),
        }}]
        objects["columnHeaders"] = [{"properties": {
            "fontColor": _solid_color_expr(tokens.text_secondary),
            "backColor": _solid_color_expr(tokens.surface),
        }}]
        objects["values"] = [{"properties": {
            "fontColor": _solid_color_expr(tokens.text_muted),
            "backColor": _solid_color_expr(tokens.canvas),
        }}]

    # Apply any explicit overrides from binding
    for key, val in binding.config_overrides.get("objects", {}).items():
        objects[key] = val

    return objects


def _build_visual_json(
    binding: VisualBinding,
    tokens: DesignTokens,
    registry: TemplateRegistry,
    z_index: int,
) -> dict:
    """Build the complete visual.json for a single binding."""
    template = registry.get(binding.template_id)
    x, y, w, h = binding.position

    container = _vis_container(
        name=binding.template_id.replace("premium_", "") + f"_{z_index}",
        x=x, y=y, w=w, h=h, z=z_index,
    )

    visual: dict[str, Any] = {
        "visualType": template.visual_type,
        "query": {"queryState": _build_query_state(binding, registry)},
        "visualContainerObjects": _build_visual_container_objects(
            binding, tokens, template.visual_type,
        ),
        "drillFilterOtherVisuals": template.supports_cross_filter,
    }

    # Add native objects for non-custom visuals
    if not _is_custom_visual_type(template.visual_type):
        native_objects = _build_native_objects(binding, tokens, template.visual_type)
        if native_objects:
            visual["objects"] = native_objects

    container["visual"] = visual
    return container


# ─────────────────────────────────────────────────────────────────────────────
# Nav Rail builder
# ─────────────────────────────────────────────────────────────────────────────


def _build_nav_rail_visuals(
    shell: PageShell,
    tokens: DesignTokens,
    dummy_field: FieldRef,
) -> list[tuple[str, dict]]:
    """Generate visual JSON dicts for the navigation rail."""
    parts: list[tuple[str, dict]] = []
    nav_width = 140

    # Nav background
    nav_bg = _vis_container("nav_rail", 0, 0, nav_width, shell.height, 1)
    nav_bg["visual"] = {
        "visualType": "textbox",
        "objects": {
            "general": [{"properties": {
                "paragraphs": _literal('[{"textRuns":[{"value":" ","textStyle":{}}]}]'),
            }}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {"show": _literal("false")}}],
            "background": [{"properties": {
                "show": _literal("true"),
                "color": _solid_color_expr(tokens.nav),
                "transparency": _literal("0D"),
            }}],
            "border": [{"properties": {
                "show": _literal("true"),
                "color": _solid_color_expr(tokens.border),
            }}],
        },
        "drillFilterOtherVisuals": False,
    }
    parts.append(("nav_rail", nav_bg))

    # Active indicator line
    active_idx = 0
    for i, (_, page_name) in enumerate(shell.nav_items):
        if page_name == shell.active_nav:
            active_idx = i
            break

    indicator_y = 78 + active_idx * 42
    indicator = _vis_container("nav_indicator", 0, indicator_y, 4, 36, 3)
    indicator["visual"] = {
        "visualType": "textbox",
        "objects": {
            "general": [{"properties": {
                "paragraphs": _literal('[{"textRuns":[{"value":" ","textStyle":{}}]}]'),
            }}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {"show": _literal("false")}}],
            "background": [{"properties": {
                "show": _literal("true"),
                "color": _solid_color_expr(tokens.accent_blue),
                "transparency": _literal("0D"),
            }}],
            "border": [{"properties": {"show": _literal("false")}}],
        },
        "drillFilterOtherVisuals": False,
    }
    parts.append(("nav_indicator", indicator))

    # Nav items
    for ni, (label, page_name) in enumerate(shell.nav_items):
        is_active = page_name == shell.active_nav
        ny = 75 + ni * 42
        color = tokens.accent_blue if is_active else tokens.text_muted

        nav_card = _vis_container(f"nav_item_{ni}", 8, ny, 126, 36, 4)
        nav_card["visual"] = {
            "visualType": "cardVisual",
            "query": {"queryState": {"Values": {"projections": [_build_projection(dummy_field)]}}},
            "visualContainerObjects": {
                "title": [{"properties": {
                    "show": _literal("true"),
                    "text": _literal(f"'{label}'"),
                    "fontColor": _solid_color_expr(color),
                    "fontSize": _literal("9D"),
                    "bold": _literal("true" if is_active else "false"),
                }}],
                "background": [{"properties": {"show": _literal("false")}}],
                "border": [{"properties": {"show": _literal("false")}}],
            },
            "drillFilterOtherVisuals": False,
        }
        parts.append((f"nav_item_{ni}", nav_card))

    return parts


# ─────────────────────────────────────────────────────────────────────────────
# Title & Slicer builders
# ─────────────────────────────────────────────────────────────────────────────


def _build_title_visual(
    shell: PageShell,
    tokens: DesignTokens,
    dummy_field: FieldRef,
    nav_width: int = 140,
) -> tuple[str, dict]:
    """Build the page title visual."""
    x = nav_width + tokens.page_margin + 5
    title_vis = _vis_container("pagetitle", x, 4, 500, 56, 4999)
    title_vis["visual"] = {
        "visualType": "cardVisual",
        "query": {"queryState": {"Values": {"projections": [_build_projection(dummy_field)]}}},
        "visualContainerObjects": {
            "title": [{"properties": {
                "show": _literal("true"),
                "text": _literal(f"'{shell.title}'"),
                "fontColor": _solid_color_expr(tokens.text_primary),
                "fontSize": _literal(f"{tokens.title_size}D"),
                "bold": _literal("true"),
            }}],
            "subTitle": [{"properties": {
                "show": _literal("true"),
                "text": _literal(f"'{shell.subtitle}'"),
                "fontColor": _solid_color_expr(tokens.text_subtle),
                "fontSize": _literal("10D"),
            }}],
            "background": [{"properties": {"show": _literal("false")}}],
            "border": [{"properties": {"show": _literal("false")}}],
        },
        "drillFilterOtherVisuals": True,
    }
    return ("pagetitle", title_vis)


def _build_slicer_visual(
    field: FieldRef,
    tokens: DesignTokens,
    index: int,
    base_x: int = 780,
    y: int = 6,
    width: int = 220,
    height: int = 72,
) -> tuple[str, dict]:
    """Build a dropdown slicer visual for a field."""
    x = base_x + index * (width + 15)
    name = f"slicer_{field.property.lower()}"

    slicer = _vis_container(name, x, y, width, height, 5000 + index)
    slicer["visual"] = {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [_build_projection(field)]}}},
        "objects": {
            "data": [{"properties": {"mode": _literal("'Dropdown'")}}],
            "selection": [{"properties": {
                "selectAllCheckboxEnabled": _literal("true"),
                "singleSelect": _literal("false"),
            }}],
            "general": [{"properties": {
                "outlineColor": _solid_color_expr("#334155"),
                "outlineWeight": _literal("1D"),
            }}],
            "items": [{"properties": {
                "fontColor": _solid_color_expr(tokens.text_secondary),
                "background": _solid_color_expr(tokens.border),
                "textSize": _literal("10D"),
            }}],
            "dropdown": [{"properties": {
                "fontColor": _solid_color_expr(tokens.text_secondary),
                "background": _solid_color_expr(tokens.border),
            }}],
            "header": [{"properties": {"show": _literal("false")}}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {
                "show": _literal("true"),
                "text": _literal(f"'📍 {field.property}'"),
                "fontColor": _solid_color_expr(tokens.text_secondary),
                "fontSize": _literal("9D"),
            }}],
            "background": [{"properties": {
                "show": _literal("true"),
                "color": _solid_color_expr(tokens.border),
                "transparency": _literal("0D"),
            }}],
            "border": [{"properties": {
                "show": _literal("true"),
                "color": _solid_color_expr("#475569"),
            }}],
            "padding": [{"properties": {
                "top": _literal("2D"),
                "bottom": _literal("2D"),
                "left": _literal("4D"),
                "right": _literal("4D"),
            }}],
        },
        "drillFilterOtherVisuals": True,
    }
    return (name, slicer)


# ─────────────────────────────────────────────────────────────────────────────
# Page Builder
# ─────────────────────────────────────────────────────────────────────────────


class PageBuilder(BaseModel):
    """Builds a complete PBIP/PBIR definition from page shell, tokens, and bindings.

    Usage:
        builder = PageBuilder(shell=shell, tokens=tokens, registry=registry)
        builder.add_visual(binding1)
        builder.add_visual(binding2)
        parts = builder.build_pbir_parts()
    """

    shell: PageShell
    tokens: DesignTokens = Field(default_factory=DesignTokens)
    registry: TemplateRegistry = Field(default_factory=TemplateRegistry.default)
    bindings: list[VisualBinding] = Field(default_factory=list)

    # Report metadata
    report_name: str = ""
    semantic_model_name: str = ""
    semantic_model_id: str = ""
    theme_name: str = "ExecutiveDark"

    def add_visual(self, binding: VisualBinding) -> None:
        """Add a visual binding to this page."""
        # Validate template exists
        self.registry.get(binding.template_id)
        self.bindings.append(binding)

    def custom_visual_packages(self) -> list[str]:
        """Return list of custom-visual GUIDs needing packaging."""
        guids: set[str] = set()
        for b in self.bindings:
            template = self.registry.get(b.template_id)
            if _is_custom_visual_type(template.visual_type):
                guids.add(template.visual_type)
        return sorted(guids)

    @property
    def _connection_string(self) -> str:
        """Build the semantic model connection string."""
        catalog = self.semantic_model_name or "UnspecifiedModel"
        sm_id = self.semantic_model_id or "00000000-0000-0000-0000-000000000000"
        return (
            f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;"
            f"initial catalog={catalog};"
            f"integrated security=ClaimsToken;"
            f"semanticmodelid={sm_id}"
        )

    @property
    def _report_display_name(self) -> str:
        return self.report_name or self.shell.display_name

    def _get_dummy_field(self) -> FieldRef:
        """Get a dummy field for structural visuals (nav, title).

        Uses the first measure from the first binding, or a fallback.
        """
        for b in self.bindings:
            for fields in b.data_bindings.values():
                for f in fields:
                    if f.is_measure:
                        return f
        # Fallback
        return FieldRef(entity="Measure", property="Value", is_measure=True)

    def build_pbir_parts(self) -> list[dict]:
        """Generate the full list of PBIP definition parts for Fabric REST API.

        Returns list of dicts with keys: path, payload, payloadType.
        """
        parts: list[dict] = []

        def _add_json(path: str, obj: Any) -> None:
            encoded = base64.b64encode(
                json.dumps(obj, ensure_ascii=False).encode()
            ).decode()
            parts.append({"path": path, "payload": encoded, "payloadType": "InlineBase64"})

        def _add_binary(path: str, data: bytes) -> None:
            parts.append({"path": path, "payload": base64.b64encode(data).decode(), "payloadType": "InlineBase64"})

        # ── .platform ──
        _add_json(".platform", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": self._report_display_name},
            "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
        })

        # ── definition.pbir ──
        _add_json("definition.pbir", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byConnection": {"connectionString": self._connection_string}},
        })

        # ── definition/version.json ──
        _add_json("definition/version.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        })

        # ── definition/report.json ──
        custom_guids = self.custom_visual_packages()
        resource_packages: list[dict] = [
            {"name": "SharedResources", "type": "SharedResources", "items": [
                {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
            ]},
            {"name": "RegisteredResources", "type": "RegisteredResources", "items": [
                {"name": self.theme_name, "type": "CustomTheme", "path": f"{self.theme_name}.json"}
            ]},
        ]
        for guid in custom_guids:
            resource_packages.append({
                "name": guid,
                "type": "CustomVisual",
                "items": [
                    {"name": f"{guid}.pbiviz.json", "type": "CustomVisualMetadata", "path": f"{guid}.pbiviz.json"},
                ],
            })

        _add_json("definition/report.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
            "themeCollection": {
                "baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"},
                "customTheme": {"name": self.theme_name, "reportVersionAtImport": "5.61", "type": "RegisteredResources"},
            },
            "layoutOptimization": "None",
            "resourcePackages": resource_packages,
        })

        # ── Theme ──
        theme_json = self.tokens.to_pbi_theme(self.theme_name)
        _add_binary(
            f"StaticResources/RegisteredResources/{self.theme_name}.json",
            json.dumps(theme_json).encode("utf-8"),
        )

        # ── Pages metadata ──
        page_name = self.shell.page_name
        _add_json("definition/pages/pages.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [page_name],
            "activePageName": page_name,
        })

        # ── Page definition ──
        _add_json(f"definition/pages/{page_name}/page.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
            "name": page_name,
            "displayName": self.shell.display_name,
            "displayOption": "FitToPage",
            "height": self.shell.height,
            "width": self.shell.width,
            "objects": {
                "background": [{"properties": {
                    "color": {"solid": {"color": _literal(f"'{self.tokens.canvas}'")["expr"]}},
                    "transparency": _literal("0D")["expr"],
                }}],
            },
        })

        # ── Structural visuals (nav, title, slicers) ──
        dummy_field = self._get_dummy_field()

        # Nav rail
        nav_parts = _build_nav_rail_visuals(self.shell, self.tokens, dummy_field)
        for vis_name, vis_json in nav_parts:
            _add_json(
                f"definition/pages/{page_name}/visuals/{vis_name}/visual.json",
                vis_json,
            )

        # Page title
        title_name, title_json = _build_title_visual(self.shell, self.tokens, dummy_field)
        _add_json(
            f"definition/pages/{page_name}/visuals/{title_name}/visual.json",
            title_json,
        )

        # Slicers
        for idx, slicer_field in enumerate(self.shell.slicers):
            slicer_name, slicer_json = _build_slicer_visual(
                slicer_field, self.tokens, idx,
            )
            _add_json(
                f"definition/pages/{page_name}/visuals/{slicer_name}/visual.json",
                slicer_json,
            )

        # ── Content visuals ──
        for z_idx, binding in enumerate(self.bindings, start=10):
            vis_json = _build_visual_json(binding, self.tokens, self.registry, z_idx)
            vis_name = vis_json["name"]
            _add_json(
                f"definition/pages/{page_name}/visuals/{vis_name}/visual.json",
                vis_json,
            )

        # ── Custom visual packages (placeholder entries) ──
        # The actual .pbiviz bytes must be supplied externally; we emit the
        # required path entries with empty placeholders that callers fill in.
        for guid in custom_guids:
            # Package.json placeholder — callers replace payload with real bytes
            parts.append({
                "path": f"CustomVisuals/{guid}/package.json",
                "payload": "",  # Must be populated from .pbiviz archive
                "payloadType": "InlineBase64",
            })
            parts.append({
                "path": f"CustomVisuals/{guid}/resources/{guid}.pbiviz.json",
                "payload": "",  # Must be populated from .pbiviz archive
                "payloadType": "InlineBase64",
            })

        return parts

    def build_pbir_parts_with_visuals(
        self,
        visual_archives: Optional[dict[str, tuple[bytes, bytes]]] = None,
    ) -> list[dict]:
        """Build parts with actual custom visual binary content.

        Args:
            visual_archives: mapping of GUID -> (package_json_bytes, pbiviz_json_bytes).
                If None, placeholder empty strings are used.
        """
        parts = self.build_pbir_parts()

        if visual_archives:
            for part in parts:
                path = part["path"]
                for guid, (pkg_bytes, res_bytes) in visual_archives.items():
                    if path == f"CustomVisuals/{guid}/package.json":
                        part["payload"] = base64.b64encode(pkg_bytes).decode()
                    elif path == f"CustomVisuals/{guid}/resources/{guid}.pbiviz.json":
                        part["payload"] = base64.b64encode(res_bytes).decode()

        return parts
