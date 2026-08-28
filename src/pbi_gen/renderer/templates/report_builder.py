"""Multi-page report builder with functional navigation (Stage 12B).

Produces a single Power BI report (PBIR) containing an arbitrary ordered list
of pages, a shared navigation rail with **clickable page-navigation actions**
and professional outline SVG icons, and custom-visual packages included once
per report.

Key contracts:
- ``ReportPage``: one page = a ``PageShell`` + its ``VisualBinding`` list.
- ``ReportSpec``: report_name, semantic model binding, ordered pages,
  default_page, navigation items, design tokens, nav tokens.
- ``build_report_spec_parts``: deterministic PBIR parts for the whole report.

Deterministic page IDs: each page's ``page_name`` is used verbatim as the PBIR
page id and as the navigation target, so nav actions never point at stale IDs.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .builder import (
    _build_slicer_visual,
    _build_title_visual,
    _build_visual_json,
    _is_custom_visual_type,
    _literal,
    _solid_color_expr,
    _vis_container,
)
from .navigation import NAV_TOKENS, NavItem, NavTokens, icon_data_uri
from .registry import DesignTokens, FieldRef, PageShell, TemplateRegistry, VisualBinding


# ─────────────────────────────────────────────────────────────────────────────
# Report spec models
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ReportPage:
    """One page of a multi-page report."""

    shell: PageShell
    bindings: list[VisualBinding]

    @property
    def page_name(self) -> str:
        """Deterministic PBIR page id — the shell page_name verbatim."""
        return self.shell.page_name


@dataclass
class ReportSpec:
    """A complete multi-page report definition."""

    report_name: str
    semantic_model_id: str
    semantic_model_name: str
    pages: list[ReportPage]
    default_page: Optional[str] = None
    nav_items: Optional[list[NavItem]] = None
    tokens: DesignTokens = field(default_factory=DesignTokens)
    nav_tokens: NavTokens = field(default_factory=lambda: NAV_TOKENS)
    theme_name: str = "ExecutiveDark"

    def __post_init__(self) -> None:
        if not self.pages:
            raise ValueError("ReportSpec requires at least one page")
        names = [p.page_name for p in self.pages]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate page names in report: {names}")
        if self.default_page is None:
            self.default_page = self.pages[0].page_name
        elif self.default_page not in names:
            raise ValueError(
                f"default_page '{self.default_page}' is not one of {names}"
            )
        # Validate nav targets resolve to real pages.
        for item in self.nav_items or []:
            if item.target_page not in names:
                raise ValueError(
                    f"Nav item '{item.label}' targets unknown page "
                    f"'{item.target_page}'. Pages: {names}"
                )

    @property
    def page_names(self) -> list[str]:
        return [p.page_name for p in self.pages]

    @property
    def _connection_string(self) -> str:
        catalog = self.semantic_model_name or "UnspecifiedModel"
        sm_id = self.semantic_model_id or "00000000-0000-0000-0000-000000000000"
        return (
            f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;"
            f"initial catalog={catalog};"
            f"integrated security=ClaimsToken;"
            f"semanticmodelid={sm_id}"
        )

    def custom_visual_guids(self, registry: TemplateRegistry) -> list[str]:
        """All distinct custom-visual GUIDs across every page (once each)."""
        guids: set[str] = set()
        for page in self.pages:
            for b in page.bindings:
                template = registry.get(b.template_id)
                if _is_custom_visual_type(template.visual_type):
                    guids.add(template.visual_type)
        return sorted(guids)


# ─────────────────────────────────────────────────────────────────────────────
# Functional navigation rail
# ─────────────────────────────────────────────────────────────────────────────


def _nav_background(nav: NavTokens, height: int) -> tuple[str, dict]:
    bg = _vis_container("nav_rail", 0, 0, nav.nav_width, height, 1)
    bg["visual"] = {
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
                "color": _solid_color_expr(nav.nav_background),
                "transparency": _literal("0D"),
            }}],
            "border": [{"properties": {"show": _literal("false")}}],
        },
        "drillFilterOtherVisuals": False,
    }
    return ("nav_rail", bg)


def _nav_active_pill(nav: NavTokens, active_idx: int) -> tuple[str, dict]:
    """Subtle rounded active-row background."""
    y = nav.top_offset + active_idx * nav.item_pitch
    pill = _vis_container("nav_active_pill", 6, y, nav.nav_width - 12, nav.item_height, 2)
    pill["visual"] = {
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
                "color": _solid_color_expr(nav.active_background),
                "transparency": _literal("0D"),
            }}],
            "border": [{"properties": {"show": _literal("false")}}],
        },
        "drillFilterOtherVisuals": False,
    }
    return ("nav_active_pill", pill)


def _nav_active_indicator(nav: NavTokens, active_idx: int) -> tuple[str, dict]:
    """Left accent bar marking the active page."""
    y = nav.top_offset + active_idx * nav.item_pitch
    ind = _vis_container("nav_indicator", 0, y, nav.indicator_width, nav.item_height, 3)
    ind["visual"] = {
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
                "color": _solid_color_expr(nav.active_accent),
                "transparency": _literal("0D"),
            }}],
            "border": [{"properties": {"show": _literal("false")}}],
        },
        "drillFilterOtherVisuals": False,
    }
    return ("nav_indicator", ind)


def _nav_icon(nav: NavTokens, item: NavItem, idx: int, is_active: bool) -> tuple[str, dict]:
    """An outline SVG icon rendered as an image visual."""
    color = nav.active_accent if is_active else nav.inactive_color
    data_uri = icon_data_uri(item.icon_key, color, stroke=nav.icon_stroke, size=nav.icon_size)
    box = nav.item_height
    y = nav.top_offset + idx * nav.item_pitch
    # Center the icon vertically within the row, inset from the left.
    icon_y = y + (box - nav.icon_size) // 2
    name = f"nav_icon_{idx}"
    vis = _vis_container(name, nav.left_padding, icon_y, nav.icon_size, nav.icon_size, 4 + idx * 2)
    vis["visual"] = {
        "visualType": "image",
        "objects": {
            "general": [{"properties": {
                "imageUrl": _literal(f"'{data_uri}'"),
            }}],
            "imageScaling": [{"properties": {
                "imageScalingType": _literal("'Fit'"),
            }}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {"show": _literal("false")}}],
            "background": [{"properties": {"show": _literal("false")}}],
            "border": [{"properties": {"show": _literal("false")}}],
            # The icon itself is decorative; the clickable target is the label
            # button which spans the whole row (see _nav_button).
        },
        "drillFilterOtherVisuals": False,
    }
    return (name, vis)


def _nav_label(
    nav: NavTokens, item: NavItem, idx: int, is_active: bool, dummy_field: FieldRef,
) -> tuple[str, dict]:
    """The item label, rendered via a cardVisual container title — the proven
    text-rendering path in this codebase."""
    from .builder import _build_projection

    color = nav.active_label_color if is_active else nav.inactive_color
    y = nav.top_offset + idx * nav.item_pitch
    text_x = nav.left_padding + nav.icon_size + nav.icon_label_gap
    label_w = nav.nav_width - text_x - 4
    name = f"nav_label_{idx}"
    label_y = y + (nav.item_height - 20) // 2
    vis = _vis_container(name, text_x, label_y, label_w, 20, 5 + idx * 3)
    vis["visual"] = {
        "visualType": "cardVisual",
        "query": {"queryState": {"Values": {"projections": [_build_projection(dummy_field)]}}},
        "visualContainerObjects": {
            "title": [{"properties": {
                "show": _literal("true"),
                "text": _literal(f"'{item.label}'"),
                "fontColor": _solid_color_expr(color),
                "fontSize": _literal(f"{nav.label_font_size}D"),
                "bold": _literal("true" if is_active else "false"),
                "alignment": _literal("'left'"),
            }}],
            "background": [{"properties": {"show": _literal("false")}}],
            "border": [{"properties": {"show": _literal("false")}}],
        },
        "drillFilterOtherVisuals": False,
    }
    return (name, vis)


def _nav_button(nav: NavTokens, item: NavItem, idx: int, is_active: bool) -> tuple[str, dict]:
    """A transparent full-row click layer carrying the page-navigation action.

    Rendered on top so the whole row is clickable; the visible icon + label are
    separate visuals underneath.
    """
    y = nav.top_offset + idx * nav.item_pitch
    name = f"nav_item_{idx}"
    vis = _vis_container(name, 0, y, nav.nav_width, nav.item_height, 7 + idx * 3)
    vis["visual"] = {
        "visualType": "actionButton",
        "objects": {
            "text": [{"properties": {"show": _literal("false")}}],
            "fill": [{"properties": {
                "show": _literal("true"),
                "fillColor": _solid_color_expr(nav.nav_background),
                "transparency": _literal("100D"),  # fully transparent click layer
            }}],
            "outline": [{"properties": {"show": _literal("false")}}],
            "icon": [{"properties": {"show": _literal("false")}}],
        },
        "visualContainerObjects": {
            "visualHeader": [{"properties": {"show": _literal("false")}}],
            # Functional page-navigation action — targets a deterministic page.
            "visualLink": [{"properties": {
                "show": _literal("true"),
                "type": _literal("'PageNavigation'"),
                "navigationSection": _literal(f"'{item.target_page}'"),
            }}],
        },
        "drillFilterOtherVisuals": False,
    }
    return (name, vis)


def build_nav_visuals(
    nav_items: list[NavItem],
    active_page: str,
    nav: NavTokens,
    page_height: int,
    dummy_field: Optional[FieldRef] = None,
) -> list[tuple[str, dict]]:
    """Build the full navigation rail for one page: background, active pill +
    indicator, and per-item icon + label + clickable action layer."""
    if dummy_field is None:
        dummy_field = FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)
    parts: list[tuple[str, dict]] = [_nav_background(nav, page_height)]

    active_idx = next(
        (i for i, it in enumerate(nav_items) if it.target_page == active_page),
        0,
    )
    parts.append(_nav_active_pill(nav, active_idx))
    parts.append(_nav_active_indicator(nav, active_idx))

    for idx, item in enumerate(nav_items):
        is_active = item.target_page == active_page
        parts.append(_nav_icon(nav, item, idx, is_active))
        parts.append(_nav_label(nav, item, idx, is_active, dummy_field))
        parts.append(_nav_button(nav, item, idx, is_active))

    return parts


# ─────────────────────────────────────────────────────────────────────────────
# Multi-page report parts assembly
# ─────────────────────────────────────────────────────────────────────────────


def _get_dummy_field(spec: ReportSpec) -> FieldRef:
    for page in spec.pages:
        for b in page.bindings:
            for fields in b.data_bindings.values():
                for f in fields:
                    if f.is_measure:
                        return f
    return FieldRef(entity="Measure", property="Value", is_measure=True)


def build_report_spec_parts(
    spec: ReportSpec,
    registry: Optional[TemplateRegistry] = None,
    *,
    visual_archives: Optional[dict[str, tuple[bytes, bytes]]] = None,
) -> list[dict]:
    """Generate the full PBIR parts list for a multi-page report.

    Each page gets: its content visuals, the shared functional nav rail, the
    page title and slicers. Custom visuals are packaged exactly once for the
    whole report.
    """
    registry = registry or TemplateRegistry.default()
    tokens = spec.tokens
    nav = spec.nav_tokens
    nav_items = spec.nav_items or []
    parts: list[dict] = []

    def _add_json(path: str, obj) -> None:
        payload = base64.b64encode(
            json.dumps(obj, ensure_ascii=False).encode()
        ).decode()
        parts.append({"path": path, "payload": payload, "payloadType": "InlineBase64"})

    # ── .platform ──
    _add_json(".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": spec.report_name},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    })

    # ── definition.pbir (byConnection to the shared semantic model) ──
    _add_json("definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byConnection": {"connectionString": spec._connection_string}},
    })

    # ── version ──
    _add_json("definition/version.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })

    # ── report.json (custom visuals listed once per report) ──
    custom_guids = spec.custom_visual_guids(registry)
    resource_packages: list[dict] = [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": "RegisteredResources", "type": "RegisteredResources", "items": [
            {"name": spec.theme_name, "type": "CustomTheme", "path": f"{spec.theme_name}.json"}
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
            "customTheme": {"name": spec.theme_name, "reportVersionAtImport": "5.61", "type": "RegisteredResources"},
        },
        "layoutOptimization": "None",
        "resourcePackages": resource_packages,
    })

    # ── theme ──
    theme_json = tokens.to_pbi_theme(spec.theme_name)
    parts.append({
        "path": f"StaticResources/RegisteredResources/{spec.theme_name}.json",
        "payload": base64.b64encode(json.dumps(theme_json).encode("utf-8")).decode(),
        "payloadType": "InlineBase64",
    })

    # ── pages metadata (ordered page list + default active) ──
    _add_json("definition/pages/pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": spec.page_names,
        "activePageName": spec.default_page,
    })

    dummy_field = _get_dummy_field(spec)

    # ── each page ──
    for page in spec.pages:
        page_name = page.page_name
        shell = page.shell

        _add_json(f"definition/pages/{page_name}/page.json", {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
            "name": page_name,
            "displayName": shell.display_name,
            "displayOption": "FitToPage",
            "height": shell.height,
            "width": shell.width,
            "objects": {
                "background": [{"properties": {
                    "color": _solid_color_expr(tokens.canvas),
                    "transparency": _literal("0D"),
                }}],
            },
        })

        def _add_visual(vis_name: str, vis_json: dict) -> None:
            _add_json(
                f"definition/pages/{page_name}/visuals/{vis_name}/visual.json",
                vis_json,
            )

        # Functional navigation rail (icons + clickable page-nav buttons)
        for vis_name, vis_json in build_nav_visuals(
            nav_items, active_page=shell.active_nav, nav=nav,
            page_height=shell.height, dummy_field=dummy_field,
        ):
            _add_visual(vis_name, vis_json)

        # Page title
        title_name, title_json = _build_title_visual(
            shell, tokens, dummy_field, nav_width=nav.nav_width,
        )
        _add_visual(title_name, title_json)

        # Slicers
        for idx, slicer_field in enumerate(shell.slicers):
            slicer_name, slicer_json = _build_slicer_visual(slicer_field, tokens, idx)
            _add_visual(slicer_name, slicer_json)

        # Content visuals
        for z_idx, binding in enumerate(page.bindings, start=20):
            vis_json = _build_visual_json(binding, tokens, registry, z_idx)
            _add_visual(vis_json["name"], vis_json)

    # ── custom-visual packages (once each) ──
    for guid in custom_guids:
        pkg_payload = ""
        res_payload = ""
        if visual_archives and guid in visual_archives:
            pkg_bytes, res_bytes = visual_archives[guid]
            pkg_payload = base64.b64encode(pkg_bytes).decode()
            res_payload = base64.b64encode(res_bytes).decode()
        parts.append({
            "path": f"CustomVisuals/{guid}/package.json",
            "payload": pkg_payload,
            "payloadType": "InlineBase64",
        })
        parts.append({
            "path": f"CustomVisuals/{guid}/resources/{guid}.pbiviz.json",
            "payload": res_payload,
            "payloadType": "InlineBase64",
        })

    return parts
