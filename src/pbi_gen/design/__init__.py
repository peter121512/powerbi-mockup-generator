"""Stage 13 — conversational image-first dashboard design workflow.

Public API:
- DataContext ingestion: profile_spreadsheet, resolve_url, context_from_description
- DashboardMockupService (+ OpenAIImageAdapter / StubImageAdapter)
- DesignWorkflow (start_session, revise, approve)
- DashboardDesignSession / DashboardDesignSpec
- feasibility: classify_visual, CustomVisualRequirement, ImplementationClass
- build handoff: spec_to_report_spec
"""

from .data_context import DataContext, DataSource, FieldProfile, FieldRole, FieldType
from .feasibility import (
    CustomVisualRequirement,
    ImplementationClass,
    VisualClassification,
    build_custom_visual_requirement,
    classify_visual,
)
from .ingestion import (
    FileResolver,
    context_from_description,
    profile_spreadsheet,
    resolve_url,
)
from .mockup_service import (
    DashboardMockupService,
    ImageAdapter,
    MockupRevision,
    OpenAIImageAdapter,
    StubImageAdapter,
    default_adapter,
)
from .session import (
    ApprovalState,
    DashboardDesignSession,
    DashboardDesignSpec,
    ProposedVisual,
    RevisionDelta,
    is_approval_intent,
)
from .workflow import DesignWorkflow, infer_audience, infer_kpis, parse_revision

__all__ = [
    "DataContext", "DataSource", "FieldProfile", "FieldRole", "FieldType",
    "profile_spreadsheet", "resolve_url", "context_from_description", "FileResolver",
    "DashboardMockupService", "ImageAdapter", "OpenAIImageAdapter", "StubImageAdapter",
    "MockupRevision", "default_adapter",
    "DashboardDesignSession", "DashboardDesignSpec", "ProposedVisual", "RevisionDelta",
    "ApprovalState", "is_approval_intent",
    "classify_visual", "VisualClassification", "ImplementationClass",
    "CustomVisualRequirement", "build_custom_visual_requirement",
    "DesignWorkflow", "infer_audience", "infer_kpis", "parse_revision",
]
