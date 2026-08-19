"""Query the deployed semantic model to verify measures evaluate correctly."""
import sys
from pathlib import Path
import requests
from azure.identity import AzureCliCredential
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    # Get credentials and config
    config_path = Path.home() / ".pbi_gen" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    workspace_id = config["workspace_id"]

    cred = AzureCliCredential()
    token = cred.get_token("https://analysis.windows.net/powerbi/api/.default")
    headers = {"Authorization": f"Bearer {token.token}"}
    base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"

    # Find our dataset
    r = requests.get(f"{base}/datasets", headers=headers, timeout=30)
    datasets = r.json().get("value", [])
    dataset = next((d for d in datasets if d["name"] == "ExecutiveRetailPerformanceDashboard"), None)
    if not dataset:
        print("ERROR: Dataset not found!")
        return
    dataset_id = dataset["id"]
    print(f"Dataset: {dataset['name']} (id={dataset_id})")

    # Execute DAX queries
    queries = [
        ("Sales Row Count", "EVALUATE ROW(\"Count\", COUNTROWS(Sales))"),
        ("Date Row Count", "EVALUATE ROW(\"Count\", COUNTROWS('Date'))"),
        ("Store Row Count", "EVALUATE ROW(\"Count\", COUNTROWS(Store))"),
        ("Region Row Count", "EVALUATE ROW(\"Count\", COUNTROWS(Region))"),
        ("Product Row Count", "EVALUATE ROW(\"Count\", COUNTROWS(Product))"),
        ("Total Revenue", "EVALUATE ROW(\"Value\", [TotalRevenue])"),
        ("Gross Margin %", "EVALUATE ROW(\"Value\", [GrossMarginPct])"),
        ("YoY Growth %", "EVALUATE ROW(\"Value\", [YoYGrowthPct])"),
        ("Region Members", "EVALUATE VALUES(Region[RegionName])"),
        ("Category Members", "EVALUATE VALUES(Product[CategoryName])"),
    ]

    print("\n=== DAX Query Results ===\n")
    for name, dax in queries:
        payload = {
            "queries": [{"query": dax}],
            "serializerSettings": {"includeNulls": True},
        }
        r = requests.post(
            f"{base}/datasets/{dataset_id}/executeQueries",
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if r.status_code == 200:
            result = r.json()
            tables = result.get("results", [{}])[0].get("tables", [])
            if tables:
                rows = tables[0].get("rows", [])
                if len(rows) <= 5:
                    print(f"  {name}: {rows}")
                else:
                    print(f"  {name}: {len(rows)} rows - first 3: {rows[:3]}")
            else:
                error = result.get("results", [{}])[0].get("error", {})
                print(f"  {name}: ERROR - {error}")
        else:
            print(f"  {name}: HTTP {r.status_code} - {r.text[:200]}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
