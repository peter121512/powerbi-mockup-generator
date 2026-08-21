"""Stage 07d-a: Deploy with correct custom visual registration approaches.

KEY FINDING: We were using 'publicCustomVisuals' (for AppSource) instead of either:
- 'organizationCustomVisuals' (for org-registered visuals)
- resourcePackages with type 'CustomVisual' (embedded in report)

This script tests BOTH approaches on the same report.
"""
import sys
import json
import base64
import time
import uuid
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
DIAG_NAME = "DiagBindingV3"
evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")
evidence_dir.mkdir(parents=True, exist_ok=True)

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == DIAG_NAME:
        print(f"Deleting existing: {item['id']}")
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# Read the pbiviz package and extract JS/CSS
pbiviz_path = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz")
pbiviz_bytes = pbiviz_path.read_bytes()
print(f"Custom visual package: {len(pbiviz_bytes)} bytes")

# Also read the built JS from the dist folder
import zipfile
import io
pbiviz_zip = zipfile.ZipFile(io.BytesIO(pbiviz_bytes))
print(f"Pbiviz contents: {pbiviz_zip.namelist()}")

parts = []
def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

def add_binary_part(path, data):
    parts.append({"path": path, "payload": base64.b64encode(data).decode("ascii"), "payloadType": "InlineBase64"})

add_part(".platform", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": DIAG_NAME},
    "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
})
add_part("definition.pbir", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byConnection": {"connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}"}},
})
add_part("definition/version.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
})

# report.json with BOTH approaches
# Approach 1: organizationCustomVisuals (for kpi1)
# Approach 2: resourcePackages with CustomVisual type (for kpi2)
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "organizationCustomVisuals": [{
        "name": KPI_GUID,
        "path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz",
    }],
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
    ],
    "settings": {"useStylableVisualContainerHeader": True, "useEnhancedTooltips": True},
})

add_part("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["diag1"], "activePageName": "diag1",
})
add_part("definition/pages/diag1/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "diag1", "displayName": "Diagnostic", "displayOption": "FitToPage", "height": 720, "width": 1280,
})

# Custom KPI visual using org visual approach 
add_part("definition/pages/diag1/visuals/kpi1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi1",
    "position": {"x": 50, "y": 50, "z": 1000, "width": 300, "height": 150, "tabOrder": 1000},
    "visual": {
        "visualType": KPI_GUID,
        "query": {
            "queryState": {
                "measure": {
                    "projections": [{
                        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                        "queryRef": "Fact.Total",
                        "active": True,
                    }]
                }
            }
        },
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# Native card for comparison (should always work)
add_part("definition/pages/diag1/visuals/nativecard/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "nativecard",
    "position": {"x": 50, "y": 250, "z": 1001, "width": 300, "height": 150, "tabOrder": 1001},
    "visual": {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
            "queryRef": "Fact.Total", "active": True,
        }]}}},
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# Include pbiviz file
add_binary_part(f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz", pbiviz_bytes)

# Deploy
print(f"\nCreating: {DIAG_NAME}")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": DIAG_NAME, "type": "Report", "definition": {"parts": parts}}, timeout=60)
print(f"Status: {r.status_code}")
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    op = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc or f"{FABRIC_API_BASE}/operations/{op}", headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("Created successfully!")
            break
        elif data.get("status") == "Failed":
            print(f"FAILED: {json.dumps(data, indent=2)}")
            sys.exit(1)
elif r.status_code == 201:
    print("Created (sync)!")
else:
    print(f"Error: {r.text[:500]}")
    sys.exit(1)

# Get report ID
time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")
print(f"Report URL: https://app.fabric.microsoft.com/groups/{workspace_id}/reports/{report_id}")

# Capture definition
print("\nFetching definition to verify what was stored...")
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
            definition = result.json().get("definition", {}).get("parts", [])
            pre_data = {}
            for part in definition:
                path = part["path"]
                decoded = base64.b64decode(part["payload"]).decode("utf-8")
                try:
                    pre_data[path] = json.loads(decoded)
                except json.JSONDecodeError:
                    pre_data[path] = f"[binary: {len(decoded)} bytes]"
            
            print(f"\nStored paths ({len(definition)}):")
            for path in sorted(pre_data.keys()):
                content = pre_data[path]
                if isinstance(content, str) and 'binary' in content:
                    print(f"  {path} -> {content}")
                else:
                    print(f"  {path} -> JSON")
            
            # Check report.json
            report_json = pre_data.get("definition/report.json", {})
            print(f"\norganizationCustomVisuals: {report_json.get('organizationCustomVisuals')}")
            print(f"publicCustomVisuals: {report_json.get('publicCustomVisuals')}")
            print(f"resourcePackages: {json.dumps(report_json.get('resourcePackages', []), indent=2)[:500]}")
            
            pre_path = evidence_dir / "PRE_v3_definition.json"
            pre_path.write_text(json.dumps(pre_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\nSaved: {pre_path}")
            break

print(f"\n=== Please check {DIAG_NAME} in view mode ===")
print("Does the custom KPI (top-left) show '600' or a dash '—'?")
print("The native card (bottom-left) should show 600.")
