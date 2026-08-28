"""Donut composite and header-alignment utilities.

Provides:
- compute_donut_center(): derive center KPI overlay geometry from donut bounds
- DonutComposite: declarative donut + center KPI pairing
- HEADER_GEOMETRY: shared header/title layout constants
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Donut Composite Positioning
# ─────────────────────────────────────────────────────────────────────────────

# Power BI native donut layout constants (empirically derived from rendered output):
# - Title region: ~24px top (when title shown)
# - Legend at right: ~120px when external legend enabled
# - Plot area: remaining space, centred within its region
# - Internal donut padding: ~8px each side

# With legend to the right and title at top, the donut plot center is:
#   cx = (donut_width - legend_width) / 2
#   cy = title_height + (donut_height - title_height) / 2

# These constants MUST match the internal layout in
# custom-visuals/premiumDonut/src/visual.ts so the overlay lands exactly on the
# donut hole. See that file's update() layout block.
DONUT_TITLE_HEIGHT = 28  # titleHeight in the visual
DONUT_PADDING = 12  # padding in the visual
DONUT_LEGEND_FRACTION = 0.35  # legendWidth = min(width * fraction, cap)
DONUT_LEGEND_CAP = 140  # legendWidth cap in the visual


def compute_donut_center(
    donut_x: int,
    donut_y: int,
    donut_w: int,
    donut_h: int,
    *,
    overlay_w: int = 100,
    overlay_h: int = 44,
    has_title: bool = True,
    has_legend: bool = True,
) -> tuple[int, int, int, int]:
    """Compute the center KPI overlay position from donut container bounds.

    Returns (x, y, w, h) for the overlay visual, centred in the donut hole.

    The geometry mirrors the premiumDonut custom visual exactly:
        legendWidth  = min(w * 0.35, 140)   (when legend shown)
        chartArea    = w - legendWidth - 2 * padding
        chartCenterX = padding + chartArea / 2
        chartCenterY = titleHeight + (h - titleHeight) / 2

    Keeping this in lockstep with visual.ts guarantees the overlay lands on the
    actual donut hole at any size.
    """
    title_offset = DONUT_TITLE_HEIGHT if has_title else 0
    legend_width = min(donut_w * DONUT_LEGEND_FRACTION, DONUT_LEGEND_CAP) if has_legend else 0

    # Donut plot geometry (relative to the donut container), matching visual.ts
    chart_area = donut_w - legend_width - 2 * DONUT_PADDING
    center_x = donut_x + DONUT_PADDING + chart_area / 2
    center_y = donut_y + title_offset + (donut_h - title_offset) / 2

    # Overlay positioned so its center aligns with the donut hole center
    overlay_x = int(round(center_x - overlay_w / 2))
    overlay_y = int(round(center_y - overlay_h / 2))

    return (overlay_x, overlay_y, overlay_w, overlay_h)


@dataclass
class DonutComposite:
    """Declarative specification for a donut + center KPI pair.

    Callers specify only the donut bounds and center content.
    The overlay geometry is computed automatically.
    """

    # Donut container bounds
    donut_position: tuple[int, int, int, int]  # (x, y, w, h)

    # Center KPI configuration
    center_title: str  # Static title text (e.g., "876")
    center_subtitle: str = ""  # e.g., "Active Customers"
    center_binding: Optional[dict] = None  # {"entity": ..., "property": ..., "is_measure": True}

    # Sizing options
    overlay_w: int = 100
    overlay_h: int = 44
    has_title: bool = True
    has_legend: bool = True

    # Visual formatting
    title_color: str = "#ffffff"
    title_font_size: int = 18
    title_bold: bool = True

    @property
    def center_position(self) -> tuple[int, int, int, int]:
        """Compute the center overlay position from donut bounds."""
        x, y, w, h = self.donut_position
        return compute_donut_center(
            x, y, w, h,
            overlay_w=self.overlay_w,
            overlay_h=self.overlay_h,
            has_title=self.has_title,
            has_legend=self.has_legend,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Unified Header/Title Geometry
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HeaderGeometry:
    """Shared header/title geometry constants for all visual panels.

    Ensures consistent title placement across native and custom visuals.
    """

    # Title region
    title_top_inset: int = 6  # px from top of panel to title baseline
    title_left_inset: int = 10  # px from left edge of panel
    title_font_size: int = 12  # section title size
    title_font_weight: str = "semibold"
    title_color_token: str = "text_secondary"  # reference into DesignTokens

    # Subtitle
    subtitle_offset: int = 16  # px below title baseline
    subtitle_font_size: int = 8
    subtitle_color_token: str = "text_muted"

    # Plot spacing
    title_to_plot_spacing: int = 4  # px between title region bottom and plot area top

    # Consistency rules
    disable_native_title: bool = False  # When True, suppress PBI native title and use renderer-owned

    @property
    def title_region_height(self) -> int:
        """Total height consumed by title + spacing before plot area."""
        return self.title_top_inset + self.title_font_size + self.title_to_plot_spacing


# Shared singleton — all templates reference this
HEADER_GEOMETRY = HeaderGeometry()

# Templates that use the standard header system
TITLED_TEMPLATES = {
    "premium_trend",
    "premium_bar",
    "premium_column",
    "premium_donut",
    "premium_table",
    "premium_waterfall",
    "premium_gauge",
    "premium_insights",
}

# Templates with their own internal header grammar (exempt from unified header)
SELF_TITLED_TEMPLATES = {
    "premium_kpi",  # KPI cards have their own compact label grammar
    "donut_center_kpi",  # Overlay, no panel title needed
}



# ─────────────────────────────────────────────────────────────────────────────
# Convenience: VisualBinding-level composite for existing configs
# ─────────────────────────────────────────────────────────────────────────────

def make_donut_composite_bindings(
    donut_position: tuple[int, int, int, int],
    donut_title: str,
    donut_category,  # FieldRef
    donut_measure,  # FieldRef
    center_title: str,
    center_measure,  # FieldRef
    center_subtitle: str = "",
    *,
    overlay_w: int = 100,
    overlay_h: int = 44,
    has_title: bool = True,
    has_legend: bool = True,
    title_font_size: int = 14,
) -> tuple:
    """Create a self-centring donut VisualBinding (single-element tuple).

    The donut visual draws its own centre KPI (value = ``center_title``,
    label = ``center_subtitle``) inside the ring group, so the KPI is centred by
    construction — there is no separate overlay to align. Returns a one-tuple for
    backward compatibility with callers that unpack the result.

    ``center_measure`` is retained for signature compatibility but is unused.
    """
    from pbi_gen.renderer.templates.registry import VisualBinding

    donut_binding = VisualBinding(
        template_id="premium_donut",
        title=donut_title,
        data_bindings={
            "category": [donut_category],
            "values": [donut_measure],
        },
        position=donut_position,
        config_overrides={
            # Donut draws its own centred KPI using these caller-supplied values.
            "center_value": center_title,
            "center_label": center_subtitle,
        },
    )

    return (donut_binding,)
