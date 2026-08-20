"""Deploy a report that exactly mirrors the working CRMmetricsng structure.

Uses CRMmetricsng's exact report.json format, page schema, visual schema,
theme registration pattern — but points to BareMinimal's semantic model.
"""
import sys
import json
import base64
import time
import uuid
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pbi_gen.deploy.fabric import load_config, get_credential

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# BareMinimal semantic model ID
sm_id = "ca81c70a-f84a-4417-adfa-0e1e7694f746"

# Build parts exactly like CRMmetricsng
page_name = "a1b2c3d4e5f6a7b8c9d0"  # hex-style name

parts = []

# .platform
platform = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": "ExactClone"},
    "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
}
parts.append({"path": ".platform", "payload": base64.b64encode(json.dumps(platform).encode()).decode(), "payloadType": "InlineBase64"})

# definition.pbir - use byConnection like CRMmetricsng has stored
pbir = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {
        "byConnection": {
            "connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=BareMinimal;integrated security=ClaimsToken;semanticmodelid={sm_id}"
        }
    },
}
parts.append({"path": "definition.pbir", "payload": base64.b64encode(json.dumps(pbir).encode()).decode(), "payloadType": "InlineBase64"})

# definition/version.json
version = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
}
parts.append({"path": "definition/version.json", "payload": base64.b64encode(json.dumps(version).encode()).decode(), "payloadType": "InlineBase64"})

# definition/report.json - exactly like CRMmetricsng but without custom theme (simpler)
report = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {
        "baseTheme": {
            "name": "CY24SU10",
            "reportVersionAtImport": "5.61",
            "type": "SharedResources",
        }
    },
    "layoutOptimization": "None",
    "resourcePackages": [
        {
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [
                {
                    "name": "CY24SU10",
                    "path": "BaseThemes/CY24SU10.json",
                    "type": "BaseTheme",
                }
            ],
        }
    ],
    "settings": {
        "useStylableVisualContainerHeader": True,
        "defaultFilterActionIsDataFilter": True,
        "defaultDrillFilterOtherVisuals": True,
        "allowChangeFilterTypes": True,
        "allowInlineExploration": True,
        "useEnhancedTooltips": True,
    },
}
parts.append({"path": "definition/report.json", "payload": base64.b64encode(json.dumps(report).encode()).decode(), "payloadType": "InlineBase64"})

# definition/pages/pages.json
pages = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": [page_name],
    "activePageName": page_name,
}
parts.append({"path": "definition/pages/pages.json", "payload": base64.b64encode(json.dumps(pages).encode()).decode(), "payloadType": "InlineBase64"})

# definition/pages/<hex>/page.json - exactly like CRMmetricsng
page = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": page_name,
    "displayName": "Test Page",
    "displayOption": "FitToPage",
    "height": 720,
    "width": 1280,
}
parts.append({"path": f"definition/pages/{page_name}/page.json", "payload": base64.b64encode(json.dumps(page).encode()).decode(), "payloadType": "InlineBase64"})

# One card visual - exactly like CRMmetricsng visual structure
visual_name = "f1e2d3c4b5a6f7e8d9c0"
visual = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
    "name": visual_name,
    "position": {
        "x": 32,
        "y": 32,
        "z": 8000,
        "height": 200,
        "width": 300,
        "tabOrder": 1000,
    },
    "visual": {
        "visualType": "card",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {
                                        "SourceRef": {"Entity": "Fact"}
                                    },
                                    "Property": "Total",
                                }
                            },
                            "queryRef": "Fact.Total",
                            "active": True,
                        }
                    ]
                }
            }
        },
        "drillFilterOtherVisuals": True,
    },
}
parts.append({"path": f"definition/pages/{page_name}/visuals/{visual_name}/visual.json", "payload": base64.b64encode(json.dumps(visual).encode()).decode(), "payloadType": "InlineBase64"})

# Create via Fabric API
print(f"Creating ExactClone report with {len(parts)} parts...")
create_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
body = {
    "displayName": "ExactClone",
    "type": "Report",
    "definition": {"parts": parts},
}
r = requests.post(create_url, headers=headers, json=body, timeout=60)
print(f"Status: {r.status_code}")

if r.status_code == 202:
    loc = r.headers.get("Location", "")
    op = r.headers.get("x-ms-operation-id", "")
    for _ in range(15):
        time.sleep(3)
        poll = requests.get(loc or f"https://api.fabric.microsoft.com/v1/operations/{op}", headers=headers, timeout=30)
        pdata = poll.json()
        print(f"  Status: {pdata.get('status')}")
        if pdata.get("status") == "Succeeded":
            print("SUCCESS! Report created.")
            # Get the report ID
            r2 = requests.get(f"https://api.fabric.microsoft.com/v1/operations/{op}/result", headers=headers, timeout=30)
            if r2.status_code == 200:
                print(f"  Result: {r2.json()}")
            break
        elif pdata.get("status") == "Failed":
            print(f"  Error: {pdata.get('error', {})}")
            break
elif r.status_code in (200, 201):
    print(f"Created: {r.json()}")
else:
    print(f"Error: {r.text[:500]}")
