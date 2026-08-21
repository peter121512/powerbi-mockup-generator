"""Stage 07d-a: Deploy with full dataTransforms/queryMetadata to test auto-binding.

Hypothesis: native visuals work because PBI auto-generates dataTransforms when deploying
standard visualTypes, but custom visuals need explicit dataTransforms in the PBIR definition.
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
CHART_GUID = "premiumChart1A2B3C4D5E6F7A8B9C0D1E2F"
DIAG_NAME = "DiagBindingV2"
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

parts = []
def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

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
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "publicCustomVisuals": [KPI_GUID],
    "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
        {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
    ]}],
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

# CANDIDATE A: Custom KPI with full dataTransforms
# This includes the dataTransforms block that Power BI generates internally
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
        "dataTransforms": {
            "projectionActiveItems": {"measure": [{"queryRef": "Fact.Total", "active": True}]},
            "projectionOrdering": {"measure": [0]},
            "queryMetadata": {
                "Select": [{
                    "Restatement": "Total",
                    "Name": "Fact.Total",
                    "Type": 1
                }]
            },
            "selects": [{
                "queryName": "Fact.Total",
                "displayName": "Total",
                "roles": {"measure": True},
                "type": {"category": None, "underlyingType": 259},
                "expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
            }],
            "objects": {},
        },
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# CANDIDATE B: Custom KPI with dataTransforms + prototypeQuery
add_part("definition/pages/diag1/visuals/kpi2/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi2",
    "position": {"x": 400, "y": 50, "z": 1001, "width": 300, "height": 150, "tabOrder": 1001},
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
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "f", "Entity": "Fact", "Type": 0}],
                "Select": [{
                    "Measure": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": "Total"},
                    "Name": "Fact.Total",
                }],
            },
        },
        "dataTransforms": {
            "projectionActiveItems": {"measure": [{"queryRef": "Fact.Total", "active": True}]},
            "projectionOrdering": {"measure": [0]},
            "queryMetadata": {
                "Select": [{
                    "Restatement": "Total",
                    "Name": "Fact.Total",
                    "Type": 1
                }]
            },
            "selects": [{
                "queryName": "Fact.Total",
                "displayName": "Total",
                "roles": {"measure": True},
                "type": {"category": None, "underlyingType": 259},
                "expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
            }],
            "objects": {},
        },
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# CANDIDATE C: Minimal — just prototypeQuery, no dataTransforms
add_part("definition/pages/diag1/visuals/kpi3/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi3",
    "position": {"x": 750, "y": 50, "z": 1002, "width": 300, "height": 150, "tabOrder": 1002},
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
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "f", "Entity": "Fact", "Type": 0}],
                "Select": [{
                    "Measure": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": "Total"},
                    "Name": "Fact.Total",
                }],
            },
        },
        "objects": {},
        "drillFilterOtherVisuals": True,
    },
})

# CANDIDATE D: Native card for comparison (should always work)
add_part("definition/pages/diag1/visuals/nativecard/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "nativecard",
    "position": {"x": 50, "y": 250, "z": 1003, "width": 300, "height": 150, "tabOrder": 1003},
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

# Include pbiviz
pbiviz_path = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz")
if pbiviz_path.exists():
    pbiviz_bytes = pbiviz_path.read_bytes()
    parts.append({"path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz", "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})
    print(f"Including custom visual package: {len(pbiviz_bytes)} bytes")
else:
    print(f"WARNING: pbiviz not found at {pbiviz_path}")

# Deploy
print(f"Creating: {DIAG_NAME}")
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
            print(f"FAILED: {data}")
            sys.exit(1)
elif r.status_code == 201:
    print("Created (sync)!")
else:
    print(f"Error: {r.text}")
    sys.exit(1)

# Get report ID
time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")

# Capture PRE definition
print("\nFetching definition...")
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
            
            pre_path = evidence_dir / "PRE_v2_definition.json"
            pre_path.write_text(json.dumps(pre_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Saved definition: {pre_path}")
            
            # Show all visual definitions
            for path, content in sorted(pre_data.items()):
                if "visual" in path.lower() and "visual.json" in path:
                    name = path.split("/")[-2]
                    print(f"\n--- {name} ---")
                    if isinstance(content, dict):
                        vis = content.get("visual", {})
                        print(f"  visualType: {vis.get('visualType')}")
                        print(f"  has dataTransforms: {'dataTransforms' in vis}")
                        print(f"  has prototypeQuery: {'prototypeQuery' in vis.get('query', {})}")
                        query_state = vis.get("query", {}).get("queryState", {})
                        print(f"  queryState keys: {list(query_state.keys())}")
            break

print(f"\n=== DIAGNOSTIC ===")
print(f"Report URL: https://app.fabric.microsoft.com/groups/{workspace_id}/reports/{report_id}")
print(f"\nLayout:")
print(f"  Top-left (50,50):    kpi1 — dataTransforms only")
print(f"  Top-center (400,50): kpi2 — dataTransforms + prototypeQuery")
print(f"  Top-right (750,50):  kpi3 — prototypeQuery only")
print(f"  Bottom-left (50,250): native card — baseline")
print(f"\nPlease check which ones render data on first load (view mode, no editing)!")
