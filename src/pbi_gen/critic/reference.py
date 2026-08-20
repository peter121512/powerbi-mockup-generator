"""Visual reference image generation using OpenAI image models."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Optional

from pbi_gen.critic.models import VisualReferenceResult
from pbi_gen.models import DashboardSpec, PageSpec

# Default model — configurable
DEFAULT_IMAGE_MODEL = "gpt-image-2"


def _build_reference_prompt(
    requirement: str,
    spec: DashboardSpec,
    page: PageSpec,
) -> str:
    """Build a disciplined prompt for the image generation model.

    Constructs from structured spec information rather than vague requests.
    """
    # Gather KPIs/measures for this page
    visual_descriptions = []
    for v in page.visuals:
        fields = []
        for f in (v.value_fields or []):
            fields.append(f.measure or f.column or "?")
        for f in (v.category_fields or []):
            fields.append(f.column or "?")
        vtype = v.visual_type.value if v.visual_type else "unknown"
        visual_descriptions.append(f"- {v.title or v.id}: {vtype} showing {', '.join(fields)}")

    visuals_text = "\n".join(visual_descriptions) if visual_descriptions else "- General KPI cards and charts"

    # Theme context
    theme = spec.theme
    palette_info = ""
    if theme and theme.colour_roles:
        colours = [f"{cr.role}: {cr.hex_value}" for cr in theme.colour_roles[:5]]
        palette_info = ", ".join(colours)

    prompt = f"""Create a high-fidelity static mockup image of a premium enterprise Power BI dashboard page.

PAGE: {page.title}
ROLE: {page.role.value if page.role else 'executive overview'}
AUDIENCE: CEO/CFO board-level executives
BUSINESS CONTEXT: {spec.intent.business_purpose}
REQUIREMENT: {requirement}

ANALYTICS ON THIS PAGE:
{visuals_text}

LAYOUT: {page.layout.width}x{page.layout.height}px canvas, {page.layout.grid_columns} columns, {page.layout.grid_rows} rows

COLOUR PALETTE: {palette_info or 'Corporate navy/dark blue primary, gold accent, white background'}

DESIGN REQUIREMENTS:
- Executive-grade quality suitable for boardroom presentation
- Clear KPI hierarchy with headline metrics prominent at top
- Cards with large numeric values, clear labels, and trend indicators
- Charts with proper axes, legends, and readable labels
- Restrained professional colour use — not flashy or consumer-app-like
- Generous but efficient whitespace
- Consistent card geometry and alignment on a grid
- Clean typography using Segoe UI or similar professional sans-serif
- Filters/slicers integrated naturally, not hanging off the page
- Dark header/navigation bar at top with dashboard title
- Light/white content area
- Subtle shadows or borders on cards for depth
- Clear positive (green) / negative (red) visual semantics for performance indicators

DO NOT:
- Invent additional KPIs or metrics not listed above
- Use 3D effects, glassmorphism, neon colours, or excessive decoration
- Include tiny unreadable text
- Add non-Power-BI-like custom controls or widgets
- Use illustration or clip-art
- Add fake data labels that conflict with the analytical content described
- Make it look like a mobile app or consumer dashboard

The image should look like a real Power BI report screenshot — rectangular cards arranged on a grid, standard chart types, professional data visualization. Make it look polished enough to present without apology."""

    return prompt


def generate_visual_reference(
    requirement: str,
    spec: DashboardSpec,
    page_id: str,
    output_path: Path,
    *,
    model: str = DEFAULT_IMAGE_MODEL,
    api_key: Optional[str] = None,
) -> VisualReferenceResult:
    """Generate a visual reference image for a dashboard page.

    Args:
        requirement: Original user requirement text.
        spec: The complete dashboard specification.
        page_id: ID of the page to generate a reference for.
        output_path: Where to save the generated image.
        model: OpenAI image model to use.
        api_key: Optional API key override.

    Returns:
        VisualReferenceResult with success/failure and metadata.
    """
    # Find the page
    page = next((p for p in spec.pages if p.id == page_id), None)
    if page is None:
        return VisualReferenceResult(
            success=False,
            error=f"Page '{page_id}' not found in spec",
            model=model,
        )

    # Build prompt
    prompt = _build_reference_prompt(requirement, spec, page)

    # Generate image
    start = time.time()
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key) if api_key else OpenAI()

        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size="1536x1024",
            quality="high",
        )

        # Save image — download from URL or decode b64
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image_item = response.data[0]
        if hasattr(image_item, "b64_json") and image_item.b64_json:
            image_data = base64.b64decode(image_item.b64_json)
        elif hasattr(image_item, "url") and image_item.url:
            import urllib.request
            with urllib.request.urlopen(image_item.url) as resp:
                image_data = resp.read()
        else:
            raise ValueError("No image data in response")
        output_path.write_bytes(image_data)

        elapsed = time.time() - start
        return VisualReferenceResult(
            success=True,
            output_path=str(output_path),
            model=model,
            prompt_summary=prompt[:200] + "...",
            elapsed_seconds=elapsed,
        )

    except Exception as e:
        elapsed = time.time() - start
        return VisualReferenceResult(
            success=False,
            model=model,
            prompt_summary=prompt[:200] + "...",
            elapsed_seconds=elapsed,
            error=str(e),
        )
