"""Stage 07d-a: Deploy V6 — multiple approaches in parallel.

Test 3 different resource package configurations to find what actually loads the visual:
A) CustomVisual resource package pointing to pbiviz file in RegisteredResources
B) The pbiviz at the PBIP CustomVisuals/ root level (as Desktop does)
C) No resource package at all — just publicCustomVisuals + CustomVisuals/ file

Also try: what if we DON'T declare it in report.json at all, and just include the .pbiviz?
"""
import sys
import json
import base64
import time
import uuid
import zipfile
import io
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
evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

# Read pbiviz
pbiviz_path = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz")
pbiviz_bytes = pbiviz_path.read_bytes()

# Extract full pbiviz.json (with embedded JS/CSS)
z = zipfile.ZipFile(io.BytesIO(pbiviz_bytes))
inner_json_bytes = z.read(f"resources/{KPI_GUID}.pbiviz.json")

def delete_report(name):
    r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
    for item in r.json().get("value", []):
        if item["displayName"] == name:
            requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
            time.sleep(3)
            return True
    return False

def deploy_report(name, parts):
    print(f"\n{'='*60}")
    print(f"Deploying: {name}")
    r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                      json={"displayName": name, "type": "Report", "definition": {"parts": parts}}, timeout=60)
    if r.status_code == 202:
        loc = r.headers.get("Location", "")
        op = r.headers.get("x-ms-operation-id", "")
        for _ in range(15):
            time.sleep(3)
            poll = requests.get(loc or f"{FABRIC_API_BASE}/operations/{op}", headers=headers, timeout=30)
            data = poll.json()
            if data.get("status") == "Succeeded":
                print(f"  SUCCESS")
                time.sleep(2)
                r2 = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
                report_id = next((i["id"] for i in r2.json()["value"] if i["displayName"] == name), None)
                return report_id
            elif data.get("status") == "Failed":
                err = data.get("error", {}).get("message", "unknown")
                print(f"  FAILED: {err[:200]}")
                return None
    elif r.status_code == 201:
        r2 = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
        return next((i["id"] for i in r2.json()["value"] if i["displayName"] == name), None)
    else:
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        return None

def make_base_parts(report_json_content):
    """Create base definition parts with given report.json content."""
    parts = []
    def add(path, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})
    
    add(".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "placeholder"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    })
    add("definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byConnection": {"connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}"}},
    })
    add("definition/version.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    add("definition/report.json", report_json_content)
    add("definition/pages/pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": ["diag1"], "activePageName": "diag1",
    })
    add("definition/pages/diag1/page.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
        "name": "diag1", "displayName": "Diagnostic", "displayOption": "FitToPage", "height": 720, "width": 1280,
    })
    add("definition/pages/diag1/visuals/kpi1/visual.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": "kpi1",
        "position": {"x": 50, "y": 50, "z": 1000, "width": 300, "height": 150, "tabOrder": 1000},
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
    add("definition/pages/diag1/visuals/nativecard/visual.json", {
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
    return parts

# ============================================================
# V6A: publicCustomVisuals + CustomVisuals/ pbiviz at root 
# (original approach that "worked" before with manual touch)
# ============================================================
delete_report("DiagV6A")
parts_a = make_base_parts({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "publicCustomVisuals": [KPI_GUID],
    "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
        {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
    ]}],
})
parts_a.append({"path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz",
                "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})
id_a = deploy_report("DiagV6A", parts_a)

# ============================================================
# V6B: RegisteredResources with the FULL pbiviz.json (not .pbiviz zip)
# This is the actual visual code file as a registered resource
# ============================================================
delete_report("DiagV6B")
parts_b = make_base_parts({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "publicCustomVisuals": [KPI_GUID],
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": "RegisteredResources", "type": "RegisteredResources", "items": [
            {"name": f"{KPI_GUID}.pbiviz", "type": "CustomVisualMetadata", "path": f"{KPI_GUID}.pbiviz"},
        ]},
    ],
})
# Store the .pbiviz zip in RegisteredResources
parts_b.append({"path": f"StaticResources/RegisteredResources/{KPI_GUID}.pbiviz",
                "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})
# Also store at CustomVisuals/ just in case  
parts_b.append({"path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz",
                "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})
id_b = deploy_report("DiagV6B", parts_b)

# ============================================================
# V6C: Use a well-known AppSource custom visual GUID to test if
# the publicCustomVisuals mechanism works at all
# Let's use "advancedCardAAE0C72C204B4FD5A42B0CEAF2D33B0B" (hypothetical)
# Actually let's test with our KPI but use OrganizationalStoreCustomVisual resource type
# ============================================================
delete_report("DiagV6C")
parts_c = make_base_parts({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "publicCustomVisuals": [KPI_GUID],
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": KPI_GUID, "type": "OrganizationalStoreCustomVisual", "items": [
            {"name": f"{KPI_GUID}.pbiviz", "type": "CustomVisualMetadata", "path": f"{KPI_GUID}.pbiviz"},
        ]},
    ],
})
parts_c.append({"path": f"CustomVisuals/{KPI_GUID}/{KPI_GUID}.pbiviz",
                "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})
id_c = deploy_report("DiagV6C", parts_c)

# Print summary
print(f"\n{'='*60}")
print("RESULTS:")
print(f"  V6A (publicCustomVisuals + CustomVisuals/): {id_a}")
print(f"  V6B (RegisteredResources + publicCustomVisuals): {id_b}")
print(f"  V6C (OrganizationalStoreCustomVisual resource): {id_c}")
print()
# Screenshot each one that succeeded
import sys
sys.path.insert(0, 'src')
from pbi_gen.critic.screenshot import capture_report_page

for label, rid in [("V6A", id_a), ("V6B", id_b), ("V6C", id_c)]:
    if rid:
        out = evidence_dir / f"screenshot_{label}.png"
        result = capture_report_page(rid, "diag1", out)
        print(f"  {label}: {result.outcome.value} - errors: {result.console_errors}")
