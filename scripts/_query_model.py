"""Query the Executive Retail model to find correct entity/property names."""
import requests, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, PBI_API_BASE

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
dataset_id = 'b731eda9-c402-42c4-ad27-f4641c7d6bcd'

def run_dax(query):
    r = requests.post(
        f'{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
        headers=headers,
        json={'queries': [{'query': query}], 'serializerSettings': {'includeNulls': True}},
        timeout=30)
    if r.status_code == 200:
        result = r.json()
        if 'error' in result.get('results', [{}])[0]:
            return None, result['results'][0]['error']['message']
        return result['results'][0]['tables'][0]['rows'], None
    return None, f"HTTP {r.status_code}"

# Test measures
rows, err = run_dax('EVALUATE ROW("rev", [TotalRevenue])')
print(f"TotalRevenue: {rows if rows else err}")

rows, err = run_dax('EVALUATE ROW("val", [AvgOrderValue])')
print(f"AvgOrderValue: {rows if rows else err}")

rows, err = run_dax('EVALUATE ROW("val", [TotalOrders])')
print(f"TotalOrders: {rows if rows else err}")

rows, err = run_dax('EVALUATE ROW("val", [GrossMarginPct])')
print(f"GrossMarginPct: {rows if rows else err}")

# Try other measure names
for name in ['AverageOrderValue', 'OrderCount', 'TotalTransactions', 'AvgBasketValue', 'TransactionCount']:
    rows, err = run_dax(f'EVALUATE ROW("val", [{name}])')
    if rows:
        print(f"  FOUND: [{name}] = {rows}")

# Check table/column names
print("\n--- Columns ---")
rows, err = run_dax('EVALUATE TOPN(5, ALL(Sales))')
if rows:
    print(f"Sales columns: {list(rows[0].keys())}")
elif err:
    print(f"Sales table error: {err[:100]}")

rows, err = run_dax('EVALUATE TOPN(2, ALL(Calendar))')
if rows:
    print(f"Calendar columns: {list(rows[0].keys())}")
elif err:
    # Try Date table
    rows, err = run_dax('EVALUATE TOPN(2, ALL(Date))')
    if rows:
        print(f"Date columns: {list(rows[0].keys())}")
    else:
        print(f"Calendar/Date error: {err[:100]}")

rows, err = run_dax('EVALUATE TOPN(2, ALL(Store))')
if rows:
    print(f"Store columns: {list(rows[0].keys())}")
elif err:
    print(f"Store error: {err[:100]}")
