"""Get report definition from Fabric to see what was actually stored."""
import sys
import json
import base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}"}

# Get BareMinimal report definition
report_id = "37b92fa7-2025-47fa-8302-c8b6e42ef487"
report_name = "BareMinimal"

print(f"=== Getting definition for: {report_name} ({report_id}) ===\n")

# Try Fabric API - Get Item Definition
url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{report_id}/getDefinition"
r = requests.post(url, headers=headers, timeout=60)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    definition = r.json()
    parts = definition.get("definition", {}).get("parts", [])
    print(f"Parts count: {len(parts)}\n")
    for part in parts:
        path = part.get("path", "?")
        payload = part.get("payload", "")
        print(f"--- {path} ---")
        try:
            decoded = base64.b64decode(payload).decode("utf-8")
            # Try to pretty-print JSON
            try:
                obj = json.loads(decoded)
                print(json.dumps(obj, indent=2)[:2000])
            except json.JSONDecodeError:
                print(decoded[:2000])
        except Exception as e:
            print(f"  [binary/error: {e}]")
        print()
elif r.status_code == 202:
    print("Long running operation - checking...")
    location = r.headers.get("Location", "")
    op_id = r.headers.get("x-ms-operation-id", "")
    print(f"  Location: {location}")
    print(f"  Operation: {op_id}")
    # Poll
    import time
    for _ in range(10):
        time.sleep(2)
        poll_r = requests.get(location or f"https://api.fabric.microsoft.com/v1/operations/{op_id}", headers=headers, timeout=30)
        print(f"  Poll: {poll_r.status_code}")
        if poll_r.status_code == 200:
            data = poll_r.json()
            status = data.get("status", "")
            print(f"  Status: {status}")
            if status == "Succeeded":
                # Get result
                result_url = f"https://api.fabric.microsoft.com/v1/operations/{op_id}/result"
                result_r = requests.get(result_url, headers=headers, timeout=30)
                if result_r.status_code == 200:
                    definition = result_r.json()
                    parts = definition.get("definition", {}).get("parts", [])
                    print(f"\nParts count: {len(parts)}\n")
                    for part in parts:
                        path = part.get("path", "?")
                        payload = part.get("payload", "")
                        print(f"--- {path} ---")
                        try:
                            decoded = base64.b64decode(payload).decode("utf-8")
                            try:
                                obj = json.loads(decoded)
                                print(json.dumps(obj, indent=2)[:2000])
                            except json.JSONDecodeError:
                                print(decoded[:2000])
                        except Exception as e:
                            print(f"  [binary/error: {e}]")
                        print()
                break
else:
    print(f"Error: {r.text[:500]}")
