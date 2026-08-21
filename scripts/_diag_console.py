"""Capture full browser diagnostics for custom visual loading."""
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
print(f'embed_url: {embed_url[:80]}...')
print(f'dataset_id: {dataset_id}')
print(f'embed_token exists: {bool(embed_token)}')

html = EMBED_HTML_TEMPLATE.format(
    width=1280, height=720, token=embed_token,
    embed_url=embed_url, report_id=report_id, page_name='diag1'
)
html_path = Path('docs/stages/07d-a-custom-visual-auto-binding/_diag.html')
html_path.write_text(html, encoding='utf-8')

all_messages = []
network_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    
    page.on('console', lambda msg: all_messages.append(f'[{msg.type}] {msg.text}'))
    page.on('response', lambda resp: network_errors.append(
        f'{resp.status} {resp.url[:120]}') if resp.status >= 400 else None)
    
    page.goto(f'file:///{html_path.resolve()}')
    
    js_check = "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')"
    try:
        page.wait_for_function(js_check, timeout=30000)
    except Exception as e:
        print(f"Wait failed: {e}")
    
    page.wait_for_timeout(3000)
    title = page.title()
    print(f'\nTitle: {title}')
    
    browser.close()

html_path.unlink(missing_ok=True)

print(f'\n=== Network errors ({len(network_errors)}) ===')
for e in network_errors:
    print(f'  {e}')

print(f'\n=== Console messages ({len(all_messages)}) ===')
for m in all_messages[:50]:
    print(f'  {m[:250]}')
