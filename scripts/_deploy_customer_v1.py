"""Deploy Customer Performance page using the template system.

Uses the same architecture as Financial: DesignTokens + TemplateRegistry + PageBuilder.
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
from pbi_gen.renderer.templates.registry import DesignTokens, TemplateRegistry
from pbi_gen.renderer.templates.builder import PageBuilder
from pbi_gen.renderer.templates.customer_config import customer_page_shell, customer_visual_bindings
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

# Constants
sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
REPORT_NAME = "CustomerPerformance_v1"
evidence_dir = Path("docs/stages/09-customer-dashboard")
evidence_dir.mkdir(parents=True, exist_ok=True)

KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
AREA_GUID = "premiumAreaChart1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D"
INSIGHTS_GUID = "premiumInsights2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D"

# Authenticate
config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Build page
tokens = DesignTokens()
reg = TemplateRegistry.default()
shell = customer_page_shell()

builder = PageBuilder(
    shell=shell,
    tokens=tokens,
    registry=reg,
    semantic_model_id=sm_id,
    semantic_model_name="ExecutiveRetailPerformanceDashboard",
    report_name=REPORT_NAME,
)

for binding in customer_visual_bindings():
    builder.add_visual(binding)

# Load custom visual archives and build parts with real binary content
def load_visual_archive(guid: str, folder: str) -> tuple[bytes, bytes]:
    pbiviz_path = Path(f"custom-visuals/{folder}/dist/{guid}.1.0.0.0.pbiviz")
    with zipfile.ZipFile(io.BytesIO(pbiviz_path.read_bytes())) as z:
        pkg = z.read("package.json")
        res = z.read(f"resources/{guid}.pbiviz.json")
        return (pkg, res)

visual_archives = {
    KPI_GUID: load_visual_archive(KPI_GUID, "premiumKPI"),
    AREA_GUID: load_visual_archive(AREA_GUID, "premiumAreaChart"),
    INSIGHTS_GUID: load_visual_archive(INSIGHTS_GUID, "premiumInsights"),
}

parts = builder.build_pbir_parts_with_visuals(visual_archives)

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == REPORT_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# Deploy
print(f"Creating: {REPORT_NAME}")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": REPORT_NAME, "type": "Report", "definition": {"parts": parts}}, timeout=60)
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
            print(f"FAILED: {data.get('error', {}).get('message', '')[:400]}")
            sys.exit(1)
else:
    print(f"Error {r.status_code}: {r.text[:300]}")
    sys.exit(1)

time.sleep(3)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == REPORT_NAME), None)
print(f"Report ID: {report_id}")

# Screenshot using embed token
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
print(f"Embed URL: {embed_url[:80]}...")

# Generate embed token
embed_body = {"datasets": [{"id": sm_id}], "reports": [{"id": report_id}]}
er = requests.post("https://api.powerbi.com/v1.0/myorg/GenerateToken", headers=headers, json=embed_body, timeout=30)
embed_token = er.json().get("token", token)
print(f"Embed token generated ({len(embed_token)} chars)")

page_name = shell.page_name
html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
    '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
    '<style>*{margin:0;padding:0}body{overflow:hidden;background:#0f1623}#r{width:1280px;height:720px}</style>'
    '</head><body><div id="r"></div><script>'
    'const m=window["powerbi-client"].models;'
    f'const c={{type:"report",tokenType:m.TokenType.Embed,accessToken:"{embed_token}",'
    f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"{page_name}",'
    'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
    'background:m.BackgroundType.Transparent,'
    'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
    'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
    'const r=powerbi.embed(document.getElementById("r"),c);'
    'r.on("rendered",()=>{document.title="RENDERED"});'
    'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
    '</script></body></html>'
)
html_path = evidence_dir / '_customer.html'
html_path.write_text(html, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.goto(f'file:///{html_path.resolve()}')
    try:
        page.wait_for_function('document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")', timeout=45000)
    except:
        pass
    page.wait_for_timeout(5000)
    print(f"Title: {page.title()}")
    page.screenshot(path=str(evidence_dir / 'customer_v1.png'))
    browser.close()
html_path.unlink(missing_ok=True)
print("Done! Check customer_v1.png")
