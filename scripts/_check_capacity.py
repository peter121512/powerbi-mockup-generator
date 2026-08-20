"""Check workspace info and query BareMinimal dataset."""
import sys
import json
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}"}

# Workspace details
print("=== Workspace Info ===")
r = requests.get(f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}", headers=headers, timeout=30)
ws = r.json()
print(json.dumps(ws, indent=2))

# Query BareMinimal
print("\n=== DAX query against BareMinimal ===")
dataset_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
dax_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
body = {
    "queries": [{"query": "EVALUATE ROW(\"val\", [Total])"}],
    "serializerSettings": {"includeNulls": True},
}
r = requests.post(dax_url, headers=headers, json=body, timeout=30)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    results = r.json().get("results", [{}])[0].get("tables", [{}])[0].get("rows", [])
    print(f"Result: {results}")
else:
    print(r.text[:500])

# Try to get report embed info which might reveal errors
print("\n=== Report embed info (BareMinimal) ===")
report_id = "37b92fa7-2025-47fa-8302-c8b6e42ef487"
r = requests.post(
    f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken",
    headers=headers,
    json={"accessLevel": "View"},
    timeout=30,
)
print(f"GenerateToken status: {r.status_code}")
if r.status_code != 200:
    print(r.text[:300])
else:
    print("Token generated OK (report is accessible)")
