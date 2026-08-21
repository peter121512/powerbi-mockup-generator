"""V8: Pure organizationCustomVisuals (no publicCustomVisuals fallback).

From diagnostics:
- V3 (organizationCustomVisuals only) had NO 403 on resourcePackageItem
- V6A/V7 (publicCustomVisuals) had 403 on resourcePackageItem 
- V3 showed "add it to this report" message visually

Hypothesis: The "add to report" is a UI consent overlay that might not appear
in embed mode with the right token type. Let's test with:
1. aad token (not embed token) 
2. longer wait time
3. Check if the visual actually renders behind the overlay
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
from pbi_gen.critic.screenshot import _generate_embed_token, _get_embed_url, EMBED_HTML_TEMPLATE
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"
KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
DIAG_NAME = "DiagV8Pure"
evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

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
# ONLY organizationCustomVisuals — no publicCustomVisuals
add_part("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "organizationCustomVisuals": [{
        "name": KPI_GUID,
        "path": f"CustomVisuals/{KPI_GUID}.1.0.0.0.pbiviz",
    }],
    "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
        {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
    ]}],
})
add_part("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["diag1"], "activePageName": "diag1",
})
add_part("definition/pages/diag1/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "diag1", "displayName": "Diagnostic", "displayOption": "FitToPage", "height": 720, "width": 1280,
})
add_part("definition/pages/diag1/visuals/kpi1/visual.json", {
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
add_part("definition/pages/diag1/visuals/nativecard/visual.json", {
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

# Include pbiviz for completeness
pbiviz_bytes = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz").read_bytes()
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
            print(f"FAILED: {poll.json().get('error', {}).get('message', '')[:300]}")
            sys.exit(1)

time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")

# Now try BOTH embed approaches:
# 1. Embed token (what our screenshot tool uses)
# 2. AAD token directly (user's own token - "embed for your organization" pattern)

embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
r2 = requests.get(f'{PBI_API_BASE}/groups/{workspace_id}/reports/{report_id}',
                  headers={"Authorization": f"Bearer {token}"}, timeout=30)
dataset_id = r2.json().get('datasetId', '')
embed_token = _generate_embed_token(workspace_id, report_id, dataset_id, {"Authorization": f"Bearer {token}"})

print(f"\nEmbed URL: {embed_url[:80]}...")
print(f"Dataset ID: {dataset_id}")

# Test with AAD token (TokenType.Aad = 0)
html_aad = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PBI Capture</title>
    <script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>
    <style>* {{ margin: 0; padding: 0; }} body {{ overflow: hidden; }} #report {{ width: 1280px; height: 720px; }}</style>
</head>
<body>
    <div id="report"></div>
    <script>
        const models = window['powerbi-client'].models;
        const config = {{
            type: 'report',
            tokenType: models.TokenType.Aad,
            accessToken: '{token}',
            embedUrl: '{embed_url}',
            id: '{report_id}',
            pageName: 'diag1',
            settings: {{
                navContentPaneEnabled: false,
                filterPaneEnabled: false,
            }}
        }};
        const container = document.getElementById('report');
        const report = powerbi.embed(container, config);
        report.on('rendered', function() {{ document.title = 'RENDERED'; }});
        report.on('error', function(event) {{ document.title = 'ERROR:' + JSON.stringify(event.detail); }});
    </script>
</body>
</html>""".format(token=token, embed_url=embed_url, report_id=report_id)

html_path = evidence_dir / "_v8_aad.html"
html_path.write_text(html_aad, encoding='utf-8')

print("\n=== Testing with AAD token (user context) ===")
all_errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.on('response', lambda resp: all_errors.append(f'{resp.status} {resp.url[:120]}') if resp.status >= 400 else None)
    page.goto(f'file:///{html_path.resolve()}')
    
    try:
        page.wait_for_function(
            "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
            timeout=30000)
    except Exception as e:
        print(f"Wait timeout: {e}")
    
    page.wait_for_timeout(3000)
    title = page.title()
    print(f"Title: {title}")
    page.screenshot(path=str(evidence_dir / "screenshot_V8_aad.png"))
    browser.close()

html_path.unlink(missing_ok=True)

print(f"\nNetwork errors ({len(all_errors)}):")
for e in all_errors:
    print(f"  {e}")

# Also test with embed token for comparison
print("\n=== Testing with Embed token ===")
from pbi_gen.critic.screenshot import capture_report_page
result = capture_report_page(report_id, "diag1", evidence_dir / "screenshot_V8_embed.png")
print(f"Result: {result.outcome.value}")
print(f"Errors: {result.console_errors}")
