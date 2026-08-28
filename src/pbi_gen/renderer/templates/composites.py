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

DONUT_TITLE_HEIGHT = 28  # PBI native title row height when title shown
DONUT_LEGEND_WIDTH = 120  # Approximate legend column width (right-positioned)
DONUT_PLOT_PADDING = 8  # Internal padding around donut plot


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

    The donut plot area is offset by:
    - title_height from the top (when title is shown)
    - legend_width subtracted from the right (when legend is right-positioned)

    The donut hole center is then the geometric center of the remaining plot region.
    """
    title_offset = DONUT_TITLE_HEIGHT if has_title else 0
    legend_offset = DONUT_LEGEND_WIDTH if has_legend else 0

    # Plot region within the donut container
    plot_x = donut_x + DONUT_PLOT_PADDING
    plot_y = donut_y + title_offset
    plot_w = donut_w - legend_offset - (2 * DONUT_PLOT_PADDING)
    plot_h = donut_h - title_offset - DONUT_PLOT_PADDING

    # Center of the plot region = center of the donut hole
    center_x = plot_x + plot_w // 2
    center_y = plot_y + plot_h // 2

    # Overlay positioned so its center aligns with the donut hole center
    overlay_x = center_x - overlay_w // 2
    overlay_y = center_y - overlay_h // 2

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
    """Create (donut_binding, center_binding) VisualBinding pair.

    For use in the older financial_config / customer_config style.
    Imports VisualBinding from registry to avoid circular imports.
    """
    from pbi_gen.renderer.templates.registry import VisualBinding

    center_pos = compute_donut_center(
        *donut_position,
        overlay_w=overlay_w,
        overlay_h=overlay_h,
        has_title=has_title,
        has_legend=has_legend,
    )

    donut_binding = VisualBinding(
        template_id="premium_donut",
        title=donut_title,
        data_bindings={
            "category": [donut_category],
            "values": [donut_measure],
        },
        position=donut_position,
        config_overrides={
            # Suppress the donut's own centre total; the overlay below supplies
            # the intended centre metric.
            "show_center_value": False,
        },
    )

    center_binding = VisualBinding(
        template_id="donut_center_kpi",
        title=center_title,
        data_bindings={"measure": [center_measure]},
        position=center_pos,
        config_overrides={
            "subtitle": center_subtitle,
            "show_background": False,
            "show_border": False,
            "title_bold": True,
            "title_font_size": title_font_size,
            "title_color": "#ffffff",
        },
    )

    return (donut_binding, center_binding)
