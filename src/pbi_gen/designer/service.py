"""Main designer service — the public entry point for dashboard design.

Orchestrates: prompt construction → LLM call → parsing → validation →
clarification gate → typed result.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from uuid import uuid4

from pydantic import ValidationError

from pbi_gen.models.dashboard_spec import DashboardSpec, RevisionMetadata
from pbi_gen.designer.clarification import evaluate_clarification_gate
from pbi_gen.designer.prompt import (
    build_user_message,
    get_dashboard_schema,
    get_system_prompt,
)
from pbi_gen.designer.provider import LLMProvider, ProviderError
from pbi_gen.designer.result import (
    DesignDiagnostics,
    DesignResult,
    ValidationIssue,
)
from pbi_gen.designer.validator import validate_spec

logger = logging.getLogger(__name__)


class DashboardDesigner:
    """AI-powered dashboard designer service.

    Converts natural-language requirements into a validated DashboardSpec
    through LLM reasoning, Pydantic validation, semantic checks, and a
    deterministic clarification gate.

    Usage:
        from pbi_gen.designer import DashboardDesigner
        from pbi_gen.designer.provider import BedrockProvider

        designer = DashboardDesigner(provider=BedrockProvider())
        result = designer.design_dashboard(
            "Create an executive retail performance dashboard..."
        )

        if result.outcome == DesignOutcome.SUCCESS:
            spec = result.spec
        elif result.outcome == DesignOutcome.CLARIFICATION_NEEDED:
            print(result.clarification.question)
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        debug: bool = False,
    ):
        """Initialize the designer.

        Args:
            provider: LLM provider for generating structured output.
            debug: If True, include raw model response in diagnostics.
        """
        self._provider = provider
        self._debug = debug

    def design_dashboard(self, requirement: str) -> DesignResult:
        """Design a new dashboard from a natural-language requirement.

        This is the primary public entry point. The flow is:
        1. Build prompt with schema constraints
        2. Call LLM provider
        3. Parse JSON response
        4. Validate through Pydantic
        5. Ensure valid initial revision metadata
        6. Run semantic cross-reference validation
        7. Apply deterministic clarification gate
        8. Return typed result

        Args:
            requirement: Natural-language dashboard requirements.

        Returns:
            DesignResult with one of:
            - SUCCESS: validated DashboardSpec
            - CLARIFICATION_NEEDED: question for the user
            - PROVIDER_ERROR: provider call failed
            - INVALID_OUTPUT: response wasn't valid JSON/schema
            - VALIDATION_ERROR: semantic cross-reference issues
        """
        diagnostics_kwargs = {
            "provider": self._provider.provider_name,
            "model": self._provider.model_name,
        }

        # 1. Build prompt
        schema = get_dashboard_schema()
        system_prompt = get_system_prompt(schema)
        user_message = build_user_message(requirement)

        # 2. Call provider
        try:
            response = self._provider.generate_structured(
                system_prompt=system_prompt,
                user_message=user_message,
                json_schema=schema,
            )
        except ProviderError as e:
            logger.error("Provider error: %s", e)
            return DesignResult.provider_error(
                str(e),
                DesignDiagnostics(**diagnostics_kwargs),
            )

        raw_content = response.content
        if self._debug:
            diagnostics_kwargs["raw_response"] = raw_content

        # 3. Parse JSON
        json_data = _extract_json(raw_content)
        if json_data is None:
            logger.error("Failed to parse JSON from model response")
            return DesignResult.invalid_output(
                "Model response is not valid JSON.",
                DesignDiagnostics(**diagnostics_kwargs),
            )

        # 4. Validate through Pydantic
        try:
            spec = DashboardSpec.model_validate(json_data)
        except ValidationError as e:
            logger.error("Pydantic validation failed: %s", e)
            issues = [
                ValidationIssue(
                    category="pydantic_error",
                    message=str(err["msg"]),
                    path=".".join(str(x) for x in err.get("loc", [])),
                )
                for err in e.errors()
            ]
            return DesignResult.invalid_output(
                f"Model output failed schema validation: {len(e.errors())} error(s).",
                DesignDiagnostics(
                    **diagnostics_kwargs,
                    validation_errors=issues,
                ),
            )

        # 5. Ensure valid initial revision metadata
        spec = _ensure_initial_revision(spec)

        # 6. Semantic cross-reference validation
        semantic_issues = validate_spec(spec)
        if semantic_issues:
            logger.warning(
                "Semantic validation found %d issue(s)", len(semantic_issues)
            )
            return DesignResult.validation_error(
                f"Generated spec has {len(semantic_issues)} semantic issue(s).",
                issues=semantic_issues,
                diagnostics=DesignDiagnostics(**diagnostics_kwargs),
            )

        # 7. Deterministic clarification gate
        gate_decision = evaluate_clarification_gate(spec)

        # Reconcile: deterministic gate overrides LLM's requires_clarification
        if gate_decision.should_clarify and gate_decision.clarification:
            logger.info(
                "Clarification gate triggered: %s",
                gate_decision.triggered_rules,
            )
            diag = DesignDiagnostics(
                **diagnostics_kwargs,
                clarification_dimensions=[gate_decision.clarification.dimension],
                assumptions_made=[
                    a.statement for a in spec.confidence.assumptions
                ],
            )
            return DesignResult.needs_clarification(
                gate_decision.clarification,
                diag,
            )

        # 8. Success
        diag = DesignDiagnostics(
            **diagnostics_kwargs,
            assumptions_made=[a.statement for a in spec.confidence.assumptions],
        )
        return DesignResult.success(spec, diag)


def _extract_json(content: str) -> dict | None:
    """Extract JSON from model response, handling markdown code fences."""
    content = content.strip()

    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    if "```" in content:
        # Find content between first ``` and last ```
        lines = content.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            elif line.strip() == "```" and in_block:
                break
            elif in_block:
                json_lines.append(line)

        if json_lines:
            try:
                return json.loads("\n".join(json_lines))
            except json.JSONDecodeError:
                pass

    # Try finding the outermost { ... }
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _ensure_initial_revision(spec: DashboardSpec) -> DashboardSpec:
    """Ensure the spec has valid initial revision metadata.

    For a newly designed dashboard:
    - version must be 1
    - parent_spec_id must be empty
    - spec_id must be valid (generate if missing/default)
    - created_at should be current
    """
    revision = spec.revision

    # Force version 1 and no parent for initial generation
    needs_update = False
    new_values = {}

    if revision.version != 1:
        new_values["version"] = 1
        needs_update = True

    if revision.parent_spec_id:
        new_values["parent_spec_id"] = ""
        needs_update = True

    if needs_update:
        # Rebuild with corrected values
        revision_data = revision.model_dump()
        revision_data.update(new_values)
        new_revision = RevisionMetadata.model_validate(revision_data)
        spec_data = spec.model_dump()
        spec_data["revision"] = new_revision.model_dump()
        spec = DashboardSpec.model_validate(spec_data)

    return spec


# Convenience function for simple usage
def design_dashboard(
    requirement: str,
    provider: LLMProvider,
    *,
    debug: bool = False,
) -> DesignResult:
    """Design a dashboard from a natural-language requirement.

    Convenience wrapper around DashboardDesigner for simple one-shot usage.

    Args:
        requirement: Natural-language dashboard requirements.
        provider: LLM provider instance.
        debug: Include raw response in diagnostics.

    Returns:
        DesignResult with the outcome.
    """
    designer = DashboardDesigner(provider=provider, debug=debug)
    return designer.design_dashboard(requirement)
