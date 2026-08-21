"""Get definition of a report where the custom visual was manually activated."""
import sys
import json
import base64
import time
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

def get_definition(report_id, label):
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{report_id}/getDefinition"
    r = requests.post(url, headers=headers, timeout=60)
    if r.status_code == 202:
        loc = r.headers.get("Location", "")
        op_id = r.headers.get("x-ms-operation-id", "")
        for _ in range(15):
            time.sleep(2)
            poll = requests.get(loc, headers=headers, timeout=30)
            data = poll.json()
            if data.get("status") == "Succeeded":
                result = requests.get(f"{FABRIC_API_BASE}/operations/{op_id}/result", headers=headers, timeout=30)
                parts = result.json().get("definition", {}).get("parts", [])
                definition = {}
                for part in parts:
                    decoded = base64.b64decode(part["payload"]).decode("utf-8", errors="replace")
                    try:
                        definition[part["path"]] = json.loads(decoded)
                    except json.JSONDecodeError:
                        definition[part["path"]] = f"[binary/text: {len(decoded)} chars]"
                
                out_path = evidence_dir / f"definition_{label}.json"
                out_path.write_text(json.dumps(definition, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"\n{label}: saved to {out_path} ({len(parts)} parts)")
                return definition
    print(f"{label}: FAILED to get definition (status={r.status_code})")
    return None

# Get BothVisualsNew - this was manually activated 
both_def = get_definition("6e10467f-59c0-4a65-b642-bb48be541220", "BothVisualsNew_activated")

# Get our fresh DiagKPIOnly - consent blocked
diag_def = get_definition("176c1028-e1ab-428a-a5f3-9e6419146d3f", "DiagKPIOnly_fresh")

if both_def and diag_def:
    # Compare report.json specifically
    print("\n\n=== BothVisualsNew report.json ===")
    both_report = both_def.get("definition/report.json", {})
    print(json.dumps(both_report, indent=2)[:3000])
    
    print("\n\n=== DiagKPIOnly report.json ===")
    diag_report = diag_def.get("definition/report.json", {})
    print(json.dumps(diag_report, indent=2)[:3000])
    
    # Compare paths 
    print("\n\n=== Paths in BothVisualsNew ===")
    for p in sorted(both_def.keys()):
        print(f"  {p}")
    
    print("\n=== Paths in DiagKPIOnly ===")
    for p in sorted(diag_def.keys()):
        print(f"  {p}")
