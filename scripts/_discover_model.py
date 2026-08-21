"""Discover measures and columns in the Executive Retail semantic model."""
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

# Get measures
r = requests.post(
    f'{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
    headers=headers,
    json={'queries': [{'query': 'EVALUATE INFO.MEASURES()'}], 'serializerSettings': {'includeNulls': True}},
    timeout=30)
if r.status_code == 200:
    rows = r.json()['results'][0]['tables'][0]['rows']
    print("=== MEASURES ===")
    for row in rows:
        name = row.get("[Name]", "?")
        table_id = row.get("[TableID]", "?")
        print(f"  Table {table_id}: {name}")

# Get tables
print()
r = requests.post(
    f'{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
    headers=headers,
    json={'queries': [{'query': 'EVALUATE INFO.TABLES()'}], 'serializerSettings': {'includeNulls': True}},
    timeout=30)
if r.status_code == 200:
    rows = r.json()['results'][0]['tables'][0]['rows']
    print("=== TABLES ===")
    for row in rows:
        name = row.get("[Name]", "?")
        tid = row.get("[ID]", "?")
        print(f"  ID {tid}: {name}")

# Get key columns
print()
r = requests.post(
    f'{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries',
    headers=headers,
    json={'queries': [{'query': 'EVALUATE TOPN(40, INFO.COLUMNS(), [TableID], ASC, [ExplicitName], ASC)'}], 'serializerSettings': {'includeNulls': True}},
    timeout=30)
if r.status_code == 200:
    rows = r.json()['results'][0]['tables'][0]['rows']
    print("=== COLUMNS (sample) ===")
    for row in rows:
        name = row.get("[ExplicitName]", "?")
        table_id = row.get("[TableID]", "?")
        hidden = row.get("[IsHidden]", False)
        print(f"  Table {table_id}: {name} (hidden={hidden})")
