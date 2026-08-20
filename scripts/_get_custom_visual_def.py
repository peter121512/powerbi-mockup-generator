"""Get the custom visual report definition after manual touch to diff binding metadata."""
import sys
import json
import base64
import time
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}"}

# Find CustomVisualTest report
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next(i["id"] for i in r.json()["value"] if i["displayName"] == "CustomVisualTest")
print(f"Report: {report_id}")

# Get definition
url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{report_id}/getDefinition"
r = requests.post(url, headers=headers, timeout=60)
if r.status_code == 202:
    location = r.headers.get("Location", "")
    op_id = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(2)
        poll = requests.get(location, headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            result = requests.get(f"{FABRIC_API_BASE}/operations/{op_id}/result", headers=headers, timeout=30)
            parts = result.json().get("definition", {}).get("parts", [])
            print(f"Parts: {len(parts)}")
            
            for part in parts:
                path = part["path"]
                decoded = base64.b64decode(part["payload"]).decode("utf-8")
                
                # Show visual definitions
                if "visual.json" in path:
                    print(f"\n=== {path} ===")
                    try:
                        obj = json.loads(decoded)
                        print(json.dumps(obj, indent=2))
                    except:
                        print(decoded[:500])
                
                # Show report.json custom visuals
                elif path == "definition/report.json":
                    obj = json.loads(decoded)
                    if "publicCustomVisuals" in obj:
                        print(f"\npublicCustomVisuals: {obj['publicCustomVisuals']}")
            break
