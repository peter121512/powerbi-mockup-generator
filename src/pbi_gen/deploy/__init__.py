"""Deployment utilities for Power BI / Fabric.

Public API:
    deploy_to_workspace     — Deploy PBIP project via fabric-cicd
    refresh_dataset         — Trigger dataset refresh in Power BI Service
    get_credential          — Get Azure credential for API calls
    load_config             — Load deployment config
    DeploymentError         — Deployment error type

    export_to_csv              — Export SQLite tables to CSV
    generate_m_expression      — M expression from CSV URL
    generate_inline_m_expression — M expression with embedded data
    generate_inline_m_from_db  — M expression directly from SQLite

    deploy_end_to_end       — Full orchestration pipeline
    DeploymentResult        — Typed deployment result
    DeploymentOutcome       — Outcome enum
"""

from pbi_gen.deploy.fabric import (
    DeploymentError,
    deploy_to_workspace,
    get_credential,
    load_config,
    refresh_dataset,
)
from pbi_gen.deploy.orchestrator import (
    DeploymentOutcome,
    DeploymentResult,
    deploy_end_to_end,
)
from pbi_gen.deploy.staging import (
    export_to_csv,
    generate_inline_m_expression,
    generate_inline_m_from_db,
    generate_m_expression,
)

__all__ = [
    "DeploymentError",
    "DeploymentOutcome",
    "DeploymentResult",
    "deploy_end_to_end",
    "deploy_to_workspace",
    "export_to_csv",
    "generate_inline_m_expression",
    "generate_inline_m_from_db",
    "generate_m_expression",
    "get_credential",
    "load_config",
    "refresh_dataset",
]
