"""Premium design language variants for Power BI dashboard rendering.

Defines three art-direction variants that share composition structure but differ
in colour, typography emphasis, and surface treatment.
"""

from __future__ import annotations

from dataclasses import dataclass

from pbi_gen.models.dashboard_spec import PresentationMode, ThemeSpec


@dataclass(frozen=True)
class DesignLanguageVariant:
    """A complete visual art-direction specification for dashboard rendering."""

    name: str
    id: str  # 'executive_light', 'executive_dark', 'corporate_editorial'

    # Page
    page_background: str  # hex
    content_background: str  # hex for visual surfaces

    # Typography
    heading_font: str
    body_font: str
    page_title_size: float
    page_subtitle_size: float
    kpi_value_size: float
    kpi_label_size: float
    visual_title_size: float
    section_label_size: float

    # Colours
    text_primary: str  # hex
    text_secondary: str  # hex
    text_muted: str  # hex
    accent_primary: str  # hex
    accent_secondary: str  # hex
    border_color: str  # hex
    divider_color: str  # hex
    kpi_value_color: str  # hex

    # Surfaces
    card_background: str  # hex
    card_border_width: int  # px, 0 for none
    card_border_radius: int  # px
    header_band_color: str  # hex, for page identity band
    header_text_color: str  # hex
    section_band_color: str  # hex, subtle section backgrounds

    # Data colours (5-6 restrained)
    data_palette: tuple[str, ...]
    positive_color: str
    negative_color: str
    warning_color: str


# ─────────────────────────────────────────────────────────────────────────────
# Variant Definitions
# ─────────────────────────────────────────────────────────────────────────────

EXECUTIVE_LIGHT = DesignLanguageVariant(
    name="Executive Light",
    id="executive_light",
    # Page
    page_background="#F5F6F8",
    content_background="#FFFFFF",
    # Typography
    heading_font="Segoe UI Semibold",
    body_font="Segoe UI",
    page_title_size=18,
    page_subtitle_size=10,
    kpi_value_size=26,
    kpi_label_size=9,
    visual_title_size=11,
    section_label_size=10,
    # Colours
    text_primary="#1A1A2E",
    text_secondary="#4A4A6A",
    text_muted="#8E8EA0",
    accent_primary="#1B3A5C",
    accent_secondary="#C8963E",
    border_color="#E8E8F0",
    divider_color="#D8D8E8",
    kpi_value_color="#1B3A5C",
    # Surfaces
    card_background="#FFFFFF",
    card_border_width=1,
    card_border_radius=4,
    header_band_color="#1B3A5C",
    header_text_color="#FFFFFF",
    section_band_color="#F0F1F5",
    # Data colours
    data_palette=("#1B3A5C", "#C8963E", "#4A7C8F", "#7B5EA7", "#5C8A4E"),
    positive_color="#2E7D32",
    negative_color="#C62828",
    warning_color="#F57C00",
)

EXECUTIVE_DARK = DesignLanguageVariant(
    name="Executive Dark",
    id="executive_dark",
    # Page
    page_background="#0F1923",
    content_background="#1A2736",
    # Typography
    heading_font="Segoe UI Semibold",
    body_font="Segoe UI",
    page_title_size=18,
    page_subtitle_size=10,
    kpi_value_size=28,
    kpi_label_size=9,
    visual_title_size=11,
    section_label_size=10,
    # Colours
    text_primary="#E8ECF0",
    text_secondary="#A0B0C0",
    text_muted="#607080",
    accent_primary="#4FC3F7",
    accent_secondary="#FFB74D",
    border_color="#2A3A4A",
    divider_color="#2A3A4A",
    kpi_value_color="#FFFFFF",
    # Surfaces
    card_background="#1E2D3D",
    card_border_width=1,
    card_border_radius=6,
    header_band_color="#0A1218",
    header_text_color="#E8ECF0",
    section_band_color="#152230",
    # Data colours
    data_palette=("#4FC3F7", "#FFB74D", "#81C784", "#CE93D8", "#FF8A65"),
    positive_color="#66BB6A",
    negative_color="#EF5350",
    warning_color="#FFA726",
)

CORPORATE_EDITORIAL = DesignLanguageVariant(
    name="Corporate Editorial",
    id="corporate_editorial",
    # Page
    page_background="#FAFAFA",
    content_background="#FFFFFF",
    # Typography
    heading_font="Segoe UI Semibold",
    body_font="Segoe UI Light",
    page_title_size=22,
    page_subtitle_size=11,
    kpi_value_size=30,
    kpi_label_size=8,
    visual_title_size=10,
    section_label_size=9,
    # Colours
    text_primary="#111111",
    text_secondary="#444444",
    text_muted="#888888",
    accent_primary="#0066CC",
    accent_secondary="#333333",
    border_color="#E0E0E0",
    divider_color="#CCCCCC",
    kpi_value_color="#111111",
    # Surfaces
    card_background="#FFFFFF",
    card_border_width=0,
    card_border_radius=0,
    header_band_color="#FFFFFF",
    header_text_color="#111111",
    section_band_color="#F5F5F5",
    # Data colours
    data_palette=("#0066CC", "#333333", "#666666", "#0099CC", "#003366"),
    positive_color="#006600",
    negative_color="#CC0000",
    warning_color="#CC6600",
)


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

_VARIANTS: dict[str, DesignLanguageVariant] = {
    v.id: v for v in (EXECUTIVE_LIGHT, EXECUTIVE_DARK, CORPORATE_EDITORIAL)
}

AVAILABLE_VARIANTS: list[str] = list(_VARIANTS.keys())


def get_variant(variant_id: str) -> DesignLanguageVariant:
    """Get a variant by ID.

    Raises:
        ValueError: If variant_id is not a recognised variant.
    """
    if variant_id not in _VARIANTS:
        raise ValueError(
            f"Unknown variant '{variant_id}'. "
            f"Available: {AVAILABLE_VARIANTS}"
        )
    return _VARIANTS[variant_id]


def select_variant_from_theme(theme: ThemeSpec) -> DesignLanguageVariant:
    """Select the appropriate variant based on a theme spec.

    Selection logic:
        - DARK presentation_mode -> executive_dark
        - style_family containing 'editorial' -> corporate_editorial
        - Otherwise -> executive_light (default)
    """
    if theme.presentation_mode == PresentationMode.DARK:
        return EXECUTIVE_DARK

    if "editorial" in theme.style_family.lower():
        return CORPORATE_EDITORIAL

    return EXECUTIVE_LIGHT
