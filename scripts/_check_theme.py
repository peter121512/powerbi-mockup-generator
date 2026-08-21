"""Check what theme was actually stored in the deployed report."""
import sys, json, base64, time, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}'}

report_id = '657429b7-c3ff-4f40-8929-88c99ca92ff6'
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
        print(f"Parts ({len(parts)}):")
        for part in parts:
            print(f"  {part['path']}")
            if 'Dark' in part['path'] or 'theme' in part['path'].lower():
                decoded = base64.b64decode(part['payload']).decode('utf-8')
                theme = json.loads(decoded)
                print(f"  THEME CONTENT:")
                print(json.dumps(theme, indent=2)[:2000])
        break
