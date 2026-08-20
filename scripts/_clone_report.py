"""Clone the working CRMmetricsng report definition to a new name to test if tenant can render PBIR."""
import sys
import json
import base64
import time
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Step 1: Get CRMmetricsng definition
source_report_id = "7604f125-4817-40a0-a2e7-c1b61671b8de"
print("Getting CRMmetricsng definition...")
url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{source_report_id}/getDefinition"
r = requests.post(url, headers=headers, timeout=60)

parts = []
if r.status_code == 202:
    location = r.headers.get("Location", "")
    op_id = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(2)
        poll_r = requests.get(location, headers=headers, timeout=30)
        data = poll_r.json()
        if data.get("status") == "Succeeded":
            result_r = requests.get(
                f"https://api.fabric.microsoft.com/v1/operations/{op_id}/result",
                headers=headers, timeout=30,
            )
            definition = result_r.json()
            parts = definition.get("definition", {}).get("parts", [])
            break

if not parts:
    print("Failed to get definition!")
    sys.exit(1)

print(f"Got {len(parts)} parts")

# Step 2: Modify .platform to new name and new logicalId
import uuid
for part in parts:
    if part["path"] == ".platform":
        decoded = json.loads(base64.b64decode(part["payload"]).decode("utf-8"))
        decoded["metadata"]["displayName"] = "CloneTest"
        decoded["config"]["logicalId"] = str(uuid.uuid4())
        part["payload"] = base64.b64encode(json.dumps(decoded).encode("utf-8")).decode("ascii")
    # Update definition.pbir to point to the same semantic model
    # (it already points to CRMmetricsng model, which is fine for testing)

# Step 3: Create new report via Fabric API
print("Creating CloneTest report...")
create_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
body = {
    "displayName": "CloneTest",
    "type": "Report",
    "definition": {"parts": parts},
}
r = requests.post(create_url, headers=headers, json=body, timeout=60)
print(f"Create status: {r.status_code}")
if r.status_code in (200, 201, 202):
    if r.status_code == 202:
        # Long running
        loc = r.headers.get("Location", "")
        op = r.headers.get("x-ms-operation-id", "")
        print(f"  Long-running op: {op}")
        for _ in range(15):
            time.sleep(2)
            poll = requests.get(loc or f"https://api.fabric.microsoft.com/v1/operations/{op}", headers=headers, timeout=30)
            pdata = poll.json()
            print(f"  Status: {pdata.get('status')}")
            if pdata.get("status") in ("Succeeded", "Failed"):
                break
    else:
        result = r.json()
        print(f"Created: {result.get('id', '?')}")
    print("\nDone! Open 'CloneTest' in the workspace to verify it loads.")
else:
    print(f"Error: {r.text[:500]}")
