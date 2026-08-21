"""V9: Embedded CustomVisual resource package with NO org/public declaration.

Theory: The consent overlay appears because we declared it as an org visual.
If we embed it as a private/file visual (CustomVisual resource package type),
it might bypass consent since the code is in the report itself.

The file-imported visual approach doesn't need consent — it's already "in" the report.
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
DIAG_NAME = "DiagV9Embedded"
evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == DIAG_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# Extract JS and CSS from pbiviz
pbiviz_path = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz")
pbiviz_bytes = pbiviz_path.read_bytes()
z = zipfile.ZipFile(io.BytesIO(pbiviz_bytes))
inner_json = json.loads(z.read(f"resources/{KPI_GUID}.pbiviz.json").decode("utf-8"))
js_content = inner_json["content"]["js"]
css_content = inner_json["content"].get("css", "")
capabilities = inner_json["capabilities"]
print(f"JS: {len(js_content)} chars, CSS: {len(css_content)} chars")

parts = []
def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})
def add_text_part(path, text):
    parts.append({"path": path, "payload": base64.b64encode(text.encode("utf-8")).decode("ascii"), "payloadType": "InlineBase64"})

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

# NO publicCustomVisuals, NO organizationCustomVisuals
# ONLY the CustomVisual resource package
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": KPI_GUID, "type": "CustomVisual", "items": [
            {"name": f"{KPI_GUID}.js", "type": "CustomVisualJavascript", "path": f"{KPI_GUID}.js"},
            {"name": f"{KPI_GUID}.css", "type": "CustomVisualsCss", "path": f"{KPI_GUID}.css"},
            {"name": f"{KPI_GUID}.json", "type": "CustomVisualMetadata", "path": f"{KPI_GUID}.json"},
        ]},
    ],
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

# Embed the visual resources at the correct paths
base = f"CustomVisuals/{KPI_GUID}/resources"
add_text_part(f"{base}/{KPI_GUID}.js", js_content)
add_text_part(f"{base}/{KPI_GUID}.css", css_content if css_content else "/* empty */")
# Full metadata with capabilities
metadata = {
    "visual": inner_json["visual"],
    "apiVersion": inner_json["apiVersion"],
    "capabilities": capabilities,
}
add_part(f"{base}/{KPI_GUID}.json", metadata)

# Deploy
print(f"Creating: {DIAG_NAME}")
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
            print(f"FAILED: {data.get('error', {}).get('message', '')[:300]}")
            sys.exit(1)

time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")

# Test with embed token
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
r2 = requests.get(f'{PBI_API_BASE}/groups/{workspace_id}/reports/{report_id}', headers={"Authorization": f"Bearer {token}"}, timeout=30)
dataset_id = r2.json().get('datasetId', '')
embed_token = _generate_embed_token(workspace_id, report_id, dataset_id, {"Authorization": f"Bearer {token}"})

html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PBI</title>
<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>
<style>*{{margin:0;padding:0}}body{{overflow:hidden}}#r{{width:1280px;height:720px}}</style>
</head><body><div id="r"></div><script>
const m=window['powerbi-client'].models;
const c={{type:'report',tokenType:m.TokenType.Embed,accessToken:'{token}',
embedUrl:'{embed_url}',id:'{report_id}',pageName:'p1',
settings:{{navContentPaneEnabled:false,filterPaneEnabled:false,
layoutType:m.LayoutType.Custom,customLayout:{{displayOption:m.DisplayOption.FitToPage,
pageSize:{{type:m.PageSizeType.Custom,width:1280,height:720}}}}}}}};
const r=powerbi.embed(document.getElementById('r'),c);
r.on('rendered',()=>{{document.title='RENDERED'}});
r.on('error',e=>{{document.title='ERROR:'+JSON.stringify(e.detail)}});
</script></body></html>""".format(token=embed_token, embed_url=embed_url, report_id=report_id)

html_path = evidence_dir / "_v9.html"
html_path.write_text(html, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    
    errors = []
    page.on('response', lambda resp: errors.append(f'{resp.status} {resp.url[:100]}') if resp.status >= 400 else None)
    
    page.goto(f'file:///{html_path.resolve()}')
    try:
        page.wait_for_function(
            "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
            timeout=30000)
    except Exception as e:
        print(f"Timeout: {e}")
    
    page.wait_for_timeout(5000)
    print(f"\nTitle: {page.title()}")
    
    # Check frames
    for frame in page.frames:
        if 'powerbi' in (frame.url or ''):
            try:
                kpi = frame.locator(".premium-kpi-wrapper").count()
                consent = frame.locator("text=To see this custom visual").count()
                print(f"  KPI elements: {kpi}, Consent: {consent}")
                if kpi > 0:
                    val = frame.locator(".premium-kpi-value").first.text_content()
                    lab = frame.locator(".premium-kpi-label").first.text_content()
                    print(f"  *** VALUE: '{val}' LABEL: '{lab}' ***")
            except:
                pass
    
    page.screenshot(path=str(evidence_dir / "screenshot_V9.png"))
    browser.close()

html_path.unlink(missing_ok=True)
print(f"\nErrors: {errors}")
