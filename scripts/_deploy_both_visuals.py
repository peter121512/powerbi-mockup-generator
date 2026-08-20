"""Deploy report with both Premium KPI + Premium Chart custom visuals."""
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
KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
CHART_GUID = "premiumChart1A2B3C4D5E6F7A8B9C0D1E2F"

parts = []
def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

fresh_name = "BothVisualsNew"

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
    "publicCustomVisuals": [KPI_GUID, CHART_GUID],
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
    "name": "p1", "displayName": "Both Visuals", "displayOption": "FitToPage",
    "height": 720, "width": 1280,
    "objects": {"background": [{"properties": {
        "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#F5F6F8'"}}}}},
        "transparency": {"expr": {"Literal": {"Value": "0D"}}},
    }}]},
})
# KPI
add_part("definition/pages/p1/visuals/kpi1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi1",
    "position": {"x": 50, "y": 30, "z": 1000, "width": 280, "height": 130, "tabOrder": 1000},
    "visual": {
        "visualType": KPI_GUID,
        "query": {"queryState": {"measure": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
            "queryRef": "Fact.Total", "active": True,
        }]}}},
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})
# Chart
add_part("definition/pages/p1/visuals/chart1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "chart1",
    "position": {"x": 50, "y": 180, "z": 1001, "width": 900, "height": 420, "tabOrder": 1001},
    "visual": {
        "visualType": CHART_GUID,
        "query": {"queryState": {
            "category": {"projections": [{
                "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "ID"}},
                "queryRef": "Fact.ID", "active": True,
            }]},
            "values": {"projections": [{
                "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                "queryRef": "Fact.Total", "active": True,
            }]},
        }},
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# Include both pbiviz files
kpi_bytes = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz").read_bytes()
chart_bytes = Path(f"custom-visuals/premiumChart/dist/{CHART_GUID}.1.0.0.0.pbiviz").read_bytes()
parts.append({"path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz", "payload": base64.b64encode(kpi_bytes).decode("ascii"), "payloadType": "InlineBase64"})
parts.append({"path": f"CustomVisuals/{CHART_GUID}.1.0.0.0.pbiviz", "payload": base64.b64encode(chart_bytes).decode("ascii"), "payloadType": "InlineBase64"})

# Delete existing and create fresh
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
existing_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == fresh_name), None)
if existing_id:
    print(f"Deleting existing: {existing_id}")
    requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{existing_id}", headers=headers, timeout=30)
    time.sleep(3)

r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": fresh_name, "type": "Report", "definition": {"parts": parts}}, timeout=60)

print(f"Deploy: {r.status_code}")
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    op = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc or f"{FABRIC_API_BASE}/operations/{op}", headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("OK!")
            break
        elif data.get("status") == "Failed":
            print(f"FAILED: {data.get('error', {})}")
            sys.exit(1)

# Screenshot
time.sleep(2)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == fresh_name), None)
print(f"Report: {report_id}")

result = capture_report_page(report_id, "Both Visuals",
    Path("docs/stages/07d-custom-visual-feasibility/both-visuals-test.png"), timeout_ms=45000)
print(f"Screenshot: {result.outcome.value} ({result.elapsed_seconds:.1f}s)")
if result.output_path:
    size = Path(result.output_path).stat().st_size
    print(f"Size: {size//1024} KB")
