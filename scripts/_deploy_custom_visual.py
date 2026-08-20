"""Deploy a test report with the Premium KPI custom visual."""
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
workspace_name = config.get("workspace_name", "pbi")
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Semantic model ID for BareMinimal
sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
VISUAL_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"

# Read the .pbiviz file
pbiviz_path = Path("custom-visuals/premiumKPI/dist") / f"{VISUAL_GUID}.1.0.0.0.pbiviz"
pbiviz_bytes = pbiviz_path.read_bytes()
print(f"Custom visual: {pbiviz_path.name} ({len(pbiviz_bytes)} bytes)")

# Build report parts
parts = []

def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

def add_binary_part(path, data):
    parts.append({"path": path, "payload": base64.b64encode(data).decode("ascii"), "payloadType": "InlineBase64"})

# .platform
add_part(".platform", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": "CustomVisualTest"},
    "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
})

# definition.pbir
add_part("definition.pbir", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {
        "byConnection": {
            "connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_name};initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}"
        }
    },
})

# version.json
add_part("definition/version.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
})

# report.json — with publicCustomVisuals
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {
        "baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"},
    },
    "layoutOptimization": "None",
    "publicCustomVisuals": [VISUAL_GUID],
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": "RegisteredResources", "type": "RegisteredResources", "items": []},
    ],
    "settings": {
        "useStylableVisualContainerHeader": True,
        "defaultFilterActionIsDataFilter": True,
        "defaultDrillFilterOtherVisuals": True,
        "allowChangeFilterTypes": True,
        "allowInlineExploration": True,
        "useEnhancedTooltips": True,
    },
})

# pages.json
add_part("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["page1"],
    "activePageName": "page1",
})

# page.json
add_part("definition/pages/page1/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "page1",
    "displayName": "Custom Visual Test",
    "displayOption": "FitToPage",
    "height": 720,
    "width": 1280,
    "objects": {
        "background": [{"properties": {
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#F5F6F8'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}]
    },
})

# Custom KPI visual using the custom visual type
add_part("definition/pages/page1/visuals/kpi1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi1",
    "position": {"x": 50, "y": 100, "z": 1000, "width": 280, "height": 140, "tabOrder": 1000},
    "visual": {
        "visualType": VISUAL_GUID,
        "query": {
            "queryState": {
                "measure": {"projections": [{
                    "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                    "queryRef": "Fact.Total",
                    "active": True,
                }]}
            }
        },
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# Also add a standard card for comparison
add_part("definition/pages/page1/visuals/card1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "card1",
    "position": {"x": 380, "y": 100, "z": 1001, "width": 280, "height": 140, "tabOrder": 1001},
    "visual": {
        "visualType": "card",
        "query": {
            "queryState": {
                "Values": {"projections": [{
                    "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                    "queryRef": "Fact.Total",
                    "active": True,
                }]}
            }
        },
        "objects": {"general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Standard Card'"}}}}}]},
        "drillFilterOtherVisuals": True,
    },
})

# Add the custom visual .pbiviz in the CustomVisuals folder
add_binary_part(f"CustomVisuals/{VISUAL_GUID}.1.0.0.0.pbiviz", pbiviz_bytes)

# Deploy
print(f"Deploying with {len(parts)} parts...")
# Check if exists
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
existing_id = None
for item in r.json().get("value", []):
    if item["displayName"] == "CustomVisualTest":
        existing_id = item["id"]
        break

if existing_id:
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{existing_id}/updateDefinition"
    r = requests.post(url, headers=headers, json={"definition": {"parts": parts}}, timeout=60)
else:
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items"
    r = requests.post(url, headers=headers, json={"displayName": "CustomVisualTest", "type": "Report", "definition": {"parts": parts}}, timeout=60)

print(f"Status: {r.status_code}")
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    op = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc or f"{FABRIC_API_BASE}/operations/{op}", headers=headers, timeout=30)
        data = poll.json()
        print(f"  {data.get('status')}")
        if data.get("status") == "Succeeded":
            print("SUCCESS!")
            break
        elif data.get("status") == "Failed":
            print(f"FAILED: {data.get('error', {})}")
            break
elif r.status_code in (200, 201):
    print("SUCCESS!")
else:
    print(f"Error: {r.text[:500]}")
