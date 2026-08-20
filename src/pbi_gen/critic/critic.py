"""Multimodal visual critic using OpenAI vision models."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Optional

from pbi_gen.critic.models import (
    CritiqueDimensions,
    CritiqueIssue,
    IssueOwner,
    IssueSeverity,
    VisualCritique,
)
from pbi_gen.models import DashboardSpec, PageSpec

# Default model — configurable
DEFAULT_CRITIC_MODEL = "gpt-5.6-sol"


def _build_critic_prompt(
    requirement: str,
    spec: DashboardSpec,
    page: PageSpec,
) -> str:
    """Build the system prompt for the visual critic."""

    # Gather page visuals info
    visuals_info = []
    for v in page.visuals:
        fields = []
        for f in (v.value_fields or []):
            fields.append(f.measure or f.column or "?")
        for f in (v.category_fields or []):
            fields.append(f.column or "?")
        visuals_info.append(f"  - {v.title or v.id} ({v.visual_type.value}): {', '.join(fields)}")

    visuals_text = "\n".join(visuals_info)

    return f"""You are a senior enterprise dashboard design critic. You are evaluating a Power BI dashboard page against both a visual reference image and the analytical specification.

BUSINESS CONTEXT: {spec.intent.business_purpose}
USER REQUIREMENT: {requirement}
PAGE: {page.title} (role: {page.role.value if page.role else 'executive'})
AUDIENCE: CEO/CFO board-level executives

EXPECTED VISUALS ON THIS PAGE:
{visuals_text}

You will receive two images:
1. REFERENCE IMAGE — an AI-generated visual target showing the desired premium quality bar
2. ACTUAL IMAGE — a real screenshot of the deployed Power BI report

Your task:
1. Score the ACTUAL dashboard on each quality dimension (0-10 scale)
2. Identify specific actionable issues
3. Classify each issue by severity and owner
4. Note any reference image ideas that are impractical or non-analytical

IMPORTANT RULES:
- Do NOT simply optimize pixel similarity to the reference
- Judge whether the actual dashboard achieves the ANALYTICAL PURPOSE
- Distinguish renderer/theme fixable issues from Power BI platform limitations
- A difference from the reference is acceptable if the actual is analytically sound
- Never recommend changes that would break data correctness or measure semantics
- Focus on the highest-impact visual improvements that are achievable in Power BI

Respond with a JSON object matching this exact schema:
{{
  "scores": {{
    "overall": <0-10>,
    "executive_credibility": <0-10>,
    "information_hierarchy": <0-10>,
    "visual_density": <0-10>,
    "whitespace": <0-10>,
    "alignment_grid": <0-10>,
    "kpi_prominence": <0-10>,
    "typography_readability": <0-10>,
    "colour_consistency": <0-10>,
    "chart_appropriateness": <0-10>,
    "chart_legibility": <0-10>,
    "filter_placement": <0-10>,
    "data_storytelling": <0-10>,
    "polish_premium": <0-10>,
    "reference_fidelity": <0-10>,
    "implementation_feasibility": <0-10>
  }},
  "issues": [
    {{
      "id": "<short-id>",
      "severity": "critical|high|medium|low|info",
      "dimension": "<which quality dimension>",
      "page_id": "<page-id or null>",
      "visual_id": "<visual-id or null>",
      "observed": "<what you see in the actual>",
      "desired": "<what it should look like>",
      "owner": "designer|renderer|theme|layout|powerbi_limit|non_actionable_reference_gap",
      "action": "<specific recommendation>",
      "confidence": <0.0-1.0>
    }}
  ],
  "summary": "<brief overall assessment>",
  "reference_rejected_ideas": ["<ideas from reference that are impractical>"]
}}

Return ONLY valid JSON, no markdown code blocks or commentary."""


def _encode_image(path: Path) -> str:
    """Encode an image file as base64 for the API."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def critique_visuals(
    requirement: str,
    spec: DashboardSpec,
    page_id: str,
    reference_path: Path,
    actual_path: Path,
    *,
    model: str = DEFAULT_CRITIC_MODEL,
    api_key: Optional[str] = None,
) -> VisualCritique:
    """Run the multimodal visual critic on reference vs actual images.

    Args:
        requirement: Original user requirement.
        spec: Dashboard specification.
        page_id: The page being critiqued.
        reference_path: Path to the reference image.
        actual_path: Path to the actual screenshot.
        model: OpenAI model to use for critique.
        api_key: Optional API key override.

    Returns:
        Structured VisualCritique.
    """
    page = next((p for p in spec.pages if p.id == page_id), None)
    if page is None:
        raise ValueError(f"Page '{page_id}' not found in spec")

    prompt = _build_critic_prompt(requirement, spec, page)

    from openai import OpenAI

    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    # Build message with two images
    ref_b64 = _encode_image(reference_path)
    actual_b64 = _encode_image(actual_path)

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Here are the two images to compare. Image 1 is the REFERENCE (target quality). Image 2 is the ACTUAL deployed dashboard."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{ref_b64}"},
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{actual_b64}"},
                },
            ],
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=4096,
    )

    # Parse response
    content = response.choices[0].message.content.strip()

    # Strip markdown code blocks if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    data = json.loads(content)

    # Build typed model
    scores = CritiqueDimensions(**data["scores"])
    issues = []
    for issue_data in data.get("issues", []):
        issues.append(CritiqueIssue(
            id=issue_data["id"],
            severity=IssueSeverity(issue_data["severity"]),
            dimension=issue_data["dimension"],
            page_id=issue_data.get("page_id"),
            visual_id=issue_data.get("visual_id"),
            observed=issue_data["observed"],
            desired=issue_data["desired"],
            owner=IssueOwner(issue_data["owner"]),
            action=issue_data["action"],
            confidence=issue_data.get("confidence", 0.7),
        ))

    return VisualCritique(
        scores=scores,
        issues=issues,
        summary=data.get("summary", ""),
        reference_rejected_ideas=data.get("reference_rejected_ideas", []),
    )
