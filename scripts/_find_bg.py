"""Find how page background is stored in an existing report."""
import json, base64, time, requests, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}'}

# Get ExecutiveRetailPerformanceDashboard
report_id = '0b8a63f1-915b-4f40-adde-87bdfc3f8396'
url = f'{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{report_id}/getDefinition'
r = requests.post(url, headers=headers, timeout=60)
loc = r.headers.get('Location', '')
op_id = r.headers.get('x-ms-operation-id', '')
for _ in range(10):
    time.sleep(2)
    poll = requests.get(loc, headers=headers, timeout=30)
    if poll.json().get('status') == 'Succeeded':
        result = requests.get(f'{FABRIC_API_BASE}/operations/{op_id}/result', headers=headers, timeout=30)
        parts = result.json().get('definition', {}).get('parts', [])
        for part in parts:
            if 'page.json' in part['path']:
                decoded = base64.b64decode(part['payload']).decode('utf-8')
                page = json.loads(decoded)
                objects = page.get('objects', {})
                if 'background' in objects:
                    print(f"FOUND in {part['path']}:")
                    print(json.dumps(objects['background'], indent=2))
                    print()
        break
