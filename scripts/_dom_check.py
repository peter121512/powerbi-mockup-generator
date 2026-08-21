"""Check if the custom visual iframe exists in the rendered page DOM."""
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

report_id = '176c1028-e1ab-428a-a5f3-9e6419146d3f'  # Latest KPIOnly
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
evidence_dir = Path("docs/stages/07d-a-custom-visual-auto-binding")

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

html_path = evidence_dir / "_dom_check.html"
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
    title = page.title()
    print(f"Title: {title}")
    
    # Check DOM for visual containers
    dom_info = page.evaluate("""() => {
        const iframe = document.querySelector('iframe');
        if (!iframe) return {error: 'no iframe'};
        
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (!iframeDoc) return {error: 'no iframe doc'};
        
        // Look for visual containers
        const visuals = iframeDoc.querySelectorAll('[class*="visual"]');
        const containers = iframeDoc.querySelectorAll('.visualContainer');
        const customVis = iframeDoc.querySelectorAll('[class*="custom"]');
        const allIframes = iframeDoc.querySelectorAll('iframe');
        
        // Get body HTML snippet
        const bodyText = iframeDoc.body ? iframeDoc.body.innerHTML.substring(0, 2000) : 'no body';
        
        return {
            visuals: visuals.length,
            containers: containers.length,
            customVis: customVis.length,
            iframes: allIframes.length,
            bodySnippet: bodyText
        };
    }""")
    print(f"\nDOM info: {json.dumps(dom_info, indent=2)[:2000]}")
    
    # Try to find any iframe in the page and check recursively
    all_frames = page.frames
    print(f"\nTotal frames: {len(all_frames)}")
    for i, frame in enumerate(all_frames):
        url = frame.url[:100]
        print(f"  Frame {i}: {url}")
        if 'powerbi' in url or 'report' in url:
            try:
                # Check for visual elements in this frame
                visual_count = frame.evaluate("document.querySelectorAll('.visualContainer, .visual, [class*=visual]').length")
                print(f"    Visuals found: {visual_count}")
                
                # Check for our custom visual specifically
                kpi_elements = frame.evaluate("""() => {
                    const els = document.querySelectorAll('.premium-kpi-wrapper, .premium-kpi-value');
                    return els.length;
                }""")
                print(f"    KPI elements: {kpi_elements}")
                
                # Get any error/warning messages visible
                messages = frame.evaluate("""() => {
                    const msgs = document.querySelectorAll('[class*=error], [class*=warning], [class*=message]');
                    return Array.from(msgs).map(m => m.textContent.substring(0, 100)).slice(0, 5);
                }""")
                if messages:
                    print(f"    Messages: {messages}")
            except Exception as e:
                print(f"    Error inspecting: {str(e)[:100]}")
    
    browser.close()

html_path.unlink(missing_ok=True)
