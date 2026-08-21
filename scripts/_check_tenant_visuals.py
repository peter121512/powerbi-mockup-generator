"""Check tenant settings related to custom visuals."""
import requests, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
credential = get_credential(config)
token = credential.get_token('https://analysis.windows.net/powerbi/api/.default').token
headers = {'Authorization': f'Bearer {token}'}

r = requests.get('https://api.fabric.microsoft.com/v1/admin/tenantsettings', headers=headers, timeout=30)
settings = r.json().get('tenantSettings', [])

print("=== Custom Visual Related Tenant Settings ===")
for s in settings:
    name = s.get('settingName', '').lower()
    title = s.get('title', '').lower()
    if any(kw in name or kw in title for kw in ['visual', 'custom', 'appsource', 'org']):
        print(f"  {s['settingName']}: enabled={s.get('enabled')}")
        print(f"    {s.get('title')}")
        props = s.get('properties', [])
        if props:
            for p in props:
                print(f"    prop: {p.get('name')}={p.get('value')}")
        print()
