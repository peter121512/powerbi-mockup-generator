"""Theme generation for PBIP projects.

Translates the DashboardSpec ThemeSpec into Power BI theme JSON format.
"""

from __future__ import annotations

from pbi_gen.models import ColourRole, PresentationMode, ThemeSpec


# ─────────────────────────────────────────────────────────────────────────────
# Default colour palettes per style family
# ─────────────────────────────────────────────────────────────────────────────

_STYLE_PALETTES: dict[str, list[str]] = {
    "corporate_restrained": ["#1A3A52", "#D4AF37", "#2D5F3F", "#8B2635", "#6B7280"],
    "modern_bold": ["#1E40AF", "#DC2626", "#059669", "#D97706", "#7C3AED"],
    "editorial": ["#111827", "#4B5563", "#0369A1", "#B91C1C", "#065F46"],
    "default": ["#1A3A52", "#D4AF37", "#2D5F3F", "#8B2635", "#6B7280"],
}

_MODE_DEFAULTS: dict[PresentationMode, dict[str, str]] = {
    PresentationMode.LIGHT: {
        "background": "#FFFFFF",
        "foreground": "#1A3A52",
        "tableAccent": "#1A3A52",
    },
    PresentationMode.DARK: {
        "background": "#1F2937",
        "foreground": "#F9FAFB",
        "tableAccent": "#60A5FA",
    },
    PresentationMode.HIGH_CONTRAST: {
        "background": "#000000",
        "foreground": "#FFFFFF",
        "tableAccent": "#FFFF00",
    },
}


def _resolve_data_colors(theme: ThemeSpec) -> list[str]:
    """Resolve data colours from the theme spec.

    Uses explicit hex values from colour_roles where provided,
    then fills from the style family palette.
    """
    explicit = [
        role.hex_value for role in theme.colour_roles if role.hex_value
    ]

    palette_key = theme.style_family or "default"
    palette = _STYLE_PALETTES.get(palette_key, _STYLE_PALETTES["default"])

    # Start with explicit colours, fill to 5 minimum from palette
    colors = list(explicit)
    for c in palette:
        if c not in colors:
            colors.append(c)
        if len(colors) >= 5:
            break

    # Ensure at least 5 colours
    while len(colors) < 5:
        colors.append(palette[len(colors) % len(palette)])

    return colors[:5]


def _resolve_text_classes(theme: ThemeSpec) -> dict:
    """Build text classes from typography spec.

    Uses the Power BI theme textClasses which control default typography:
    - callout: KPI/card large values
    - title: visual titles
    - header: table/axis headers
    - label: axis labels, legends, body text
    """
    heading = theme.typography.heading_font or "Segoe UI Semibold"
    body = theme.typography.body_font or "Segoe UI"
    base_size = theme.typography.base_size_pt or 10.0

    # Resolve primary colour for callout from theme
    primary_color = "#1B3A5C"  # default navy
    for role in theme.colour_roles:
        if role.role == "primary" and role.hex_value:
            primary_color = role.hex_value
            break

    return {
        "callout": {
            "fontFace": heading,
            "fontSize": round(base_size + 12),  # Large callout for KPIs
            "color": primary_color,
        },
        "title": {
            "fontFace": heading,
            "fontSize": round(base_size + 1),
            "color": "#212121",
        },
        "header": {
            "fontFace": heading,
            "fontSize": round(base_size),
            "color": "#212121",
        },
        "label": {
            "fontFace": body,
            "fontSize": round(base_size - 1),
            "color": "#605E5C",
        },
    }


def generate_theme(theme: ThemeSpec) -> dict:
    """Generate a Power BI theme JSON dict from a ThemeSpec.

    Args:
        theme: The theme specification from the dashboard spec.

    Returns:
        Dict suitable for writing as theme.json.
    """
    mode = theme.presentation_mode or PresentationMode.LIGHT
    mode_defaults = _MODE_DEFAULTS.get(mode, _MODE_DEFAULTS[PresentationMode.LIGHT])

    style_name = theme.style_family or "corporate_restrained"
    theme_name = f"CustomTheme_{style_name}"

    return {
        "name": theme_name,
        "dataColors": _resolve_data_colors(theme),
        "background": mode_defaults["background"],
        "foreground": mode_defaults["foreground"],
        "tableAccent": mode_defaults["tableAccent"],
        "textClasses": _resolve_text_classes(theme),
    }
