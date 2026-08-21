"""Deploy using exact Desktop PBIP custom visual structure.

KEY DIFFERENCE FROM PREVIOUS ATTEMPTS:
- Desktop uses ResourcePackage type "CustomVisual" with single item type "CustomVisualMetadata"
- The item path points to the full pbiviz.json (with embedded JS/CSS)
- File stored at CustomVisuals/{GUID}/resources/{GUID}.pbiviz.json
- package.json at CustomVisuals/{GUID}/package.json
- NO publicCustomVisuals or organizationCustomVisuals declaration
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
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE, PBI_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url, _generate_embed_token
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
DIAG_NAME = "DiagDesktopMimicV1"
evidence_dir = Path("docs/stages/07d-b-trusted-custom-visual-delivery")
evidence_dir.mkdir(parents=True, exist_ok=True)

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == DIAG_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# Read the Desktop-authored files to replicate exactly
desktop_root = Path("custom-visuals/premiumKPI/dist/testReport.Report")

# Read the pbiviz.json (contains embedded JS/CSS + capabilities)
pbiviz_json_path = desktop_root / f"CustomVisuals/{KPI_GUID}/resources/{KPI_GUID}.pbiviz.json"
pbiviz_json_content = pbiviz_json_path.read_bytes()
print(f"pbiviz.json size: {len(pbiviz_json_content)} bytes")

# Read the package.json
package_json_content = (desktop_root / f"CustomVisuals/{KPI_GUID}/package.json").read_bytes()

parts = []
def add_part(path, content_bytes):
    parts.append({"path": path, "payload": base64.b64encode(content_bytes).decode("ascii"), "payloadType": "InlineBase64"})

def add_json_part(path, obj):
    add_part(path, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

add_json_part(".platform", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": DIAG_NAME},
    "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
})
add_json_part("definition.pbir", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byConnection": {"connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}"}},
})
add_json_part("definition/version.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
})

# Replicate EXACT Desktop report.json structure
add_json_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": KPI_GUID, "type": "CustomVisual", "items": [
            {"name": f"{KPI_GUID}.pbiviz.json", "type": "CustomVisualMetadata", "path": f"{KPI_GUID}.pbiviz.json"},
        ]},
    ],
    "settings": {"useStylableVisualContainerHeader": True, "useEnhancedTooltips": True},
})
add_json_part("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["p1"], "activePageName": "p1",
})
add_json_part("definition/pages/p1/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "p1", "displayName": "Main", "displayOption": "FitToPage", "height": 720, "width": 1280,
})

# Visual with nativeQueryRef (like Desktop does)
add_json_part("definition/pages/p1/visuals/kpi1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi1",
    "position": {"x": 100, "y": 100, "z": 0, "width": 350, "height": 200, "tabOrder": 0},
    "visual": {
        "visualType": KPI_GUID,
        "query": {
            "queryState": {
                "measure": {
                    "projections": [{
                        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
                        "queryRef": "Fact.Total",
                        "nativeQueryRef": "Total",
                    }]
                }
            },
        },
        "drillFilterOtherVisuals": True,
    },
})

# Native card for comparison
add_json_part("definition/pages/p1/visuals/card1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "card1",
    "position": {"x": 550, "y": 100, "z": 1, "width": 300, "height": 150, "tabOrder": 1},
    "visual": {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Total"}},
            "queryRef": "Fact.Total", "nativeQueryRef": "Total",
        }]}}},
        "drillFilterOtherVisuals": True,
    },
})

# Custom visual resources — EXACT Desktop structure
add_part(f"CustomVisuals/{KPI_GUID}/package.json", package_json_content)
add_part(f"CustomVisuals/{KPI_GUID}/resources/{KPI_GUID}.pbiviz.json", pbiviz_json_content)

# Deploy
print(f"\nCreating: {DIAG_NAME}")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": DIAG_NAME, "type": "Report", "definition": {"parts": parts}}, timeout=60)
print(f"Status: {r.status_code}")
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc, headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("Created!")
            break
        elif data.get("status") == "Failed":
            print(f"FAILED: {data.get('error', {}).get('message', '')[:400]}")
            sys.exit(1)
else:
    print(f"Error: {r.text[:300]}")
    sys.exit(1)

time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")

# Test with AAD token
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})

html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
    '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
    '<style>*{margin:0;padding:0}body{overflow:hidden}#r{width:1280px;height:720px}</style>'
    '</head><body><div id="r"></div><script>'
    'const m=window["powerbi-client"].models;'
    f'const c={{type:"report",tokenType:m.TokenType.Aad,accessToken:"{token}",'
    f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"p1",'
    'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
    'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
    'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
    'const r=powerbi.embed(document.getElementById("r"),c);'
    'r.on("rendered",()=>{document.title="RENDERED"});'
    'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
    '</script></body></html>'
)
html_path = evidence_dir / '_desktop_mimic.html'
html_path.write_text(html, encoding='utf-8')

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.on('response', lambda resp: errors.append(f'{resp.status} {resp.url[:120]}') if resp.status >= 400 else None)
    page.goto(f'file:///{html_path.resolve()}')
    try:
        page.wait_for_function(
            'document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")',
            timeout=30000)
    except Exception as e:
        print(f"Timeout: {e}")
    page.wait_for_timeout(5000)
    print(f"\nTitle: {page.title()}")
    
    for frame in page.frames:
        if 'powerbi' in (frame.url or ''):
            try:
                kpi = frame.locator('.premium-kpi-wrapper').count()
                consent = frame.locator('text=To see this custom visual').count()
                print(f"  KPI elements: {kpi}, Consent: {consent}")
                if kpi > 0:
                    val = frame.locator('.premium-kpi-value').first.text_content()
                    lab = frame.locator('.premium-kpi-label').first.text_content()
                    print(f"  *** SUCCESS: VALUE='{val}' LABEL='{lab}' ***")
            except:
                pass
    
    page.screenshot(path=str(evidence_dir / 'screenshot_desktop_mimic.png'))
    browser.close()

html_path.unlink(missing_ok=True)
print(f"\nErrors: {errors}")
