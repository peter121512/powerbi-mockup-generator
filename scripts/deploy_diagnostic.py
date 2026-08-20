"""Deploy a minimal diagnostic report to test if PBIR rendering works at all."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.models.dashboard_spec import (
    DashboardSpec, DashboardIntent, PageSpec, PageRole, PageLayout,
    VisualSpec, VisualType, VisualPosition, FieldRef, RevisionMetadata,
    TableSpec, ColumnSpec, MeasureSpec, ThemeSpec,
)
from pbi_gen.datagen import generate_synthetic_data
from pbi_gen.deploy.staging import generate_inline_m_from_db
from pbi_gen.renderer import render_powerbi_project
from pbi_gen.deploy.fabric import deploy_to_workspace, refresh_dataset

def main():
    project_root = Path(__file__).parent.parent

    # Minimal spec: 1 page, 1 card visual, 1 table, 1 measure
    spec = DashboardSpec(
        intent=DashboardIntent(
            title="Diagnostic Minimal",
            business_purpose="Test minimal PBIR rendering",
        ),
        revision=RevisionMetadata(spec_id="diag-001", version=1),
        pages=[
            PageSpec(
                id="page-diag",
                title="Diagnostic",
                role=PageRole.EXECUTIVE_OVERVIEW,
                layout=PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8),
                visuals=[
                    VisualSpec(
                        id="vis-rev-card",
                        visual_type=VisualType.CARD,
                        title="Revenue",
                        value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
                        position=VisualPosition(x=1, y=1, width=4, height=3),
                    ),
                ],
            ),
        ],
        tables=[
            TableSpec(
                name="Sales",
                columns=[
                    ColumnSpec(name="SaleID", data_type="INTEGER", is_key=True),
                    ColumnSpec(name="Revenue", data_type="REAL"),
                ],
                row_count_hint=10,
            ),
        ],
        measures=[
            MeasureSpec(name="TotalRevenue", expression="SUM(Sales[Revenue])", table="Sales", format_string="#,0"),
        ],
        theme=ThemeSpec(),
    )

    # Generate tiny dataset
    db_path = project_root / "build" / "diag_data" / "diag.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    result = generate_synthetic_data(spec, output_path=db_path, seed=1)
    print(f"Data: {result.outcome.value}")

    # Generate M expression
    partition_sources = {}
    for t in spec.tables:
        m = generate_inline_m_from_db(t.name, db_path, table_spec=t)
        if m:
            partition_sources[t.name] = m

    # Render PBIP
    output_dir = project_root / "build" / "diag_deploy"
    render_result = render_powerbi_project(spec=spec, output_dir=output_dir, partition_sources=partition_sources)
    print(f"Render: {render_result.outcome.value}")
    print(f"Path: {render_result.output_path}")

    # Deploy
    print("Deploying...")
    try:
        deploy_to_workspace(Path(render_result.output_path))
        print("Deployed!")
    except Exception as e:
        print(f"Deploy failed: {e}")
        return

    # Refresh
    print("Refreshing...")
    try:
        success = refresh_dataset(dataset_name="DiagnosticMinimal", wait=True, timeout=120)
        print(f"Refresh: {'OK' if success else 'FAILED'}")
    except Exception as e:
        print(f"Refresh error: {e}")


if __name__ == "__main__":
    main()
