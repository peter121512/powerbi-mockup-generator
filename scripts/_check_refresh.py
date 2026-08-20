"""Check refresh history and verify data still exists."""
import sys
import json
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, PBI_API_BASE

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}"}

dataset_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"

# Check refresh history
r = requests.get(
    f"{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/refreshes?$top=5",
    headers=headers, timeout=30,
)
refreshes = r.json().get("value", [])
print("Last refreshes:")
for ref in refreshes[:5]:
    print(f"  {ref.get('startTime', '?')} - {ref.get('status', '?')} - {ref.get('refreshType', '?')}")

# Verify data via DAX
print("\nDAX query:")
dax_url = f"{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
body = {
    "queries": [{"query": 'EVALUATE ROW("rev", [TotalRevenue], "rows", COUNTROWS(Sales))'}],
    "serializerSettings": {"includeNulls": True},
}
r2 = requests.post(dax_url, headers=headers, json=body, timeout=30)
if r2.status_code == 200:
    rows = r2.json().get("results", [{}])[0].get("tables", [{}])[0].get("rows", [])
    print(f"  TotalRevenue + Sales rows: {rows}")
else:
    print(f"  Error: {r2.status_code} {r2.text[:200]}")
