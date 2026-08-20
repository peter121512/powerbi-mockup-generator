"""Check if CRMmetricsng is PBIR or PBIR-Legacy, and also try to get report pages via PBI API."""
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

# Check CRMmetricsng format
report_id = "7604f125-4817-40a0-a2e7-c1b61671b8de"
print("=== CRMmetricsng definition format ===")
url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{report_id}/getDefinition"
r = requests.post(url, headers=headers, timeout=60)
if r.status_code == 202:
    location = r.headers.get("Location", "")
    op_id = r.headers.get("x-ms-operation-id", "")
    for _ in range(10):
        time.sleep(2)
        poll_r = requests.get(location, headers=headers, timeout=30)
        data = poll_r.json()
        if data.get("status") == "Succeeded":
            result_r = requests.get(f"https://api.fabric.microsoft.com/v1/operations/{op_id}/result", headers=headers, timeout=30)
            definition = result_r.json()
            parts = definition.get("definition", {}).get("parts", [])
            paths = [p["path"] for p in parts]
            print("Parts paths:")
            for p in sorted(paths):
                print(f"  {p}")
            has_def_folder = any("definition/" in p for p in paths)
            print(f"\nFormat: {'PBIR' if has_def_folder else 'PBIR-Legacy'}")
            break

# Now check report pages via PBI REST API for all our diagnostic reports
print("\n=== Report pages check ===")
for name, rid in [
    ("CRMmetricsng", "7604f125-4817-40a0-a2e7-c1b61671b8de"),
    ("BareMinimal", "37b92fa7-2025-47fa-8302-c8b6e42ef487"),
    ("DiagnosticMinimal", "3010758b-0691-4055-b6a1-9f3e57e9b134"),
    ("ExecutiveRetailPerformanceDashboard", "0b8a63f1-915b-4f40-adde-87bdfc3f8396"),
]:
    r = requests.get(
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{rid}/pages",
        headers=headers, timeout=30,
    )
    if r.status_code == 200:
        pages = r.json().get("value", [])
        page_names = [p.get("displayName", p.get("name", "?")) for p in pages]
        print(f"  {name}: {len(pages)} pages - {page_names}")
    else:
        print(f"  {name}: ERROR {r.status_code} - {r.text[:200]}")
