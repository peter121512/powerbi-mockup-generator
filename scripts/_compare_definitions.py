"""Get and compare stored definitions of BareMinimal vs CRMmetricsng."""
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
headers = {"Authorization": f"Bearer {token}"}


def get_definition(report_id, name):
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{report_id}/getDefinition"
    r = requests.post(url, headers=headers, timeout=60)
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
                return result_r.json().get("definition", {}).get("parts", [])
    return []


# Get both
print("=== BareMinimal ===")
bare_parts = get_definition("37b92fa7-2025-47fa-8302-c8b6e42ef487", "BareMinimal")
bare_paths = sorted([p["path"] for p in bare_parts])
for p in bare_paths:
    print(f"  {p}")

print("\n=== CRMmetricsng ===")
crm_parts = get_definition("7604f125-4817-40a0-a2e7-c1b61671b8de", "CRMmetricsng")
crm_paths = sorted([p["path"] for p in crm_parts])
for p in crm_paths:
    print(f"  {p}")

# Compare report.json
print("\n=== report.json comparison ===")
for name, parts in [("BareMinimal", bare_parts), ("CRMmetricsng", crm_parts)]:
    for part in parts:
        if part["path"] == "definition/report.json":
            decoded = json.loads(base64.b64decode(part["payload"]).decode("utf-8"))
            print(f"\n{name}:")
            print(json.dumps(decoded, indent=2))

# Compare version.json
print("\n=== version.json comparison ===")
for name, parts in [("BareMinimal", bare_parts), ("CRMmetricsng", crm_parts)]:
    for part in parts:
        if part["path"] == "definition/version.json":
            decoded = json.loads(base64.b64decode(part["payload"]).decode("utf-8"))
            print(f"\n{name}:")
            print(json.dumps(decoded, indent=2))

# Compare definition.pbir
print("\n=== definition.pbir comparison ===")
for name, parts in [("BareMinimal", bare_parts), ("CRMmetricsng", crm_parts)]:
    for part in parts:
        if part["path"] == "definition.pbir":
            decoded = json.loads(base64.b64decode(part["payload"]).decode("utf-8"))
            print(f"\n{name}:")
            print(json.dumps(decoded, indent=2))
