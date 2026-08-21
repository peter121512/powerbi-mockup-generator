"""Quick verification: is the 600/Total showing from the custom KPI or native card?

The custom KPI has distinctive styling:
- Red/brown accent bar at top
- Uppercase label
- Larger value font

The native card has standard PBI styling.

Let's deploy with ONLY the custom KPI (no native card) to prove it works.
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
DIAG_NAME = "DiagKPIOnly"

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == DIAG_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

parts = []
def add_part(path, obj):
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})

pbiviz_bytes = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz").read_bytes()

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
# ONLY the custom KPI - no native card
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
parts.append({"path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz",
              "payload": base64.b64encode(pbiviz_bytes).decode("ascii"), "payloadType": "InlineBase64"})

# Deploy
print(f"Creating: {DIAG_NAME}")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": DIAG_NAME, "type": "Report", "definition": {"parts": parts}}, timeout=60)
if r.status_code == 202:
    loc = r.headers.get("Location", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc, headers=headers, timeout=30)
        if poll.json().get("status") == "Succeeded":
            print("Created!")
            break
        elif poll.json().get("status") == "Failed":
            print(f"FAILED: {poll.json()}")
            sys.exit(1)

time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")

# Screenshot with AAD token
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})

html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PBI</title>
<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>
<style>*{{margin:0;padding:0}}body{{overflow:hidden}}#r{{width:1280px;height:720px}}</style>
</head><body><div id="r"></div><script>
const m=window['powerbi-client'].models;
const c={{type:'report',tokenType:m.TokenType.Aad,accessToken:'{token}',
embedUrl:'{embed_url}',id:'{report_id}',pageName:'p1',
settings:{{navContentPaneEnabled:false,filterPaneEnabled:false,
layoutType:m.LayoutType.Custom,customLayout:{{displayOption:m.DisplayOption.FitToPage,
pageSize:{{type:m.PageSizeType.Custom,width:1280,height:720}}}}}}}};
const r=powerbi.embed(document.getElementById('r'),c);
r.on('rendered',()=>{{document.title='RENDERED'}});
r.on('error',e=>{{document.title='ERROR:'+JSON.stringify(e.detail)}});
</script></body></html>""".format(token=token, embed_url=embed_url, report_id=report_id)

html_path = evidence_dir / "_kpionly.html"
html_path.write_text(html, encoding='utf-8')

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = ctx.new_page()
    page.on('response', lambda resp: errors.append(f'{resp.status} {resp.url[:120]}') if resp.status >= 400 else None)
    page.goto(f'file:///{html_path.resolve()}')
    try:
        page.wait_for_function(
            "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
            timeout=45000)
    except Exception as e:
        print(f"Timeout: {e}")
    page.wait_for_timeout(5000)
    title = page.title()
    print(f"Title: {title}")
    page.screenshot(path=str(evidence_dir / "screenshot_KPIOnly.png"))
    browser.close()

html_path.unlink(missing_ok=True)
print(f"Errors: {errors}")
print("Check screenshot_KPIOnly.png")
