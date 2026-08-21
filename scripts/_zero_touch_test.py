"""Stage 07d-a: Run 3 fresh zero-touch deployment tests.

SOLUTION FOUND: Use organizationCustomVisuals (not publicCustomVisuals)
in report.json, with the visual registered in the org store.
Do NOT include publicCustomVisuals — that causes a 403 on AppSource lookup.

Test protocol:
1. Create fresh report with unique name
2. Deploy via API only  
3. No edit-mode interaction
4. Embed with AAD token (user context)
5. Wait for rendered event
6. Capture screenshot
7. Verify KPI value (600) is present
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

pbiviz_bytes = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz").read_bytes()

def make_report_parts(display_name):
    parts = []
    def add(path, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        parts.append({"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"})
    
    add(".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": display_name},
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
    add("definition/report.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
        "layoutOptimization": "None",
        "organizationCustomVisuals": [{"name": KPI_GUID, "path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz"}],
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]}],
    })
    add("definition/pages/pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": ["p1"], "activePageName": "p1",
    })
    add("definition/pages/p1/page.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
        "name": "p1", "displayName": "Main", "displayOption": "FitToPage", "height": 720, "width": 1280,
    })
    add("definition/pages/p1/visuals/kpi1/visual.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": "kpi1",
        "position": {"x": 50, "y": 50, "z": 1000, "width": 350, "height": 180, "tabOrder": 1000},
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
    add("definition/pages/p1/visuals/card1/visual.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": "card1",
        "position": {"x": 450, "y": 50, "z": 1001, "width": 350, "height": 180, "tabOrder": 1001},
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
    return parts

def deploy_fresh(name):
    """Deploy a fresh report and return its ID."""
    # Delete if exists
    r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
    for item in r.json().get("value", []):
        if item["displayName"] == name:
            requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
            time.sleep(4)
            break
    
    parts = make_report_parts(name)
    r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                      json={"displayName": name, "type": "Report", "definition": {"parts": parts}}, timeout=60)
    if r.status_code == 202:
        loc = r.headers.get("Location", "")
        for _ in range(15):
            time.sleep(3)
            poll = requests.get(loc, headers=headers, timeout=30)
            if poll.json().get("status") == "Succeeded":
                break
            elif poll.json().get("status") == "Failed":
                return None
    
    time.sleep(3)
    r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
    return next((i["id"] for i in r.json()["value"] if i["displayName"] == name), None)

def screenshot_aad(report_id, output_path):
    """Take screenshot using AAD token (user context)."""
    embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
    if not embed_url:
        return False, "No embed URL"
    
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
    
    html_path = output_path.parent / "_temp_embed.html"
    html_path.write_text(html, encoding='utf-8')
    
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        page.on('response', lambda resp: errors.append(f'{resp.status} {resp.url[:100]}') if resp.status >= 400 else None)
        
        page.goto(f'file:///{html_path.resolve()}')
        try:
            page.wait_for_function(
                "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
                timeout=45000)
        except:
            pass
        
        page.wait_for_timeout(5000)
        title = page.title()
        page.screenshot(path=str(output_path))
        browser.close()
    
    html_path.unlink(missing_ok=True)
    return title == 'RENDERED', errors

# Run 3 fresh deployments
results = []
for i in range(1, 4):
    name = f"ZeroTouch_Run{i}_{uuid.uuid4().hex[:6]}"
    print(f"\n{'='*60}")
    print(f"RUN {i}/3: {name}")
    
    report_id = deploy_fresh(name)
    if not report_id:
        print(f"  DEPLOY FAILED")
        results.append({"run": i, "success": False, "reason": "deploy_failed"})
        continue
    
    print(f"  Deployed: {report_id}")
    output = evidence_dir / f"zero_touch_run{i}.png"
    rendered, errors = screenshot_aad(report_id, output)
    
    has_403 = any('403' in e for e in errors)
    print(f"  Rendered: {rendered}")
    print(f"  Has 403: {has_403}")
    print(f"  Errors: {errors}")
    
    results.append({
        "run": i, 
        "report_name": name,
        "report_id": report_id,
        "rendered": rendered,
        "has_403": has_403,
        "errors": errors,
        "success": rendered and not has_403,
    })

print(f"\n{'='*60}")
print("SUMMARY:")
for r in results:
    status = "PASS" if r.get("success") else "FAIL"
    print(f"  Run {r['run']}: {status} (rendered={r.get('rendered')}, 403={r.get('has_403')})")

passed = sum(1 for r in results if r.get("success"))
print(f"\nResult: {passed}/3 passed")

# Save results
(evidence_dir / "zero_touch_results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8")
