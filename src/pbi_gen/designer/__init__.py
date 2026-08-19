"""AI Dashboard Designer — converts natural-language requirements into DashboardSpec.

Public API:
    DashboardDesigner  — the main service class
    design_dashboard   — convenience function for one-shot usage
    DesignResult       — typed outcome of a design call
    DesignOutcome      — discriminator enum for result variants
"""

from pbi_gen.designer.result import (
    ClarificationRequest,
    DesignDiagnostics,
    DesignOutcome,
    DesignResult,
    ValidationIssue,
)
from pbi_gen.designer.service import DashboardDesigner, design_dashboard
from pbi_gen.designer.provider import (
    BedrockProvider,
    LLMProvider,
    ProviderConfig,
    ProviderError,
    ProviderResponse,
)
from pbi_gen.designer.clarification import (
    GateDecision,
    evaluate_clarification_gate,
)
from pbi_gen.designer.validator import validate_spec

__all__ = [
    # Service
    "DashboardDesigner",
    "design_dashboard",
    # Results
    "DesignResult",
    "DesignOutcome",
    "ClarificationRequest",
    "DesignDiagnostics",
    "ValidationIssue",
    # Provider
    "LLMProvider",
    "BedrockProvider",
    "ProviderConfig",
    "ProviderError",
    "ProviderResponse",
    # Gate
    "GateDecision",
    "evaluate_clarification_gate",
    # Validator
    "validate_spec",
]
