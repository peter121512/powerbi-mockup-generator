"""Test YoY measure specifically."""
import requests
import yaml
from pathlib import Path
from azure.identity import AzureCliCredential

config = yaml.safe_load(open(Path.home() / ".pbi_gen" / "config.yaml"))
workspace_id = config["workspace_id"]
cred = AzureCliCredential()
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default")
headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"

r = requests.get(f"{base}/datasets", headers=headers, timeout=30)
datasets = r.json()["value"]
dataset = next(d for d in datasets if d["name"] == "ExecutiveRetailPerformanceDashboard")
dataset_id = dataset["id"]

queries = [
    ("PrevYearRevenue", 'EVALUATE ROW("Value", [PrevYearRevenue])'),
    ("YoYGrowthPct", 'EVALUATE ROW("Value", [YoYGrowthPct])'),
    ("TotalRevenue", 'EVALUATE ROW("Value", [TotalRevenue])'),
    ("StoreCount", 'EVALUATE ROW("Value", [StoreCount])'),
    ("AvgTransValue", 'EVALUATE ROW("Value", [AvgTransactionValue])'),
    ("AtRiskStores", 'EVALUATE ROW("Value", [AtRiskStoreCount])'),
    ("HighRiskPct", 'EVALUATE ROW("Value", [HighRiskPct])'),
    ("MarginYoYDiff", 'EVALUATE ROW("Value", [MarginYoYDiff])'),
    ("PrevYearMarginPct", 'EVALUATE ROW("Value", [PrevYearMarginPct])'),
    ("TotalCost", 'EVALUATE ROW("Value", [TotalCost])'),
    ("GrossMarginPct", 'EVALUATE ROW("Value", [GrossMarginPct])'),
]

print(f"Dataset: {dataset['name']} (id={dataset_id})\n")
for name, dax in queries:
    payload = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
    r = requests.post(
        f"{base}/datasets/{dataset_id}/executeQueries",
        headers=headers,
        json=payload,
        timeout=60,
    )
    if r.status_code == 200:
        result = r.json()
        tables = result.get("results", [{}])[0].get("tables", [])
        error = result.get("results", [{}])[0].get("error")
        if error:
            print(f"  {name}: DAX ERROR - {error.get('message', str(error)[:200])}")
        elif tables:
            rows = tables[0].get("rows", [])
            print(f"  {name}: {rows}")
        else:
            print(f"  {name}: No tables in result")
    else:
        print(f"  {name}: HTTP {r.status_code}")
        error_text = r.text[:500]
        print(f"    {error_text}")
