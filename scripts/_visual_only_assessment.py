"""Visual-only design assessment — ignores analytical defects per Stage 07b rubric."""
import sys
import json
import base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openai import OpenAI

client = OpenAI()

VISUAL_ONLY_RUBRIC = """You are a senior executive dashboard design critic evaluating VISUAL PRESENTATION QUALITY ONLY.

IMPORTANT: You MUST IGNORE these analytical/data defects entirely — do NOT penalize them:
- Month ordering (alphabetical vs chronological)
- Mixed-scale axes (revenue + percentage on same axis)
- Chart type choices
- Data story or metric choices
- Semantic model issues

Score ONLY the visual design, composition, and presentation quality on these dimensions (0-10 each):

1. first_impression: Does it immediately look premium and intentionally designed?
2. executive_credibility: Would a CEO/CFO trust this as professionally produced?
3. composition_hierarchy: Is there clear focal hierarchy (header→KPIs→hero→supporting)?
4. typography: Is the typographic system deliberate and authoritative?
5. whitespace_rhythm: Is spacing deliberate, generous, and rhythmic?
6. kpi_treatment: Do KPI cards look like a coherent bespoke system?
7. colour_discipline: Are colours restrained, purposeful, and sophisticated?
8. surface_quality: Are backgrounds/borders/containers coherent and polished?
9. chart_presentation: Do charts feel integrated and clean (ignoring data choices)?
10. section_coherence: Do page sections read as one composition?
11. visual_consistency: Is styling uniform across all elements?
12. premium_feel: Does it feel materially above "default Power BI with formatting"?
13. demo_readiness: Would you show this full-screen to 500 employees without apology?
14. company_wide_readiness: Would visual quality make the team look highly professional?

Also answer these binary YES/NO questions:
Q1: "Ignoring analytical-choice defects, would you be comfortable presenting this exact dashboard design to the executive committee of a large enterprise?"
Q2: "If shown full-screen at a company-wide town hall, would its visual quality make the product/team look highly professional?"
Q3: "Does this visually feel materially closer to a premium bespoke executive dashboard than to a well-formatted default Power BI report?"

Compare the actual dashboard against the reference image for DESIGN QUALITY LEVEL (not pixel similarity or analytical content). Score reference_relative as 0-100: how close is the native dashboard's design quality to the reference's visual standard?

Respond with ONLY valid JSON:
{
  "scores": {
    "first_impression": <0-10>,
    "executive_credibility": <0-10>,
    "composition_hierarchy": <0-10>,
    "typography": <0-10>,
    "whitespace_rhythm": <0-10>,
    "kpi_treatment": <0-10>,
    "colour_discipline": <0-10>,
    "surface_quality": <0-10>,
    "chart_presentation": <0-10>,
    "section_coherence": <0-10>,
    "visual_consistency": <0-10>,
    "premium_feel": <0-10>,
    "demo_readiness": <0-10>,
    "company_wide_readiness": <0-10>
  },
  "overall": <0-10 weighted average>,
  "binary_q1": "YES" or "NO",
  "binary_q2": "YES" or "NO",
  "binary_q3": "YES" or "NO",
  "reference_relative": <0-100>,
  "summary": "<brief visual-only assessment>"
}"""


def run_visual_only_assessment(actual_path: Path, reference_path: Path) -> dict:
    ref_b64 = base64.b64encode(reference_path.read_bytes()).decode("ascii")
    actual_b64 = base64.b64encode(actual_path.read_bytes()).decode("ascii")

    messages = [
        {"role": "system", "content": VISUAL_ONLY_RUBRIC},
        {"role": "user", "content": [
            {"type": "text", "text": "Image 1 is the REFERENCE mockup (design quality target). Image 2 is the ACTUAL deployed Power BI dashboard. Score the ACTUAL on visual design only."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{ref_b64}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{actual_b64}"}},
        ]},
    ]

    response = client.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages,
        max_completion_tokens=2048,
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        response = client.chat.completions.create(model="gpt-5.6-sol", messages=messages, max_completion_tokens=2048)
        content = (response.choices[0].message.content or "").strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    return json.loads(content)


if __name__ == "__main__":
    actual = Path("docs/stages/07-enterprise-visual-baseline/executive-baseline-after.png")
    reference = Path("docs/stages/07b-executive-design-language/executive-light-ref.png")

    print("Running 3 visual-only assessments...")
    results = []
    for i in range(3):
        print(f"\nRun {i+1}/3...")
        try:
            result = run_visual_only_assessment(actual, reference)
            results.append(result)
            print(f"  Overall: {result['overall']}")
            print(f"  Q1 (exec committee): {result['binary_q1']}")
            print(f"  Q2 (company-wide): {result['binary_q2']}")
            print(f"  Q3 (premium vs default): {result['binary_q3']}")
            print(f"  Reference relative: {result['reference_relative']}/100")
        except Exception as e:
            print(f"  Error: {e}")

    if results:
        overalls = sorted([r["overall"] for r in results])
        median = overalls[len(overalls)//2]
        print(f"\n=== RESULTS ===")
        print(f"Scores: {overalls}")
        print(f"Median: {median}")
        print(f"Range: {min(overalls)}-{max(overalls)}")
        print(f"Q1 YES count: {sum(1 for r in results if r.get('binary_q1') == 'YES')}/3")
        print(f"Q2 YES count: {sum(1 for r in results if r.get('binary_q2') == 'YES')}/3")
        print(f"Q3 YES count: {sum(1 for r in results if r.get('binary_q3') == 'YES')}/3")

        # Save
        output = {
            "runs": results,
            "median_overall": median,
            "range": [min(overalls), max(overalls)],
        }
        Path("docs/stages/07b-executive-design-language/EXECUTIVE_DESIGN_ASSESSMENT.json").write_text(
            json.dumps(output, indent=2), encoding="utf-8"
        )
        print("Saved to EXECUTIVE_DESIGN_ASSESSMENT.json")
