"""Test with embed token (app-owns-data pattern) which might bypass viewer consent."""
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, PBI_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url, _generate_embed_token
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}"}

report_id = '176c1028-e1ab-428a-a5f3-9e6419146d3f'
embed_url = _get_embed_url(workspace_id, report_id, headers)

import requests
r = requests.get(f'{PBI_API_BASE}/groups/{workspace_id}/reports/{report_id}', headers=headers, timeout=30)
dataset_id = r.json().get('datasetId', '')
embed_token = _generate_embed_token(workspace_id, report_id, dataset_id, headers)
print(f"Embed token generated: {bool(embed_token)}")

evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

# Use embed token with TokenType.Embed
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

html_path = evidence_dir / "_embed_token_test.html"
html_path.write_text(html, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.goto(f'file:///{html_path.resolve()}')
    
    try:
        page.wait_for_function(
            "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
            timeout=30000)
    except Exception as e:
        print(f"Timeout: {e}")
    
    page.wait_for_timeout(5000)
    print(f"Title: {page.title()}")
    
    # Check frames for consent or KPI
    for i, frame in enumerate(page.frames):
        if 'powerbi' in (frame.url or ''):
            try:
                kpi_count = frame.locator(".premium-kpi-wrapper").count()
                consent = frame.locator("text=To see this custom visual").count()
                print(f"  Frame {i}: KPI elements={kpi_count}, Consent message={consent}")
                
                if kpi_count > 0:
                    text = frame.locator(".premium-kpi-value").first.text_content()
                    label = frame.locator(".premium-kpi-label").first.text_content()
                    print(f"  *** KPI RENDERED: value='{text}' label='{label}' ***")
            except Exception as e:
                print(f"  Frame {i}: error {str(e)[:80]}")
    
    page.screenshot(path=str(evidence_dir / "screenshot_embed_token.png"))
    browser.close()

html_path.unlink(missing_ok=True)
