"""Check all Date columns and sample data."""
import sys, json, requests
sys.path.insert(0, "src")
from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
workspace_id = config["workspace_id"]

# Get all Date table columns via DMV
dax = """EVALUATE TOPN(5, SUMMARIZE('Date', 'Date'[DateKey], 'Date'[Month], 'Date'[Year], 'Date'[Quarter]), 'Date'[DateKey], ASC)"""
body = {"queries": [{"query": dax}]}
r = requests.post(f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{sm_id}/executeQueries",
                  headers=headers, json=body, timeout=30)
print(f"Status: {r.status_code}")
data = r.json()
if "results" in data:
    print(json.dumps(data["results"][0]["tables"][0], indent=2))
else:
    print(data.get("error", {}).get("message", "")[:300])
    # Try without DateKey
    dax2 = """EVALUATE TOPN(10, SUMMARIZE('Date', 'Date'[Month], 'Date'[Year], 'Date'[Quarter]), 'Date'[Year], ASC, 'Date'[Month], ASC)"""
    body2 = {"queries": [{"query": dax2}]}
    r2 = requests.post(f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{sm_id}/executeQueries",
                      headers=headers, json=body2, timeout=30)
    data2 = r2.json()
    if "results" in data2:
        print(json.dumps(data2["results"][0]["tables"][0], indent=2))
