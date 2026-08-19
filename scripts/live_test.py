"""Live integration test for the AI Dashboard Designer against Bedrock.

This script runs the full designer pipeline with a real model call.
It is NOT part of the automated test suite — it requires live AWS credentials.
"""

import json
import sys
import time
from pathlib import Path

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.designer import (
    DashboardDesigner,
    BedrockProvider,
    DesignOutcome,
    ProviderConfig,
    validate_spec,
)
from pbi_gen.designer.clarification import evaluate_clarification_gate


def main():
    # Configuration
    config = ProviderConfig(
        provider="bedrock",
        model_id="anthropic.claude-3-7-sonnet-20250219-v1:0",
        region="eu-west-2",
        max_tokens=32768,
        temperature=0.4,
        timeout_seconds=600,
    )

    print(f"Provider: {config.provider}")
    print(f"Model: {config.model_id}")
    print(f"Region: {config.region}")
    print(f"Max tokens: {config.max_tokens}")
    print(f"Temperature: {config.temperature}")
    print()

    # The test prompt from TASK.md
    requirement = (
        "Create an executive retail performance dashboard for a UK retailer. "
        "The primary audience is the CEO and CFO. Show revenue, gross margin, "
        "YoY growth, regional performance, product/category performance and "
        "major underperformance risks. It should feel premium, restrained and "
        "boardroom-ready. Include useful filters for period, region and category."
    )

    print(f"Requirement: {requirement}")
    print()
    print("=" * 70)
    print("Calling Bedrock...")
    print()

    # Run the designer
    provider = BedrockProvider(config=config)
    designer = DashboardDesigner(provider=provider, debug=True)

    start = time.time()
    result = designer.design_dashboard(requirement)
    elapsed = time.time() - start

    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Outcome: {result.outcome.value}")
    print()

    if result.outcome == DesignOutcome.SUCCESS:
        spec = result.spec
        print(f"Title: {spec.intent.title}")
        print(f"Business purpose: {spec.intent.business_purpose}")
        print(f"Audience: {spec.intent.intended_audience}")
        print(f"Domain: {spec.intent.business_domain}")
        print(f"Pages: {len(spec.pages)}")
        for p in spec.pages:
            print(f"  - {p.title} ({p.role.value}) — {len(p.visuals)} visuals, {len(p.filters)} filters")
        print(f"Tables: {len(spec.tables)}")
        for t in spec.tables:
            print(f"  - {t.name} ({len(t.columns)} cols, {t.row_count_hint} rows)")
        print(f"Measures: {len(spec.measures)}")
        for m in spec.measures:
            print(f"  - {m.name}: {m.expression[:60]}")
        print(f"Relationships: {len(spec.relationships)}")
        print(f"Mock narrative: {'Yes' if spec.mock_data_narrative else 'No'}")
        if spec.mock_data_narrative:
            print(f"  Patterns: {len(spec.mock_data_narrative.patterns)}")
            print(f"  Insights: {len(spec.mock_data_narrative.key_insights)}")
        print(f"Theme: {spec.theme.style_family} ({spec.theme.presentation_mode.value})")
        print(f"Confidence assessments: {len(spec.confidence.assessments)}")
        print(f"Assumptions: {len(spec.confidence.assumptions)}")
        print(f"Requires clarification: {spec.confidence.requires_clarification}")
        print()

        # Semantic validation
        issues = validate_spec(spec)
        print(f"Semantic validation issues: {len(issues)}")
        for issue in issues:
            print(f"  [{issue.category}] {issue.message} @ {issue.path}")
        print()

        # Clarification gate
        gate = evaluate_clarification_gate(spec)
        print(f"Clarification gate: should_clarify={gate.should_clarify}")
        if gate.triggered_rules:
            print(f"  Rules: {gate.triggered_rules}")
        print()

        # Save output
        output_path = Path(__file__).parent.parent / "docs" / "stages" / "02a-live-designer-test" / "LIVE_OUTPUT.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved to: {output_path}")

    elif result.outcome == DesignOutcome.CLARIFICATION_NEEDED:
        print(f"Clarification question: {result.clarification.question}")
        print(f"Dimension: {result.clarification.dimension}")

    elif result.outcome == DesignOutcome.PROVIDER_ERROR:
        print(f"Provider error: {result.error_message}")

    elif result.outcome == DesignOutcome.INVALID_OUTPUT:
        print(f"Invalid output: {result.error_message}")
        if result.diagnostics.validation_errors:
            for err in result.diagnostics.validation_errors[:10]:
                print(f"  [{err.category}] {err.message} @ {err.path}")
        if result.diagnostics.raw_response:
            # Save raw response for debugging
            raw_path = Path(__file__).parent.parent / "docs" / "stages" / "02a-live-designer-test" / "RAW_RESPONSE.txt"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(result.diagnostics.raw_response, encoding="utf-8")
            print(f"Raw response saved to: {raw_path}")
            # Print first 2000 chars for diagnosis
            print(f"\nFirst 2000 chars of response:")
            print(result.diagnostics.raw_response[:2000])

    elif result.outcome == DesignOutcome.VALIDATION_ERROR:
        print(f"Validation error: {result.error_message}")
        for err in result.diagnostics.validation_errors[:10]:
            print(f"  [{err.category}] {err.message} @ {err.path}")

    print()
    print("=" * 70)
    return result


if __name__ == "__main__":
    main()
