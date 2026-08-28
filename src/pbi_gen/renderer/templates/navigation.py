"""Central navigation system for multi-page reports (Stage 12B).

Provides:
- ``NavTokens``: one shared, configurable navigation design language
  (widths, spacing, icon size/stroke, active/inactive styling). All pages
  consume this so appearance is changed in one place, not per config.
- Professional **outline SVG icons** (no emoji) rendered as base64 data URIs
  for Power BI ``image`` visuals — one consistent icon set.
- ``NavItem`` and ``build_navigation`` helpers that emit clickable Power BI
  page-navigation actions (``visualLink`` type ``PageNavigation``) targeting
  deterministic page names generated from the report spec.

The icon glyphs communicate: Overview/dashboard, Financial/chart, Customers/
users, Products/package — kept visually consistent as one stroked-outline set.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Navigation design tokens (single source of truth for nav appearance)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NavTokens:
    """Shared navigation design tokens. Change appearance here, not per page."""

    nav_width: int = 150
    top_offset: int = 96          # y of the first nav item (below the app title)
    item_height: int = 40
    item_gap: int = 8
    icon_size: int = 18
    icon_stroke: float = 1.6
    left_padding: int = 16        # left inset of icon within the rail
    icon_label_gap: int = 12      # gap between icon box and label
    label_font_size: int = 11

    # Colours (kept compatible with the dark navy shell / DesignTokens)
    nav_background: str = "#111827"
    active_background: str = "#243247"
    active_accent: str = "#4aa3ff"    # left indicator + active icon/label
    inactive_color: str = "#aab6c8"   # faded (but legible) inactive icon + label
    active_label_color: str = "#ffffff"
    indicator_width: int = 3

    @property
    def item_pitch(self) -> int:
        """Vertical distance between consecutive nav item origins."""
        return self.item_height + self.item_gap


# Shared singleton — all pages reference this unless explicitly overridden.
NAV_TOKENS = NavTokens()


# ─────────────────────────────────────────────────────────────────────────────
# Outline SVG icon set (no emoji). Stroked, 24x24 viewBox, consistent weight.
# ─────────────────────────────────────────────────────────────────────────────

# Each entry is the inner SVG body; stroke colour/width injected at render time.
_ICON_PATHS: dict[str, str] = {
    # Overview / dashboard — 2x2 panel grid
    "overview": (
        '<rect x="3" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'
    ),
    # Financial — bar chart with baseline
    "financial": (
        '<line x1="3" y1="21" x2="21" y2="21"/>'
        '<rect x="5" y="12" width="3.5" height="7" rx="0.8"/>'
        '<rect x="10.5" y="8" width="3.5" height="11" rx="0.8"/>'
        '<rect x="16" y="4" width="3.5" height="15" rx="0.8"/>'
    ),
    # Customers — two users
    "customers": (
        '<circle cx="9" cy="8" r="3.2"/>'
        '<path d="M3.5 20c0-3.2 2.6-5.3 5.5-5.3s5.5 2.1 5.5 5.3"/>'
        '<path d="M16 5.2a3.2 3.2 0 0 1 0 6"/>'
        '<path d="M17.2 14.9c2 .6 3.3 2.4 3.3 5.1"/>'
    ),
    # Products — package / box
    "products": (
        '<path d="M12 2.8 20.5 7v10L12 21.2 3.5 17V7z"/>'
        '<path d="M3.5 7 12 11.4 20.5 7"/>'
        '<line x1="12" y1="11.4" x2="12" y2="21.2"/>'
    ),
}

# Ordered logical icon set — keeps the four dashboards consistent.
ICON_KEYS = ("overview", "financial", "customers", "products")


def _svg_icon(icon_key: str, color: str, stroke: float, size: int) -> str:
    """Return a complete standalone SVG string for an outline icon."""
    body = _ICON_PATHS.get(icon_key, _ICON_PATHS["overview"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        f'{body}</svg>'
    )


def icon_data_uri(icon_key: str, color: str, *, stroke: float = 1.6, size: int = 18) -> str:
    """Return a base64 ``data:image/svg+xml`` URI for the given outline icon.

    Deployable zero-touch (inline in the report definition) — no external
    resources, no emoji.
    """
    svg = _svg_icon(icon_key, color, stroke, size)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def has_emoji(text: str) -> bool:
    """True if the string contains emoji / pictographic characters.

    Used by tests to guarantee the nav uses professional iconography only.
    """
    for ch in text:
        cp = ord(ch)
        if (
            0x1F300 <= cp <= 0x1FAFF  # symbols & pictographs, emoji
            or 0x2600 <= cp <= 0x27BF  # misc symbols + dingbats
            or 0x1F000 <= cp <= 0x1F0FF
            or cp in (0x2B50, 0x2B55, 0xFE0F)  # star, circle, variation selector
        ):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Navigation item model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class NavItem:
    """One navigation entry linking a label + icon to a target page."""

    label: str
    target_page: str            # deterministic page name (navigationSection target)
    icon_key: str               # key into the outline icon set
    tooltip: str = ""

    def __post_init__(self) -> None:
        if self.icon_key not in _ICON_PATHS:
            raise ValueError(
                f"Unknown nav icon_key '{self.icon_key}'. "
                f"Valid: {sorted(_ICON_PATHS)}"
            )
        if has_emoji(self.label):
            raise ValueError(f"Nav label must not contain emoji: {self.label!r}")


def default_nav_items() -> list[NavItem]:
    """The canonical four-dashboard navigation (labels, icons, target pages)."""
    return [
        NavItem("Overview", "executive_overview", "overview"),
        NavItem("Financial", "financial_performance", "financial"),
        NavItem("Customers", "customer_performance", "customers"),
        NavItem("Products", "product_performance", "products"),
    ]
