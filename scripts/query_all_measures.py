"""Query all 11 measures from the deployed model."""
import sys
from pathlib import Path
import requests
from azure.identity import AzureCliCredential
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

config_path = Path.home() / ".pbi_gen" / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)
workspace_id = config["workspace_id"]

cred = AzureCliCredential()
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default")
headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"

r = requests.get(f"{base}/datasets", headers=headers, timeout=30)
datasets = r.json().get("value", [])
dataset = next((d for d in datasets if d["name"] == "ExecutiveRetailPerformanceDashboard"), None)
dataset_id = dataset["id"]
print(f"Dataset: {dataset_id}\n")

measures = [
    ("TotalRevenue", "EVALUATE ROW(\"V\", [TotalRevenue])"),
    ("TotalCost", "EVALUATE ROW(\"V\", [TotalCost])"),
    ("GrossProfit", "EVALUATE ROW(\"V\", [GrossProfit])"),
    ("GrossMarginPct", "EVALUATE ROW(\"V\", [GrossMarginPct])"),
    ("PrevYearRevenue", "EVALUATE ROW(\"V\", [PrevYearRevenue])"),
    ("YoYGrowthPct", "EVALUATE ROW(\"V\", [YoYGrowthPct])"),
    ("PrevYearMarginPct", "EVALUATE ROW(\"V\", [PrevYearMarginPct])"),
    ("MarginYoYDiff", "EVALUATE ROW(\"V\", [MarginYoYDiff])"),
    ("RiskCount", "EVALUATE ROW(\"V\", [RiskCount])"),
    ("RevenueAtRisk", "EVALUATE ROW(\"V\", [RevenueAtRisk])"),
    ("PctRevenueAtRisk", "EVALUATE ROW(\"V\", [PctRevenueAtRisk])"),
]

results = {}
for name, dax in measures:
    payload = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
    r = requests.post(f"{base}/datasets/{dataset_id}/executeQueries", headers=headers, json=payload, timeout=60)
    if r.status_code == 200:
        resp = r.json()
        tables = resp.get("results", [{}])[0].get("tables", [])
        error = resp.get("results", [{}])[0].get("error")
        if error:
            print(f"  {name}: ERROR - {error.get('message', str(error)[:200])}")
            results[name] = "ERROR"
        elif tables:
            rows = tables[0].get("rows", [])
            val = rows[0].get("[V]") if rows else None
            print(f"  {name}: {val}")
            results[name] = val
        else:
            print(f"  {name}: NO DATA")
            results[name] = None
    else:
        err_text = r.text[:300]
        print(f"  {name}: HTTP {r.status_code} - {err_text}")
        results[name] = f"HTTP_{r.status_code}"

print(f"\n--- Summary ---")
passed = sum(1 for v in results.values() if v is not None and v != "ERROR" and not str(v).startswith("HTTP"))
print(f"Measures evaluating: {passed}/11")
