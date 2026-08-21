"""List all reports in workspace."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import requests
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}'}

r = requests.get(f'{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report', headers=headers, timeout=30)
for rep in sorted(r.json().get('value', []), key=lambda x: x['displayName']):
    print(f"  {rep['displayName']}: {rep['id']}")
