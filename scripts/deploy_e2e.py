"""Full end-to-end deployment: generate data, render PBIP with inline data, deploy to Fabric."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.models.dashboard_spec import DashboardSpec
from pbi_gen.datagen import generate_synthetic_data, DataGenOutcome
from pbi_gen.deploy.staging import generate_inline_m_from_db
from pbi_gen.renderer import render_powerbi_project, RenderOutcome
from pbi_gen.deploy.fabric import deploy_to_workspace, refresh_dataset, load_config


def main():
    project_root = Path(__file__).parent.parent

    # 1. Load spec
    spec_path = project_root / "docs" / "stages" / "02a-live-designer-test" / "LIVE_OUTPUT.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = DashboardSpec.model_validate(json.load(f))
    print(f"[1] Loaded spec: {spec.intent.title}")

    # 2. Generate data
    db_path = project_root / "build" / "live_data" / "retail_dashboard.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[2] Generating synthetic data...")
    data_result = generate_synthetic_data(spec, output_path=db_path, seed=42)
    if data_result.outcome != DataGenOutcome.SUCCESS:
        print(f"    FAILED: {data_result.error_message}")
        return
    print(f"    Generated {sum(t.row_count for t in data_result.diagnostics.tables)} rows")

    # 3. Generate inline M expressions for each table
    print(f"[3] Generating inline M expressions from SQLite...")
    partition_sources = {}
    for table_spec in spec.tables:
        m_expr = generate_inline_m_from_db(table_spec.name, db_path, table_spec=table_spec)
        if m_expr:
            partition_sources[table_spec.name] = m_expr
            print(f"    {table_spec.name}: {len(m_expr)} chars")
        else:
            print(f"    {table_spec.name}: SKIPPED (no data or table not found)")

    # 4. Render PBIP with real partitions
    output_dir = project_root / "build" / "deploy"
    print(f"[4] Rendering PBIP with inline data partitions...")
    render_result = render_powerbi_project(
        spec=spec,
        output_dir=output_dir,
        partition_sources=partition_sources,
    )
    if render_result.outcome != RenderOutcome.SUCCESS:
        print(f"    FAILED: {render_result.error}")
        return
    print(f"    Rendered to: {render_result.output_path}")
    print(f"    Pages: {render_result.fidelity.rendered_pages}/{render_result.fidelity.total_pages}")
    print(f"    Visuals: {render_result.fidelity.rendered_visuals}/{render_result.fidelity.total_visuals}")

    # 5. Deploy to Fabric
    print(f"[5] Deploying to Fabric workspace...")
    try:
        deploy_to_workspace(Path(render_result.output_path))
        print(f"    Deployment completed!")
    except Exception as e:
        print(f"    DEPLOYMENT FAILED: {e}")
        return

    # 6. Refresh dataset
    print(f"[6] Triggering dataset refresh...")
    try:
        success = refresh_dataset(
            dataset_name="ExecutiveRetailPerformanceDashboard",
            wait=True,
            timeout=300,
        )
        if success:
            print(f"    Refresh completed successfully!")
        else:
            print(f"    Refresh failed or timed out")
    except Exception as e:
        print(f"    REFRESH FAILED: {e}")

    # 7. Verify
    print(f"\n[7] Verifying deployment...")
    from azure.identity import AzureCliCredential
    import requests

    cred = AzureCliCredential()
    token = cred.get_token("https://analysis.windows.net/powerbi/api/.default")
    headers = {"Authorization": f"Bearer {token.token}"}
    config = load_config()
    workspace_id = config["workspace_id"]
    base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"

    # Check datasets
    r = requests.get(f"{base}/datasets", headers=headers, timeout=30)
    if r.status_code == 200:
        datasets = r.json().get("value", [])
        print(f"    Datasets: {len(datasets)}")
        for d in datasets:
            print(f"      - {d['name']} (id={d['id']})")
    
    # Check reports
    r = requests.get(f"{base}/reports", headers=headers, timeout=30)
    if r.status_code == 200:
        reports = r.json().get("value", [])
        print(f"    Reports: {len(reports)}")
        for rpt in reports:
            print(f"      - {rpt['name']} (id={rpt['id']})")
            # Get pages
            r2 = requests.get(f"{base}/reports/{rpt['id']}/pages", headers=headers, timeout=30)
            if r2.status_code == 200:
                pages = r2.json().get("value", [])
                print(f"        Pages: {len(pages)}")
                for p in pages:
                    print(f"          - {p.get('displayName', p.get('name', '?'))}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
