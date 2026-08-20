"""List all workspace items and check report/model binding."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}"}

# List items via Fabric API
r = requests.get(
    f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items",
    headers=headers, timeout=30,
)
items = r.json().get("value", [])
print("=== Workspace Items ===")
for item in items:
    print(f"  {item['type']:20s} {item['displayName']:30s} {item['id']}")

# Check reports via PBI API
r = requests.get(
    f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports",
    headers=headers, timeout=30,
)
reports = r.json().get("value", [])
print("\n=== Reports (with datasetId binding) ===")
for rpt in reports:
    print(f"  {rpt['name']:30s} id={rpt['id']}")
    print(f"    datasetId={rpt.get('datasetId', 'NONE')}")
    print(f"    datasetWorkspaceId={rpt.get('datasetWorkspaceId', 'NONE')}")

# Check datasets
r = requests.get(
    f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets",
    headers=headers, timeout=30,
)
datasets = r.json().get("value", [])
print("\n=== Datasets ===")
for ds in datasets:
    print(f"  {ds['name']:30s} id={ds['id']}")
