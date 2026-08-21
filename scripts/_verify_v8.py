"""Verify V8 - full page screenshot with AAD token to see all visuals."""
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, PBI_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token

report_id = '77d5d12b-fed3-47de-94c7-0a6470457a84'  # V8
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})

evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

# Use AAD token with FitToPage
html = """<!DOCTYPE html>
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
                layoutType: models.LayoutType.Custom,
                customLayout: {{
                    displayOption: models.DisplayOption.FitToPage,
                    pageSize: {{ type: models.PageSizeType.Custom, width: 1280, height: 720 }}
                }}
            }}
        }};
        const container = document.getElementById('report');
        const report = powerbi.embed(container, config);
        report.on('rendered', function() {{ document.title = 'RENDERED'; }});
        report.on('error', function(event) {{ document.title = 'ERROR:' + JSON.stringify(event.detail); }});
    </script>
</body>
</html>""".format(token=token, embed_url=embed_url, report_id=report_id)

html_path = evidence_dir / "_v8_verify.html"
html_path.write_text(html, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    
    all_responses = []
    page.on('response', lambda resp: all_responses.append((resp.status, resp.url[:150])) if resp.status >= 400 else None)
    
    page.goto(f'file:///{html_path.resolve()}')
    
    try:
        page.wait_for_function(
            "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
            timeout=30000)
    except Exception as e:
        print(f"Wait failed: {e}")
    
    # Extra wait for visual rendering
    page.wait_for_timeout(5000)
    title = page.title()
    print(f"Title: {title}")
    
    # Full page screenshot  
    page.screenshot(path=str(evidence_dir / "screenshot_V8_full.png"), full_page=True)
    
    # Also get the report container specifically
    try:
        report_el = page.locator("#report")
        report_el.screenshot(path=str(evidence_dir / "screenshot_V8_report.png"))
    except:
        pass
    
    browser.close()

html_path.unlink(missing_ok=True)

print(f"\nErrors ({len(all_responses)}):")
for status, url in all_responses:
    print(f"  {status}: {url}")

print("\nDone! Check screenshot_V8_full.png and screenshot_V8_report.png")
