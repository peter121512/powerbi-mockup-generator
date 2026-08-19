"""Grid-to-canvas position translation for PBIP report layout.

Converts the logical 12-column grid positions in the DashboardSpec to
pixel coordinates on the Power BI canvas.
"""

from __future__ import annotations

from dataclasses import dataclass

from pbi_gen.models import PageLayout, VisualPosition


# Default padding between visuals in pixels.
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
) -> CanvasPosition:
    """Translate a grid position to canvas pixel coordinates.

    Args:
        position: Grid-based position (x, y, width, height in grid units).
        layout: Page layout defining canvas size and grid dimensions.
        z_index: Z-order for layering.
        tab_order: Tab navigation order.
        padding: Padding in pixels between visuals.

    Returns:
        CanvasPosition with pixel values.
    """
    cell_width = layout.width / layout.grid_columns
    cell_height = layout.height / layout.grid_rows

    x_px = position.x * cell_width + padding
    y_px = position.y * cell_height + padding
    width_px = position.width * cell_width - 2 * padding
    height_px = position.height * cell_height - 2 * padding

    # Clamp to non-negative
    width_px = max(width_px, 0)
    height_px = max(height_px, 0)

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
