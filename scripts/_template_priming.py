"""Template priming approach: 
1. Clone a pre-activated report (bypasses consent)
2. Update definition to use organizationCustomVisuals (loads code from org store)
3. Test if visual renders with data
"""
import sys
import json
import base64
import time
import uuid
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE, PBI_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")
DIAG_NAME = "DiagTemplatePrimed"

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == DIAG_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# Step 1: Clone BothVisualsNew (which has pre-activated consent)
source_id = "6e10467f-59c0-4a65-b642-bb48be541220"
r = requests.post(f"{PBI_API_BASE}/groups/{workspace_id}/reports/{source_id}/Clone",
                  headers=headers, json={"name": DIAG_NAME, "targetWorkspaceId": workspace_id}, timeout=30)
print(f"Clone: {r.status_code}")
clone_id = r.json().get("id")
print(f"Clone ID: {clone_id}")
time.sleep(3)

# Step 2: Update the definition to use organizationCustomVisuals
pbiviz_bytes = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz").read_bytes()

parts = []
def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

add_part("definition.pbir", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byConnection": {"connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}"}},
})
add_part("definition/version.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
})
# Use organizationCustomVisuals instead of publicCustomVisuals
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "organizationCustomVisuals": [{"name": KPI_GUID, "path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz"}],
    "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
        {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
    ]}],
})
add_part("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["p1"], "activePageName": "p1",
})
add_part("definition/pages/p1/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "p1", "displayName": "Main", "displayOption": "FitToPage", "height": 720, "width": 1280,
})
add_part("definition/pages/p1/visuals/kpi1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "kpi1",
    "position": {"x": 100, "y": 100, "z": 1000, "width": 400, "height": 200, "tabOrder": 1000},
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
add_part("definition/pages/p1/visuals/card1/visual.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": "card1",
    "position": {"x": 550, "y": 100, "z": 1001, "width": 300, "height": 150, "tabOrder": 1001},
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
parts.append({"path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz",
              "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})

# Update definition
print(f"\nUpdating definition...")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{clone_id}/updateDefinition",
                  headers=headers, json={"definition": {"parts": parts}}, timeout=60)
print(f"Update status: {r.status_code}")
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc, headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("Updated!")
            break
        elif data.get("status") == "Failed":
            print(f"FAILED: {data.get('error', {}).get('message', '')[:300]}")
            sys.exit(1)

# Step 3: Test
time.sleep(3)
embed_url = _get_embed_url(workspace_id, clone_id, {"Authorization": f"Bearer {token}"})

html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
    '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
    '<style>*{margin:0;padding:0}body{overflow:hidden}#r{width:1280px;height:720px}</style>'
    '</head><body><div id="r"></div><script>'
    'const m=window["powerbi-client"].models;'
    f'const c={{type:"report",tokenType:m.TokenType.Aad,accessToken:"{token}",'
    f'embedUrl:"{embed_url}",id:"{clone_id}",pageName:"p1",'
    'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
    'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
    'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
    'const r=powerbi.embed(document.getElementById("r"),c);'
    'r.on("rendered",()=>{document.title="RENDERED"});'
    'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
    '</script></body></html>'
)
html_path = evidence_dir / '_template.html'
html_path.write_text(html, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.goto(f'file:///{html_path.resolve()}')
    try:
        page.wait_for_function(
            'document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")',
            timeout=30000)
    except:
        pass
    page.wait_for_timeout(5000)
    print(f"\nTitle: {page.title()}")
    for frame in page.frames:
        if 'powerbi' in (frame.url or ''):
            try:
                kpi = frame.locator('.premium-kpi-wrapper').count()
                consent = frame.locator('text=To see this custom visual').count()
                print(f"  KPI: {kpi}, Consent: {consent}")
                if kpi > 0:
                    val = frame.locator('.premium-kpi-value').first.text_content()
                    lab = frame.locator('.premium-kpi-label').first.text_content()
                    print(f"  *** VALUE='{val}' LABEL='{lab}' ***")
            except:
                pass
    page.screenshot(path=str(evidence_dir / 'screenshot_template_primed.png'))
    browser.close()
html_path.unlink(missing_ok=True)
