"""3-run zero-touch validation using Desktop-mimic custom visual structure."""
import sys
import json
import base64
import time
import uuid
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
sm_id = 'ca81c70a-f84a-4417-adfa-0e1e7694f746'
KPI_GUID = 'premiumKPI0E21B11FE691418A84E3F774DD6461A5'
evidence_dir = Path('docs/stages/07d-b-trusted-custom-visual-delivery')

desktop_root = Path('custom-visuals/premiumKPI/dist/testReport.Report')
pbiviz_json = (desktop_root / f'CustomVisuals/{KPI_GUID}/resources/{KPI_GUID}.pbiviz.json').read_bytes()
package_json_bytes = (desktop_root / f'CustomVisuals/{KPI_GUID}/package.json').read_bytes()

results = []
for run in range(1, 4):
    name = f'ZT07db_Run{run}_{uuid.uuid4().hex[:6]}'
    print(f"\n=== Run {run}: {name} ===")
    
    parts = []
    def add(path, obj):
        parts.append({'path': path, 'payload': base64.b64encode(json.dumps(obj).encode()).decode(), 'payloadType': 'InlineBase64'})
    def add_bin(path, data):
        parts.append({'path': path, 'payload': base64.b64encode(data).decode(), 'payloadType': 'InlineBase64'})

    add('.platform', {'metadata': {'type': 'Report', 'displayName': name}, 'config': {'version': '2.0', 'logicalId': str(uuid.uuid4())}})
    add('definition.pbir', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json', 'version': '4.0', 'datasetReference': {'byConnection': {'connectionString': f'Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}'}}})
    add('definition/version.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'})
    add('definition/report.json', {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json',
        'themeCollection': {'baseTheme': {'name': 'CY24SU06', 'reportVersionAtImport': '5.61', 'type': 'SharedResources'}},
        'layoutOptimization': 'None',
        'resourcePackages': [
            {'name': 'SharedResources', 'type': 'SharedResources', 'items': [{'name': 'CY24SU06', 'type': 'BaseTheme', 'path': 'BaseThemes/CY24SU06.json'}]},
            {'name': KPI_GUID, 'type': 'CustomVisual', 'items': [{'name': f'{KPI_GUID}.pbiviz.json', 'type': 'CustomVisualMetadata', 'path': f'{KPI_GUID}.pbiviz.json'}]},
        ]
    })
    add('definition/pages/pages.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json', 'pageOrder': ['p1'], 'activePageName': 'p1'})
    add('definition/pages/p1/page.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json', 'name': 'p1', 'displayName': 'Main', 'displayOption': 'FitToPage', 'height': 720, 'width': 1280})
    add('definition/pages/p1/visuals/kpi1/visual.json', {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json',
        'name': 'kpi1',
        'position': {'x': 100, 'y': 100, 'z': 0, 'width': 350, 'height': 200, 'tabOrder': 0},
        'visual': {
            'visualType': KPI_GUID,
            'query': {'queryState': {'measure': {'projections': [{'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Fact'}}, 'Property': 'Total'}}, 'queryRef': 'Fact.Total', 'nativeQueryRef': 'Total'}]}}},
            'drillFilterOtherVisuals': True,
        },
    })
    add_bin(f'CustomVisuals/{KPI_GUID}/package.json', package_json_bytes)
    add_bin(f'CustomVisuals/{KPI_GUID}/resources/{KPI_GUID}.pbiviz.json', pbiviz_json)

    # Deploy
    r = requests.post(f'{FABRIC_API_BASE}/workspaces/{workspace_id}/items', headers=headers,
                      json={'displayName': name, 'type': 'Report', 'definition': {'parts': parts}}, timeout=60)
    if r.status_code == 202:
        loc = r.headers.get('Location', '')
        deployed = False
        for _ in range(15):
            time.sleep(3)
            poll = requests.get(loc, headers=headers, timeout=30)
            status = poll.json().get('status')
            if status == 'Succeeded':
                deployed = True
                break
            elif status == 'Failed':
                print(f"  DEPLOY FAILED: {poll.json().get('error', {}).get('message', '')[:200]}")
                break
        if not deployed:
            results.append({'run': run, 'success': False, 'reason': 'deploy_failed'})
            continue
    
    time.sleep(2)
    r = requests.get(f'{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report', headers=headers, timeout=30)
    report_id = next((i['id'] for i in r.json()['value'] if i['displayName'] == name), None)
    embed_url = _get_embed_url(workspace_id, report_id, {'Authorization': f'Bearer {token}'})
    
    # Embed and check
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
        '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
        '<style>*{margin:0;padding:0}body{overflow:hidden}#r{width:1280px;height:720px}</style>'
        '</head><body><div id="r"></div><script>'
        'const m=window["powerbi-client"].models;'
        f'const c={{type:"report",tokenType:m.TokenType.Aad,accessToken:"{token}",'
        f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"p1",'
        'settings:{navContentPaneEnabled:false,filterPaneEnabled:false}};'
        'const r=powerbi.embed(document.getElementById("r"),c);'
        'r.on("rendered",()=>{document.title="RENDERED"});'
        'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
        '</script></body></html>'
    )
    html_path = evidence_dir / f'_zt{run}.html'
    html_path.write_text(html, encoding='utf-8')
    
    found_kpi = False
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
        
        for frame in page.frames:
            if 'powerbi' in (frame.url or ''):
                try:
                    kpi = frame.locator('.premium-kpi-wrapper').count()
                    if kpi > 0:
                        val = frame.locator('.premium-kpi-value').first.text_content()
                        found_kpi = (val == '600')
                        print(f"  KPI value: '{val}' -> {'PASS' if found_kpi else 'FAIL'}")
                except:
                    pass
        
        page.screenshot(path=str(evidence_dir / f'zero_touch_run{run}.png'))
        browser.close()
    
    html_path.unlink(missing_ok=True)
    results.append({'run': run, 'name': name, 'report_id': report_id, 'success': found_kpi})
    print(f"  Result: {'PASS' if found_kpi else 'FAIL'}")

print(f"\n{'='*40}")
print(f"FINAL: {sum(1 for r in results if r.get('success'))}/3 passed")
Path(evidence_dir / 'zero_touch_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
