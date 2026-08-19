"""End-to-end deployment orchestration.

Coordinates the full deploy pipeline:
1. Stage data (generate inline M expressions from SQLite)
2. Render PBIP with real partition sources
3. Deploy to Fabric via fabric-cicd
4. Trigger dataset refresh
5. Return typed result

This module provides the deploy_end_to_end() function as the single entry
point for deploying a generated dashboard to Power BI Service.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pbi_gen.deploy.fabric import DeploymentError, deploy_to_workspace, refresh_dataset
from pbi_gen.deploy.staging import generate_inline_m_from_db
from pbi_gen.models import DashboardSpec
from pbi_gen.renderer import render_powerbi_project


class DeploymentOutcome(Enum):
    """Possible outcomes of an end-to-end deployment."""

    SUCCESS = "success"
    AUTH_FAILURE = "auth_failure"
    WORKSPACE_FAILURE = "workspace_failure"
    SEMANTIC_MODEL_FAILURE = "semantic_model_failure"
    REPORT_FAILURE = "report_failure"
    DATA_STAGING_FAILURE = "data_staging_failure"
    REFRESH_FAILURE = "refresh_failure"


@dataclass
class DeploymentResult:
    """Result of an end-to-end deployment attempt."""

    outcome: DeploymentOutcome
    message: str
    workspace_id: str = ""
    semantic_model_name: str = ""
    report_name: str = ""
    refresh_status: str = ""
    elapsed_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the deployment succeeded."""
        return self.outcome == DeploymentOutcome.SUCCESS


def deploy_end_to_end(
    spec: DashboardSpec,
    data_path: Path,
    output_dir: Path,
    config: dict | None = None,
) -> DeploymentResult:
    """Execute a complete deployment pipeline.

    Orchestrates data staging, PBIP rendering with real data, deployment
    to Fabric workspace, and dataset refresh.

    Args:
        spec: The dashboard specification to deploy.
        data_path: Path to the SQLite database with generated data.
        output_dir: Working directory for rendered PBIP output.
        config: Optional config overrides (workspace_id, auth, etc.).

    Returns:
        DeploymentResult with outcome and metadata.
    """
    start_time = time.time()
    warnings: list[str] = []

    # ── Step 1: Stage data — generate inline M expressions ──────────────
    try:
        partition_sources = _stage_data(spec, data_path)
    except Exception as e:
        return DeploymentResult(
            outcome=DeploymentOutcome.DATA_STAGING_FAILURE,
            message=f"Data staging failed: {e}",
            elapsed_seconds=time.time() - start_time,
        )

    # ── Step 2: Render PBIP with real partition sources ──────────────────
    try:
        render_result = render_powerbi_project(
            spec,
            output_dir,
            partition_sources=partition_sources,
        )
        if render_result.outcome.value not in ("success", "partial"):
            return DeploymentResult(
                outcome=DeploymentOutcome.SEMANTIC_MODEL_FAILURE,
                message=f"PBIP render failed: {render_result.message}",
                elapsed_seconds=time.time() - start_time,
            )
        if render_result.outcome.value == "partial":
            warnings.append(f"Partial render: {render_result.message}")

        project_root = render_result.output_path
        project_name = render_result.project_name
    except Exception as e:
        return DeploymentResult(
            outcome=DeploymentOutcome.SEMANTIC_MODEL_FAILURE,
            message=f"PBIP rendering failed: {e}",
            elapsed_seconds=time.time() - start_time,
        )

    # ── Step 3: Deploy via fabric-cicd ──────────────────────────────────
    try:
        deploy_to_workspace(project_root)
    except DeploymentError as e:
        error_msg = str(e)
        if "Authentication" in error_msg or "auth" in error_msg.lower():
            outcome = DeploymentOutcome.AUTH_FAILURE
        elif "not found" in error_msg.lower() or "workspace" in error_msg.lower():
            outcome = DeploymentOutcome.WORKSPACE_FAILURE
        else:
            outcome = DeploymentOutcome.SEMANTIC_MODEL_FAILURE
        return DeploymentResult(
            outcome=outcome,
            message=error_msg,
            elapsed_seconds=time.time() - start_time,
            warnings=warnings,
        )
    except Exception as e:
        return DeploymentResult(
            outcome=DeploymentOutcome.SEMANTIC_MODEL_FAILURE,
            message=f"Deployment failed: {e}",
            elapsed_seconds=time.time() - start_time,
            warnings=warnings,
        )

    # ── Step 4: Trigger dataset refresh ─────────────────────────────────
    try:
        refresh_ok = refresh_dataset(dataset_name=project_name, wait=True)
        refresh_status = "completed" if refresh_ok else "failed"
    except DeploymentError as e:
        return DeploymentResult(
            outcome=DeploymentOutcome.REFRESH_FAILURE,
            message=f"Dataset refresh failed: {e}",
            semantic_model_name=project_name,
            report_name=project_name,
            elapsed_seconds=time.time() - start_time,
            warnings=warnings,
        )
    except Exception as e:
        return DeploymentResult(
            outcome=DeploymentOutcome.REFRESH_FAILURE,
            message=f"Refresh error: {e}",
            semantic_model_name=project_name,
            report_name=project_name,
            elapsed_seconds=time.time() - start_time,
            warnings=warnings,
        )

    if refresh_status == "failed":
        return DeploymentResult(
            outcome=DeploymentOutcome.REFRESH_FAILURE,
            message="Dataset refresh completed with failure status",
            semantic_model_name=project_name,
            report_name=project_name,
            refresh_status=refresh_status,
            elapsed_seconds=time.time() - start_time,
            warnings=warnings,
        )

    # ── Success ─────────────────────────────────────────────────────────
    return DeploymentResult(
        outcome=DeploymentOutcome.SUCCESS,
        message="Deployment and refresh completed successfully",
        semantic_model_name=project_name,
        report_name=project_name,
        refresh_status=refresh_status,
        elapsed_seconds=time.time() - start_time,
        warnings=warnings,
    )


def _stage_data(spec: DashboardSpec, db_path: Path) -> dict[str, str]:
    """Generate inline M expressions for all tables in the spec.

    Args:
        spec: Dashboard specification with table definitions.
        db_path: Path to the SQLite database.

    Returns:
        Mapping of {table_name: m_expression} for partition sources.
    """
    partition_sources: dict[str, str] = {}
    for table in spec.tables:
        m_expr = generate_inline_m_from_db(table.name, db_path)
        partition_sources[table.name] = m_expr
    return partition_sources
