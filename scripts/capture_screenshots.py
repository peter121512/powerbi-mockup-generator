"""Attempt to capture screenshots of all 4 report pages."""
import requests
import time
import json
from pathlib import Path
from azure.identity import AzureCliCredential
import yaml

config_path = Path.home() / ".pbi_gen" / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)
workspace_id = config["workspace_id"]

cred = AzureCliCredential()
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default")
headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"

# Get report
r = requests.get(f"{base}/reports", headers=headers, timeout=30)
reports = r.json().get("value", [])
report = next((rp for rp in reports if rp["name"] == "ExecutiveRetailPerformanceDashboard"), None)
if not report:
    print("Report not found")
    exit()
report_id = report["id"]
print(f"Report: {report['name']} (id={report_id})")

# Get pages
r = requests.get(f"{base}/reports/{report_id}/pages", headers=headers, timeout=30)
pages = r.json().get("value", [])
print(f"Pages: {len(pages)}")
for p in pages:
    print(f"  {p['name']}: {p['displayName']}")

# Try export to PNG
output_dir = Path("docs/stages/05a-populated-visual-proof")
output_dir.mkdir(parents=True, exist_ok=True)

# Export all pages as a single PDF first
print("\nAttempting export...")
export_payload = {
    "format": "PNG",
    "powerBIReportConfiguration": {
        "pages": [{"pageName": p["name"]} for p in pages[:1]],  # Just first page
    },
}
r = requests.post(
    f"{base}/reports/{report_id}/ExportTo",
    headers=headers,
    json=export_payload,
    timeout=30,
)
print(f"Export response: {r.status_code}")
if r.status_code == 202:
    export_info = r.json()
    export_id = export_info.get("id", "")
    print(f"Export initiated: id={export_id}")
    
    # Poll for completion
    for i in range(30):
        time.sleep(5)
        r = requests.get(
            f"{base}/reports/{report_id}/exports/{export_id}",
            headers=headers,
            timeout=30,
        )
        if r.status_code == 200:
            status_info = r.json()
            status = status_info.get("status", "Unknown")
            pct = status_info.get("percentComplete", 0)
            print(f"  Status: {status} ({pct}%)")
            if status == "Succeeded":
                # Download the file
                r = requests.get(
                    f"{base}/reports/{report_id}/exports/{export_id}/file",
                    headers=headers,
                    timeout=60,
                )
                if r.status_code == 200:
                    out_path = output_dir / "page1_executive_overview.png"
                    out_path.write_bytes(r.content)
                    print(f"  Saved: {out_path} ({len(r.content)} bytes)")
                break
            elif status == "Failed":
                print(f"  Failed: {status_info}")
                break
elif r.status_code == 200:
    # Direct file response
    out_path = output_dir / "page1_executive_overview.png"
    out_path.write_bytes(r.content)
    print(f"Saved: {out_path} ({len(r.content)} bytes)")
else:
    print(f"Error: {r.text[:500]}")
    # Try alternative: exportToFile on individual page
    print("\nTrying page-level export...")
    for p in pages:
        r = requests.get(
            f"{base}/reports/{report_id}/pages/{p['name']}/export",
            headers=headers,
            timeout=30,
        )
        print(f"  {p['displayName']}: {r.status_code} ({r.text[:100] if r.status_code != 200 else f'{len(r.content)} bytes'})")
