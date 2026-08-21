"""Test if the cloned report bypasses consent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token

clone_id = 'fb804f1a-a1cc-45e7-badc-e01aa77a6ecb'
embed_url = _get_embed_url(workspace_id, clone_id, {'Authorization': f'Bearer {token}'})
evidence_dir = Path('docs/stages/07d-a-custom-visual-auto-binding')

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

html_path = evidence_dir / '_clone.html'
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
    print(f'Title: {page.title()}')
    for frame in page.frames:
        if 'powerbi' in (frame.url or ''):
            try:
                kpi = frame.locator('.premium-kpi-wrapper').count()
                consent = frame.locator('text=To see this custom visual').count()
                print(f'  KPI: {kpi}, Consent: {consent}')
                if kpi > 0:
                    val = frame.locator('.premium-kpi-value').first.text_content()
                    print(f'  *** VALUE: {val} ***')
            except:
                pass
    page.screenshot(path=str(evidence_dir / 'screenshot_clone.png'))
    browser.close()
html_path.unlink(missing_ok=True)
