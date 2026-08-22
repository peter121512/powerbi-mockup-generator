"""Deploy Financial Performance page using the template system.

Uses DesignTokens + TemplateRegistry + PageBuilder to generate the full
PBIR definition from declarative configuration, then deploys via Fabric REST API
and captures a headless screenshot.
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
from pbi_gen.renderer.templates.financial_config import financial_page_shell, financial_visual_bindings
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
REPORT_NAME = "FinancialPerformance_v1"
evidence_dir = Path("docs/stages/08-financial-dashboard")
evidence_dir.mkdir(parents=True, exist_ok=True)

KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
AREA_GUID = "premiumAreaChart1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D"
WATERFALL_GUID = "premiumWaterfall3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D"

# ─────────────────────────────────────────────────────────────────────────────
# Authenticate
# ─────────────────────────────────────────────────────────────────────────────

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ─────────────────────────────────────────────────────────────────────────────
# Build page using template system
# ─────────────────────────────────────────────────────────────────────────────

tokens = DesignTokens()
reg = TemplateRegistry.default()
shell = financial_page_shell()

builder = PageBuilder(
    shell=shell,
    tokens=tokens,
    registry=reg,
    semantic_model_id=sm_id,
    semantic_model_name="ExecutiveRetailPerformanceDashboard",
    report_name=REPORT_NAME,
)

for binding in financial_visual_bindings():
    builder.add_visual(binding)

# ─────────────────────────────────────────────────────────────────────────────
# Package custom visuals
# ─────────────────────────────────────────────────────────────────────────────


def load_visual_archive(guid: str, visual_dir: str) -> tuple[bytes, bytes]:
    """Load package.json and pbiviz.json from a built custom visual."""
    pbiviz_path = Path(f"custom-visuals/{visual_dir}/dist/{guid}.1.0.0.0.pbiviz")
    with zipfile.ZipFile(io.BytesIO(pbiviz_path.read_bytes())) as z:
        package_json = z.read("package.json")
        pbiviz_json = z.read(f"resources/{guid}.pbiviz.json")
    return package_json, pbiviz_json


visual_archives: dict[str, tuple[bytes, bytes]] = {
    KPI_GUID: load_visual_archive(KPI_GUID, "premiumKPI"),
    AREA_GUID: load_visual_archive(AREA_GUID, "premiumAreaChart"),
    WATERFALL_GUID: load_visual_archive(WATERFALL_GUID, "premiumWaterfall"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Build PBIR parts and replace custom visual placeholders
# ─────────────────────────────────────────────────────────────────────────────

parts = builder.build_pbir_parts()
final_parts = []
for p in parts:
    path = p["path"]
    if path.startswith("CustomVisuals/") and path.endswith("/package.json"):
        guid = path.split("/")[1]
        if guid in visual_archives:
            pkg_json, _ = visual_archives[guid]
            final_parts.append({"path": path, "payload": base64.b64encode(pkg_json).decode(), "payloadType": "InlineBase64"})
        else:
            final_parts.append(p)
    elif path.startswith("CustomVisuals/") and "resources/" in path:
        guid = path.split("/")[1]
        if guid in visual_archives:
            _, pviz_json = visual_archives[guid]
            final_parts.append({"path": path, "payload": base64.b64encode(pviz_json).decode(), "payloadType": "InlineBase64"})
        else:
            final_parts.append(p)
    else:
        final_parts.append(p)

# ─────────────────────────────────────────────────────────────────────────────
# Delete existing report with same name
# ─────────────────────────────────────────────────────────────────────────────

r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == REPORT_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# ─────────────────────────────────────────────────────────────────────────────
# Create report via Fabric REST API
# ─────────────────────────────────────────────────────────────────────────────

print(f"Creating: {REPORT_NAME}")
r = requests.post(
    f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items",
    headers=headers,
    json={"displayName": REPORT_NAME, "type": "Report", "definition": {"parts": final_parts}},
    timeout=60,
)
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

# ─────────────────────────────────────────────────────────────────────────────
# Get report ID
# ─────────────────────────────────────────────────────────────────────────────

time.sleep(8)
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == REPORT_NAME), None)
print(f"Report ID: {report_id}")

# ─────────────────────────────────────────────────────────────────────────────
# Get embed URL
# ─────────────────────────────────────────────────────────────────────────────

embed_url = None
for attempt in range(3):
    embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
    if embed_url:
        break
    print(f"  Embed URL attempt {attempt+1} failed, retrying...")
    time.sleep(5)

if not embed_url:
    print("ERROR: Could not get embed URL")
    sys.exit(1)

print(f"Embed URL: {embed_url[:80]}...")

# ─────────────────────────────────────────────────────────────────────────────
# Generate embed token and screenshot
# ─────────────────────────────────────────────────────────────────────────────

token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
time.sleep(5)

gen_token_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken"
gen_resp = requests.post(gen_token_url, headers=headers, json={"accessLevel": "View"}, timeout=30)
if gen_resp.status_code != 200:
    print(f"ERROR: Could not generate embed token: {gen_resp.status_code} {gen_resp.text[:200]}")
    sys.exit(1)
embed_token = gen_resp.json()["token"]
print(f"Embed token generated ({len(embed_token)} chars)")

html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
    '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
    '<style>*{margin:0;padding:0}body{overflow:hidden;background:#0f1623}#r{width:1280px;height:720px}</style>'
    '</head><body><div id="r"></div><script>'
    'const m=window["powerbi-client"].models;'
    f'const c={{type:"report",tokenType:m.TokenType.Embed,accessToken:"{embed_token}",'
    f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"{shell.page_name}",'
    'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
    'background:m.BackgroundType.Transparent,'
    'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
    'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
    'const r=powerbi.embed(document.getElementById("r"),c);'
    'r.on("rendered",()=>{document.title="RENDERED"});'
    'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
    '</script></body></html>'
)
html_path = evidence_dir / "_financial.html"
html_path.write_text(html, encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(f"file:///{html_path.resolve()}")
    try:
        page.wait_for_function('document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")', timeout=60000)
    except Exception:
        pass
    page.wait_for_timeout(6000)
    print(f"Title: {page.title()}")
    page.screenshot(path=str(evidence_dir / "financial_v1.png"))
    browser.close()
html_path.unlink(missing_ok=True)
print("Done! Check financial_v1.png")
