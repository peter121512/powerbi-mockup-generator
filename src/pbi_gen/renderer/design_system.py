"""Enterprise Design System — coherent visual tokens and policies for Power BI rendering.

Provides deterministic, theme-driven formatting decisions for all visual elements
in a Power BI report. Accepts a ThemeSpec and resolves colours, typography, spacing,
surface treatments, number formatting, and per-visual-family formatting policies.

This module is generic — no domain-specific (retail, healthcare, etc.) logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pbi_gen.models.dashboard_spec import (
    ColourRole,
    DensityPreference,
    PresentationMode,
    ThemeSpec,
    TypographySpec,
    VisualType,
)


# ─────────────────────────────────────────────────────────────────────────────
# Typography Tokens
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TypographyTokens:
    """Resolved font families and sizes (in pt) for every text role."""

    heading_font: str
    body_font: str
    page_title: float
    visual_title: float
    kpi_value: float
    kpi_label: float
    axis_label: float
    legend: float
    table_header: float
    table_body: float
    slicer_label: float

    @property
    def axis_label_size(self) -> float:
        """Alias for charts/tables that use the _size suffix."""
        return self.axis_label

    @property
    def visual_title_size(self) -> float:
        """Alias for formatters that use the _size suffix."""
        return self.visual_title

    @property
    def legend_size(self) -> float:
        """Alias for formatters that use the _size suffix."""
        return self.legend


# ─────────────────────────────────────────────────────────────────────────────
# Spacing Tokens
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SpacingTokens:
    """Absolute pixel spacing values for a 1280×720 canvas."""

    page_margin: int
    gutter: int
    card_padding: int
    title_margin: int
    filter_row_height: int


# ─────────────────────────────────────────────────────────────────────────────
# Surface Tokens
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SurfaceTokens:
    """Card/page surface visual treatment."""

    page_background: str  # hex colour
    card_background: str  # hex colour
    card_border_color: str  # hex colour
    card_border_width: int  # px
    card_corner_radius: int  # px
    card_shadow: bool


# ─────────────────────────────────────────────────────────────────────────────
# Colour Policy
# ─────────────────────────────────────────────────────────────────────────────


# Enterprise defaults
_DEFAULT_PRIMARY = "#1B3A5C"  # Navy / dark blue
_DEFAULT_ACCENT = "#C8963E"  # Gold
_DEFAULT_POSITIVE = "#2E7D32"  # Muted green
_DEFAULT_NEGATIVE = "#C62828"  # Muted red
_DEFAULT_NEUTRAL = "#757575"  # Medium grey

_DEFAULT_PALETTE_LIGHT = [
    "#1B3A5C",  # navy
    "#C8963E",  # gold
    "#4A7C8F",  # teal
    "#7B5EA7",  # muted purple
    "#D17B4A",  # burnt orange
    "#5C8A4E",  # olive green
]

_DEFAULT_PALETTE_DARK = [
    "#5B9BD5",  # lighter blue
    "#E8C76A",  # lighter gold
    "#6BBFCF",  # lighter teal
    "#A688C9",  # lighter purple
    "#E8A06A",  # lighter orange
    "#7DB86A",  # lighter green
]


@dataclass(frozen=True)
class ColourPolicy:
    """Resolved colour assignments derived from ThemeSpec colour_roles."""

    _primary: str
    _accent: str
    _positive: str
    _negative: str
    _neutral: str
    _palette: list[str]
    _text_primary: str
    _text_secondary: str

    @property
    def primary_series_color(self) -> str:
        return self._primary

    @property
    def accent_color(self) -> str:
        return self._accent

    @property
    def positive_color(self) -> str:
        return self._positive

    @property
    def negative_color(self) -> str:
        return self._negative

    @property
    def neutral_color(self) -> str:
        return self._neutral

    @property
    def categorical_palette(self) -> list[str]:
        """5–6 restrained colours for categorical series."""
        return list(self._palette)

    @property
    def text_primary(self) -> str:
        return self._text_primary

    @property
    def text_secondary(self) -> str:
        return self._text_secondary

    @property
    def grid_color(self) -> str:
        """Light grey for gridlines and subtle separators."""
        return "#E8E8E8"


# ─────────────────────────────────────────────────────────────────────────────
# Number Format Policy
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NumberFormatPolicy:
    """Deterministic number formatting for display values."""

    currency_symbol: str = "£"
    decimal_places_pct: int = 1
    thousand_separator: str = ","

    def format_currency_compact(self, value: float) -> str:
        """Format currency with compact notation for large numbers.

        Examples: £1.2M, £450K, £3.5B, £850
        """
        symbol = self.currency_symbol
        abs_value = abs(value)
        sign = "-" if value < 0 else ""

        if abs_value >= 1_000_000_000:
            return f"{sign}{symbol}{abs_value / 1_000_000_000:.1f}B"
        if abs_value >= 1_000_000:
            return f"{sign}{symbol}{abs_value / 1_000_000:.1f}M"
        if abs_value >= 1_000:
            return f"{sign}{symbol}{abs_value / 1_000:.1f}K"
        return f"{sign}{symbol}{abs_value:,.0f}"

    def format_percentage(self, value: float) -> str:
        """Format as percentage with configured decimal places.

        Input is assumed to be in ratio form (0.25 → 25.0%).
        """
        return f"{value * 100:.{self.decimal_places_pct}f}%"

    def format_integer(self, value: int | float) -> str:
        """Format integer with thousand separators."""
        return f"{int(value):,}".replace(",", self.thousand_separator)

    def get_display_units(self, max_value: float) -> tuple[float, str]:
        """Determine appropriate display units for an axis/label.

        Returns:
            Tuple of (divisor, suffix) e.g. (1_000_000, "M").
        """
        abs_max = abs(max_value)
        if abs_max >= 1_000_000_000:
            return 1_000_000_000, "B"
        if abs_max >= 1_000_000:
            return 1_000_000, "M"
        if abs_max >= 10_000:
            return 1_000, "K"
        return 1, ""


# ─────────────────────────────────────────────────────────────────────────────
# Visual Formatting Policy
# ─────────────────────────────────────────────────────────────────────────────


class VisualFamily(str, Enum):
    """Logical groupings of visual types for formatting policy."""

    CARD = "card"
    LINE = "line"
    BAR = "bar"
    DONUT = "donut"
    TABLE = "table"
    SLICER = "slicer"
    MAP = "map"
    SCATTER = "scatter"


@dataclass(frozen=True)
class VisualFormattingSpec:
    """Formatting directives for a visual family."""

    show_title: bool = True
    show_data_labels: bool = False
    show_legend: bool = False
    show_gridlines: bool = False
    show_axis_title: bool = False
    show_background: bool = True
    border_visible: bool = True
    data_label_font_size: float = 9.0
    use_series_colors: bool = True
    legend_position: str = "bottom"


# Mapping of visual families to their default formatting policies
_FAMILY_FORMATTING: dict[VisualFamily, VisualFormattingSpec] = {
    VisualFamily.CARD: VisualFormattingSpec(
        show_title=True,
        show_data_labels=True,
        show_legend=False,
        show_gridlines=False,
        show_axis_title=False,
        show_background=True,
        border_visible=True,
        data_label_font_size=28.0,
        use_series_colors=False,
    ),
    VisualFamily.LINE: VisualFormattingSpec(
        show_title=True,
        show_data_labels=False,
        show_legend=True,
        show_gridlines=True,
        show_axis_title=True,
        show_background=True,
        border_visible=True,
        data_label_font_size=9.0,
        use_series_colors=True,
        legend_position="bottom",
    ),
    VisualFamily.BAR: VisualFormattingSpec(
        show_title=True,
        show_data_labels=True,
        show_legend=False,
        show_gridlines=False,
        show_axis_title=False,
        show_background=True,
        border_visible=True,
        data_label_font_size=9.0,
        use_series_colors=True,
    ),
    VisualFamily.DONUT: VisualFormattingSpec(
        show_title=True,
        show_data_labels=True,
        show_legend=True,
        show_gridlines=False,
        show_axis_title=False,
        show_background=True,
        border_visible=True,
        data_label_font_size=9.0,
        use_series_colors=True,
        legend_position="right",
    ),
    VisualFamily.TABLE: VisualFormattingSpec(
        show_title=True,
        show_data_labels=False,
        show_legend=False,
        show_gridlines=True,
        show_axis_title=False,
        show_background=True,
        border_visible=True,
        data_label_font_size=9.0,
        use_series_colors=False,
    ),
    VisualFamily.SLICER: VisualFormattingSpec(
        show_title=True,
        show_data_labels=False,
        show_legend=False,
        show_gridlines=False,
        show_axis_title=False,
        show_background=False,
        border_visible=False,
        data_label_font_size=9.0,
        use_series_colors=False,
    ),
    VisualFamily.MAP: VisualFormattingSpec(
        show_title=True,
        show_data_labels=False,
        show_legend=True,
        show_gridlines=False,
        show_axis_title=False,
        show_background=True,
        border_visible=True,
        data_label_font_size=9.0,
        use_series_colors=True,
        legend_position="bottom",
    ),
    VisualFamily.SCATTER: VisualFormattingSpec(
        show_title=True,
        show_data_labels=False,
        show_legend=True,
        show_gridlines=True,
        show_axis_title=True,
        show_background=True,
        border_visible=True,
        data_label_font_size=9.0,
        use_series_colors=True,
        legend_position="bottom",
    ),
}

# Map VisualType → VisualFamily
_VISUAL_TYPE_TO_FAMILY: dict[str, VisualFamily] = {
    VisualType.CARD.value: VisualFamily.CARD,
    VisualType.KPI.value: VisualFamily.CARD,
    VisualType.MULTI_ROW_CARD.value: VisualFamily.CARD,
    VisualType.LINE_CHART.value: VisualFamily.LINE,
    VisualType.AREA_CHART.value: VisualFamily.LINE,
    VisualType.COMBO_CHART.value: VisualFamily.LINE,
    VisualType.BAR_CHART.value: VisualFamily.BAR,
    VisualType.CLUSTERED_BAR.value: VisualFamily.BAR,
    VisualType.STACKED_BAR.value: VisualFamily.BAR,
    VisualType.COLUMN_CHART.value: VisualFamily.BAR,
    VisualType.CLUSTERED_COLUMN.value: VisualFamily.BAR,
    VisualType.STACKED_COLUMN.value: VisualFamily.BAR,
    VisualType.WATERFALL.value: VisualFamily.BAR,
    VisualType.RIBBON.value: VisualFamily.BAR,
    VisualType.DONUT_CHART.value: VisualFamily.DONUT,
    VisualType.PIE_CHART.value: VisualFamily.DONUT,
    VisualType.FUNNEL.value: VisualFamily.DONUT,
    VisualType.TREEMAP.value: VisualFamily.DONUT,
    VisualType.TABLE.value: VisualFamily.TABLE,
    VisualType.MATRIX.value: VisualFamily.TABLE,
    VisualType.SLICER.value: VisualFamily.SLICER,
    VisualType.MAP.value: VisualFamily.MAP,
    VisualType.FILLED_MAP.value: VisualFamily.MAP,
    VisualType.SHAPE_MAP.value: VisualFamily.MAP,
    VisualType.SCATTER.value: VisualFamily.SCATTER,
    VisualType.GAUGE.value: VisualFamily.CARD,
}


class VisualFormattingPolicy:
    """Resolves formatting policies per visual type."""

    def get_family(self, visual_type: VisualType | str) -> VisualFamily:
        """Determine the formatting family for a visual type."""
        vt = visual_type.value if isinstance(visual_type, VisualType) else visual_type
        return _VISUAL_TYPE_TO_FAMILY.get(vt, VisualFamily.CARD)

    def get_formatting(self, visual_type: VisualType | str) -> VisualFormattingSpec:
        """Get the formatting spec for a visual type."""
        family = self.get_family(visual_type)
        return _FAMILY_FORMATTING[family]


# ─────────────────────────────────────────────────────────────────────────────
# Enterprise Design System (top-level orchestrator)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class EnterpriseDesignSystem:
    """Coherent visual design system derived from a ThemeSpec.

    Provides all tokens and policies needed to render a Power BI report with
    consistent, enterprise-quality visual treatment.

    Usage:
        ds = EnterpriseDesignSystem.from_theme(spec.theme)
        colour = ds.colours.primary_series_color
        font_size = ds.typography.kpi_value
    """

    typography: TypographyTokens
    spacing: SpacingTokens
    surfaces: SurfaceTokens
    colours: ColourPolicy
    numbers: NumberFormatPolicy
    formatting: VisualFormattingPolicy

    # ─────────────────────────────────────────────────────────────────────────
    # Factory
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def from_theme(cls, theme: ThemeSpec) -> "EnterpriseDesignSystem":
        """Build a complete design system from a ThemeSpec."""
        typography = _resolve_typography(theme.typography, theme.density)
        spacing = _resolve_spacing(theme.density)
        surfaces = _resolve_surfaces(theme.presentation_mode, theme.card_style)
        colours = _resolve_colours(theme.colour_roles, theme.presentation_mode)
        numbers = NumberFormatPolicy()
        formatting = VisualFormattingPolicy()

        return cls(
            typography=typography,
            spacing=spacing,
            surfaces=surfaces,
            colours=colours,
            numbers=numbers,
            formatting=formatting,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Resolution helpers (private)
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_typography(
    typo: TypographySpec, density: DensityPreference
) -> TypographyTokens:
    """Resolve typography tokens from spec preferences."""
    heading_font = typo.heading_font or "Segoe UI Semibold"
    body_font = typo.body_font or "Segoe UI"
    base = typo.base_size_pt if typo.base_size_pt > 0 else 10.0

    # Scale factors relative to base size, adjusted by density
    density_scale = {
        DensityPreference.COMPACT: 0.9,
        DensityPreference.COMFORTABLE: 1.0,
        DensityPreference.SPACIOUS: 1.1,
    }.get(density, 1.0)

    return TypographyTokens(
        heading_font=heading_font,
        body_font=body_font,
        page_title=round(base * 1.8 * density_scale, 1),
        visual_title=round(base * 1.1 * density_scale, 1),
        kpi_value=round(base * 2.8 * density_scale, 1),
        kpi_label=round(base * 0.9 * density_scale, 1),
        axis_label=round(base * 0.85 * density_scale, 1),
        legend=round(base * 0.85 * density_scale, 1),
        table_header=round(base * 0.95 * density_scale, 1),
        table_body=round(base * 0.9 * density_scale, 1),
        slicer_label=round(base * 0.9 * density_scale, 1),
    )


def _resolve_spacing(density: DensityPreference) -> SpacingTokens:
    """Resolve spacing tokens based on density preference.

    Values are absolute pixels for a 1280×720 canvas.
    """
    if density == DensityPreference.COMPACT:
        return SpacingTokens(
            page_margin=16,
            gutter=8,
            card_padding=10,
            title_margin=4,
            filter_row_height=36,
        )
    if density == DensityPreference.SPACIOUS:
        return SpacingTokens(
            page_margin=32,
            gutter=16,
            card_padding=20,
            title_margin=12,
            filter_row_height=48,
        )
    # COMFORTABLE (default)
    return SpacingTokens(
        page_margin=24,
        gutter=12,
        card_padding=14,
        title_margin=8,
        filter_row_height=40,
    )


def _resolve_surfaces(
    mode: PresentationMode, card_style: str
) -> SurfaceTokens:
    """Resolve surface tokens from presentation mode and card style hints."""
    is_dark = mode == PresentationMode.DARK

    # Defaults by mode
    if is_dark:
        page_bg = "#1E1E1E"
        card_bg = "#2D2D2D"
        border_color = "#404040"
        text_default_shadow = False
    else:
        page_bg = "#F5F5F5"
        card_bg = "#FFFFFF"
        border_color = "#E0E0E0"
        text_default_shadow = True

    # Parse card_style hints
    card_style_lower = card_style.lower() if card_style else ""
    if "shadow" in card_style_lower or "elevated" in card_style_lower:
        shadow = True
        border_width = 0
        corner_radius = 8
    elif "flat" in card_style_lower or "border" in card_style_lower:
        shadow = False
        border_width = 1
        corner_radius = 4
    elif "sharp" in card_style_lower:
        shadow = False
        border_width = 1
        corner_radius = 0
    else:
        # Default: subtle border with gentle radius
        shadow = text_default_shadow
        border_width = 1
        corner_radius = 6

    return SurfaceTokens(
        page_background=page_bg,
        card_background=card_bg,
        card_border_color=border_color,
        card_border_width=border_width,
        card_corner_radius=corner_radius,
        card_shadow=shadow,
    )


def _resolve_colours(
    colour_roles: list[ColourRole], mode: PresentationMode
) -> ColourPolicy:
    """Resolve colours from ThemeSpec roles or fall back to enterprise defaults."""
    is_dark = mode == PresentationMode.DARK

    # Build lookup from supplied roles
    role_map: dict[str, str] = {}
    for cr in colour_roles:
        if cr.hex_value:
            role_map[cr.role.lower()] = cr.hex_value

    # Resolve each semantic colour
    primary = role_map.get("primary", _DEFAULT_PRIMARY)
    accent = role_map.get("accent", _DEFAULT_ACCENT)
    positive = role_map.get("positive", _DEFAULT_POSITIVE)
    negative = role_map.get("negative", _DEFAULT_NEGATIVE)
    neutral = role_map.get("neutral", _DEFAULT_NEUTRAL)

    # Palette: use supplied roles or defaults
    if is_dark:
        palette = _DEFAULT_PALETTE_DARK
    else:
        palette = _DEFAULT_PALETTE_LIGHT

    # Override palette[0] and palette[1] with primary/accent if custom
    palette = list(palette)  # copy
    if "primary" in role_map:
        palette[0] = primary
    if "accent" in role_map:
        palette[1] = accent

    # Text colours
    if is_dark:
        text_primary = role_map.get("text_primary", "#E0E0E0")
        text_secondary = role_map.get("text_secondary", "#A0A0A0")
    else:
        text_primary = role_map.get("text_primary", "#212121")
        text_secondary = role_map.get("text_secondary", "#616161")

    return ColourPolicy(
        _primary=primary,
        _accent=accent,
        _positive=positive,
        _negative=negative,
        _neutral=neutral,
        _palette=palette,
        _text_primary=text_primary,
        _text_secondary=text_secondary,
    )
