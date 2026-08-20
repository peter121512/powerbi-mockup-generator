"""Grid-to-canvas position translation for PBIP report layout.

Converts the logical 12-column grid positions in the DashboardSpec to
pixel coordinates on the Power BI canvas.
"""

from __future__ import annotations

from dataclasses import dataclass

from pbi_gen.models import PageLayout, VisualPosition


# ─────────────────────────────────────────────────────────────────────────────
# Layout constants
# ─────────────────────────────────────────────────────────────────────────────

# Page margin — inset from each edge of the canvas (px).
PAGE_MARGIN = 20

# Gutter — spacing between adjacent visuals (px).
GUTTER = 12

# Default height reserved for the slicer/filter row at the top (px).
DEFAULT_FILTER_ROW_HEIGHT = 56

# Legacy padding constant (kept for backward-compat but now unused internally).
DEFAULT_PADDING_PX = 8


@dataclass
class CanvasPosition:
    """Absolute pixel position on the Power BI canvas."""

    x: float
    y: float
    z: int
    width: float
    height: float
    tab_order: int = 0


def grid_to_canvas(
    position: VisualPosition,
    layout: PageLayout,
    *,
    z_index: int = 1000,
    tab_order: int = 0,
    padding: int = DEFAULT_PADDING_PX,
    page_margin: int = PAGE_MARGIN,
    gutter: int = GUTTER,
    filter_row_height: int = 0,
) -> CanvasPosition:
    """Translate a grid position to canvas pixel coordinates.

    The usable area is inset by *page_margin* on all sides, and optionally
    reduced at the top by *filter_row_height* (for a slicer row).  Gutters
    are inserted between columns/rows so visuals never touch each other.

    Args:
        position: Grid-based position (x, y, width, height in grid units).
        layout: Page layout defining canvas size and grid dimensions.
        z_index: Z-order for layering.
        tab_order: Tab navigation order.
        padding: (Legacy) Not used internally but kept for API compat.
        page_margin: Inset from each canvas edge in pixels.
        gutter: Space between adjacent visuals in pixels.
        filter_row_height: Pixel height reserved at the top for a filter row.
            When > 0, the grid content area begins below this row (plus a
            gutter separator).

    Returns:
        CanvasPosition with pixel values.
    """
    # Usable canvas area after margins
    usable_width = layout.width - 2 * page_margin
    usable_height = layout.height - 2 * page_margin

    # Reserve space for filter row if present
    content_top_offset = 0
    if filter_row_height > 0:
        # Filter row sits at the top inside the margins; add gutter below it
        content_top_offset = filter_row_height + gutter
        usable_height -= content_top_offset

    # Total gutter space consumed by gaps between cells
    total_col_gutters = (layout.grid_columns - 1) * gutter
    total_row_gutters = (layout.grid_rows - 1) * gutter

    # Per-cell dimensions (excluding gutters)
    cell_width = (usable_width - total_col_gutters) / layout.grid_columns
    cell_height = (usable_height - total_row_gutters) / layout.grid_rows

    # Position: margin + cells before this one + gutters between them
    x_px = page_margin + position.x * (cell_width + gutter)
    y_px = (
        page_margin
        + content_top_offset
        + position.y * (cell_height + gutter)
    )

    # Size: span cells + gutters that fall BETWEEN spanned cells
    width_px = position.width * cell_width + (position.width - 1) * gutter
    height_px = position.height * cell_height + (position.height - 1) * gutter

    # Clamp to non-negative and ensure we don't exceed canvas bounds
    width_px = max(width_px, 0)
    height_px = max(height_px, 0)

    # Safety clamp: don't exceed page bounds
    if x_px + width_px > layout.width - page_margin:
        width_px = layout.width - page_margin - x_px
    if y_px + height_px > layout.height - page_margin:
        height_px = layout.height - page_margin - y_px

    return CanvasPosition(
        x=round(x_px, 2),
        y=round(y_px, 2),
        z=z_index,
        width=round(width_px, 2),
        height=round(height_px, 2),
        tab_order=tab_order,
    )


def position_to_dict(pos: CanvasPosition) -> dict:
    """Convert a CanvasPosition to the PBIR position dict."""
    return {
        "x": pos.x,
        "y": pos.y,
        "z": pos.z,
        "width": pos.width,
        "height": pos.height,
        "tabOrder": pos.tab_order,
    }
