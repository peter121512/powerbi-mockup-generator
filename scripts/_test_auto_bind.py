"""Deploy a FRESH custom visual report and test if it renders headlessly without manual touch."""
import sys
import json
import base64
import time
import uuid
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.critic.screenshot import capture_report_page

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
VISUAL_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"

fresh_name = "FreshAutoBindTest"
parts = []

def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

add_part(".platform", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": fresh_name},
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
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "publicCustomVisuals": [VISUAL_GUID],
    "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
        {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
    ]}],
    "settings": {"useStylableVisualContainerHeader": True, "useEnhancedTooltips": True},
})
add_part("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["p1"], "activePageName": "p1",
})
add_part("definition/pages/p1/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "p1", "displayName": "Auto Bind Test", "displayOption": "FitToPage", "height": 720, "width": 1280,
})
add_part("definition/pages/p1/visuals/kpi1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi1",
    "position": {"x": 50, "y": 50, "z": 1000, "width": 300, "height": 150, "tabOrder": 1000},
    "visual": {
        "visualType": VISUAL_GUID,
        "query": {"queryState": {"measure": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
            "queryRef": "Fact.Total", "active": True,
        }]}}},
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# Include pbiviz
pbiviz_bytes = Path(f"custom-visuals/premiumKPI/dist/{VISUAL_GUID}.1.0.0.0.pbiviz").read_bytes()
parts.append({"path": f"CustomVisuals/{VISUAL_GUID}.1.0.0.0.pbiviz", "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})

# Delete old if exists
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == fresh_name:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(3)
        print("Deleted old report")
        break

# Create fresh
print(f"Creating fresh report: {fresh_name}")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": fresh_name, "type": "Report", "definition": {"parts": parts}}, timeout=60)
print(f"Status: {r.status_code}")
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    op = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc or f"{FABRIC_API_BASE}/operations/{op}", headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("Created!")
            break
        elif data.get("status") == "Failed":
            print(f"Failed: {data.get('error', {})}")
            sys.exit(1)

# Find report ID
time.sleep(2)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == fresh_name), None)
print(f"Report ID: {report_id}")

# Headless screenshot - NO manual intervention
print("Capturing headless screenshot (no manual touch)...")
out_path = Path("docs/stages/07d-custom-visual-feasibility/auto-bind-test.png")
result = capture_report_page(report_id, "Auto Bind Test", out_path, timeout_ms=45000)
print(f"Outcome: {result.outcome.value} ({result.elapsed_seconds:.1f}s)")
if result.output_path:
    size = Path(result.output_path).stat().st_size
    print(f"Size: {size} bytes ({size//1024} KB)")
    if size > 5000:
        print(">>> LIKELY HAS CONTENT (>5KB) - AUTO BINDING MAY WORK!")
    else:
        print(">>> Likely empty/minimal (<5KB) - auto binding issue persists")
