"""Discover all measures in the model."""
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

def dax(q):
    r = requests.post(f'{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
        headers=headers, json={'queries': [{'query': q}], 'serializerSettings': {'includeNulls': True}}, timeout=30)
    if r.status_code == 200:
        res = r.json()
        if 'error' not in res.get('results', [{}])[0]:
            return res['results'][0]['tables'][0]['rows']
    return None

measures = ['TotalRevenue', 'GrossMarginPct', 'TotalCost', 'NetRevenue', 'RevenueGrowth',
    'CustomerCount', 'TransactionCount', 'AverageBasketSize', 'UnitsSold', 'TotalQuantity',
    'RevenuePerStore', 'StoreCount', 'ProductCount', 'AvgUnitPrice', 'TotalProfit',
    'ProfitMargin', 'YoYGrowth', 'MoMGrowth', 'AvgTransactionValue', 'MarginPct',
    'OrderCount', 'BasketSize', 'RevenuePerTransaction', 'CostOfGoods', 'GrossProfit',
    'RevenuePY', 'RevenueYoY', 'CustomerGrowth', 'NewCustomers', 'RepeatCustomers',
    'Profit', 'COGS']

print("=== AVAILABLE MEASURES ===")
for m in measures:
    q = 'EVALUATE ROW("v", [' + m + '])'
    rows = dax(q)
    if rows:
        val = rows[0].get("[v]", "?")
        print(f"  {m} = {val}")

# Check for Region table or column
print("\n=== REGION DATA ===")
tables = ['Region', 'Geography', 'Regions', 'Location']
for t in tables:
    q = f"EVALUATE TOPN(3, ALL('{t}'))"
    rows = dax(q)
    if rows:
        print(f"  Table '{t}' columns: {list(rows[0].keys())}")
        break

# Store RegionID values
q = "EVALUATE DISTINCT(Store[RegionID])"
rows = dax(q)
if rows:
    print(f"  Store RegionID values: {[r.get('Store[RegionID]') for r in rows]}")

# Date MonthName values
q = "EVALUATE TOPN(3, DISTINCT(Date[MonthName]))"
rows = dax(q)
if rows:
    print(f"\n=== DATE MONTHS ===")
    print(f"  {[r.get('Date[MonthName]') for r in rows]}")
