"""Capture full 403 URL and test access with bearer token."""
import sys
import time
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential, PBI_API_BASE
from pbi_gen.critic.screenshot import EMBED_HTML_TEMPLATE, _generate_embed_token, _get_embed_url
import requests
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config['workspace_id']
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}'}

report_id = 'ac399fd5-e078-47a0-8ce1-8cd7bd7b00f1'  # V6A

embed_url = _get_embed_url(workspace_id, report_id, headers)
r = requests.get(f'{PBI_API_BASE}/groups/{workspace_id}/reports/{report_id}', headers=headers, timeout=30)
dataset_id = r.json().get('datasetId', '')
embed_token = _generate_embed_token(workspace_id, report_id, dataset_id, headers)

html = EMBED_HTML_TEMPLATE.format(
    width=1280, height=720, token=embed_token,
    embed_url=embed_url, report_id=report_id, page_name='diag1'
)
html_path = Path('docs/stages/07d-a-custom-visual-auto-binding/_diag2.html')
html_path.write_text(html, encoding='utf-8')

all_urls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    
    def on_response(resp):
        if resp.status >= 400:
            all_urls.append((resp.status, resp.url))
    
    page.on('response', on_response)
    page.goto(f'file:///{html_path.resolve()}')
    
    js_check = "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')"
    try:
        page.wait_for_function(js_check, timeout=30000)
    except Exception as e:
        print(f"Wait failed: {e}")
    
    page.wait_for_timeout(3000)
    browser.close()

html_path.unlink(missing_ok=True)

print("=== Failed URLs ===")
for status, url in all_urls:
    print(f"  {status}: {url}")

# Now try to access the 403 URL with bearer token directly
print("\n=== Testing 403 URLs with bearer token ===")
for status, url in all_urls:
    if status == 403 and 'resourcePackageItem' in url:
        print(f"\nTrying: {url}")
        r = requests.get(url, headers=headers, timeout=30)
        print(f"  Bearer token result: {r.status_code}")
        if r.status_code == 200:
            print(f"  Content-Type: {r.headers.get('content-type')}")
            print(f"  Body length: {len(r.content)}")
        else:
            print(f"  Body: {r.text[:300]}")

# Also try the V3 report (organizationCustomVisuals) to compare
print("\n\n=== Testing V3 (organizationCustomVisuals) report ===")
report_id_v3 = 'b68ed805-7183-4e6b-bbd4-07da8e842191'
embed_url_v3 = _get_embed_url(workspace_id, report_id_v3, headers)
r = requests.get(f'{PBI_API_BASE}/groups/{workspace_id}/reports/{report_id_v3}', headers=headers, timeout=30)
dataset_id_v3 = r.json().get('datasetId', '')
embed_token_v3 = _generate_embed_token(workspace_id, report_id_v3, dataset_id_v3, headers)

html_v3 = EMBED_HTML_TEMPLATE.format(
    width=1280, height=720, token=embed_token_v3,
    embed_url=embed_url_v3, report_id=report_id_v3, page_name='diag1'
)
html_path_v3 = Path('docs/stages/07d-a-custom-visual-auto-binding/_diag3.html')
html_path_v3.write_text(html_v3, encoding='utf-8')

v3_urls = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.on('response', lambda resp: v3_urls.append((resp.status, resp.url)) if resp.status >= 400 else None)
    page.goto(f'file:///{html_path_v3.resolve()}')
    js_check = "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')"
    try:
        page.wait_for_function(js_check, timeout=30000)
    except:
        pass
    page.wait_for_timeout(3000)
    browser.close()

html_path_v3.unlink(missing_ok=True)

print(f"V3 failed URLs ({len(v3_urls)}):")
for status, url in v3_urls:
    print(f"  {status}: {url}")
