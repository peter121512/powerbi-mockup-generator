"""Check Date table columns in the semantic model."""
import sys, json, requests
sys.path.insert(0, "src")
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
workspace_id = config["workspace_id"]

# Try to query Quarter column
dax = """EVALUATE TOPN(5, SUMMARIZE('Date', 'Date'[Month], 'Date'[Year], 'Date'[Quarter]), 'Date'[Month], ASC)"""
body = {"queries": [{"query": dax}]}
r = requests.post(f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{sm_id}/executeQueries",
                  headers=headers, json=body, timeout=30)
print(f"Status: {r.status_code}")
data = r.json()
if "results" in data:
    print(json.dumps(data["results"][0]["tables"][0], indent=2))
elif "error" in data:
    print(f"Error: {data['error'].get('message', '')[:200]}")
    # Try without Quarter
    dax2 = """EVALUATE INFO.COLUMNS() ORDER BY [TableName], [ExplicitName]"""
    body2 = {"queries": [{"query": dax2}]}
    r2 = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{sm_id}/executeQueries",
                      headers=headers, json=body2, timeout=30)
    data2 = r2.json()
    if "results" in data2:
        for row in data2["results"][0]["tables"][0]["rows"]:
            if row.get("[TableName]") == "Date":
                print(f"  Date.{row.get('[ExplicitName]')}")
