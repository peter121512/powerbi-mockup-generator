"""Critic loop orchestrator — runs the full reference → screenshot → critique → revise cycle."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pbi_gen.critic.models import (
    LoopIterationResult,
    ScreenshotOutcome,
    VisualCritique,
)
from pbi_gen.critic.planner import create_revision_plan, should_stop
from pbi_gen.critic.reference import generate_visual_reference
from pbi_gen.critic.critic import critique_visuals
from pbi_gen.critic.screenshot import capture_report_page
from pbi_gen.models import DashboardSpec


def run_critic_loop(
    requirement: str,
    spec: DashboardSpec,
    page_id: str,
    report_id: str,
    output_dir: Path,
    *,
    max_iterations: int = 3,
    reference_path: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> list[LoopIterationResult]:
    """Run the full visual critic loop.

    Steps per iteration:
    1. Capture actual screenshot
    2. Critique against reference + spec
    3. Create revision plan
    4. Check stopping policy
    5. Apply revisions (if continuing)

    Args:
        requirement: Original user requirement.
        spec: Dashboard specification.
        page_id: Page to critique.
        report_id: Deployed report ID.
        output_dir: Directory for artifacts.
        max_iterations: Maximum loop iterations.
        reference_path: Pre-generated reference image. If None, generates one.
        api_key: OpenAI API key.

    Returns:
        List of iteration results.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[LoopIterationResult] = []
    previous_score: Optional[float] = None

    # Step 0: Generate reference if not provided
    if reference_path is None or not reference_path.exists():
        reference_path = output_dir / "reference.png"
        ref_result = generate_visual_reference(
            requirement=requirement,
            spec=spec,
            page_id=page_id,
            output_path=reference_path,
            api_key=api_key,
        )
        if not ref_result.success:
            results.append(LoopIterationResult(
                iteration=0,
                stopped_reason=f"Reference generation failed: {ref_result.error}",
            ))
            return results

    for iteration in range(1, max_iterations + 1):
        # 1. Capture screenshot
        screenshot_path = output_dir / f"actual-iter{iteration}.png"

        # Find page name from spec
        page = next((p for p in spec.pages if p.id == page_id), None)
        page_name = page.title if page else page_id

        screenshot = capture_report_page(
            report_id=report_id,
            page_name=page_name,
            output_path=screenshot_path,
        )

        if screenshot.outcome != ScreenshotOutcome.SUCCESS:
            results.append(LoopIterationResult(
                iteration=iteration,
                stopped_reason=f"Screenshot failed: {screenshot.outcome.value} - {screenshot.error}",
            ))
            break

        # 2. Critique
        try:
            critique = critique_visuals(
                requirement=requirement,
                spec=spec,
                page_id=page_id,
                reference_path=reference_path,
                actual_path=screenshot_path,
                api_key=api_key,
            )
        except Exception as e:
            results.append(LoopIterationResult(
                iteration=iteration,
                screenshot_path=str(screenshot_path),
                stopped_reason=f"Critique failed: {e}",
            ))
            break

        # 3. Revision plan
        plan = create_revision_plan(critique)

        # 4. Check stopping policy
        stop, reason = should_stop(
            critique,
            iteration,
            max_iterations=max_iterations,
            previous_score=previous_score,
        )

        result = LoopIterationResult(
            iteration=iteration,
            critique=critique,
            revision_plan=plan,
            screenshot_path=str(screenshot_path),
            score_before=previous_score,
            score_after=critique.scores.overall,
            stopped_reason=reason if stop else None,
        )
        results.append(result)

        previous_score = critique.scores.overall

        if stop:
            break

        # 5. Apply revisions would go here — for now we record the plan
        # Actual code changes require renderer/spec modifications which
        # are stage-specific and implemented in the live integration script

    return results
