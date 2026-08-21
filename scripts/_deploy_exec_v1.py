"""Deploy full Executive Overview page with dark canvas, KPI row, and native charts.

Uses ExecutiveRetailPerformanceDashboard semantic model.
Iterates toward Mockup 1 visual standard.
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
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.critic.screenshot import _get_embed_url
from playwright.sync_api import sync_playwright

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Executive Retail semantic model
sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
KPI_GUID = "premiumKPI0E21B11FE691418A84E3F774DD6461A5"
DIAG_NAME = "ExecOverview_v1"
evidence_dir = Path("docs/stages/07e-executive-custom-visual-demo")
evidence_dir.mkdir(parents=True, exist_ok=True)

# Delete existing
r = requests.get(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report", headers=headers, timeout=30)
for item in r.json().get("value", []):
    if item["displayName"] == DIAG_NAME:
        requests.delete(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item['id']}", headers=headers, timeout=30)
        time.sleep(5)
        break

# Read KPI visual resources
pbiviz_path = Path(f"custom-visuals/premiumKPI/dist/{KPI_GUID}.1.0.0.0.pbiviz")
pbiviz_bytes = pbiviz_path.read_bytes()
z = zipfile.ZipFile(io.BytesIO(pbiviz_bytes))
pbiviz_json = z.read(f"resources/{KPI_GUID}.pbiviz.json")
package_json_bytes = z.read("package.json")

parts = []
def add(path, obj):
    parts.append({"path": path, "payload": base64.b64encode(json.dumps(obj, ensure_ascii=False).encode()).decode(), "payloadType": "InlineBase64"})
def add_bin(path, data):
    parts.append({"path": path, "payload": base64.b64encode(data).decode(), "payloadType": "InlineBase64"})

# Platform
add(".platform", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": DIAG_NAME},
    "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
})

# Definition
add("definition.pbir", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byConnection": {"connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/pbi;initial catalog=ExecutiveRetailPerformanceDashboard;integrated security=ClaimsToken;semanticmodelid={sm_id}"}},
})
add("definition/version.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
})

# Report with custom theme + custom visual
add("definition/report.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
    "themeCollection": {
        "baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.61", "type": "SharedResources"},
        "customTheme": {"name": "ExecutiveDark", "reportVersionAtImport": "5.61", "type": "RegisteredResources"},
    },
    "layoutOptimization": "None",
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU06", "type": "BaseTheme", "path": "BaseThemes/CY24SU06.json"}
        ]},
        {"name": "RegisteredResources", "type": "RegisteredResources", "items": [
            {"name": "ExecutiveDark", "type": "CustomTheme", "path": "ExecutiveDark.json"}
        ]},
        {"name": KPI_GUID, "type": "CustomVisual", "items": [
            {"name": f"{KPI_GUID}.pbiviz.json", "type": "CustomVisualMetadata", "path": f"{KPI_GUID}.pbiviz.json"},
        ]},
    ],
})

# Dark theme
dark_theme = {
    "name": "ExecutiveDark",
    "dataColors": ["#3898ff", "#a78bfa", "#34d399", "#fbbf24", "#f87171", "#06b6d4", "#818cf8", "#fb923c"],
    "background": "#0f1623",
    "foreground": "#ffffff",
    "foregroundNeutralSecondary": "#94a3b8",
    "foregroundNeutralTertiary": "#64748b",
    "backgroundLight": "#151d2e",
    "backgroundNeutral": "#1e293b",
    "backgroundDark": "#0a0e17",
    "tableAccent": "#3898ff",
    "good": "#34d399",
    "bad": "#f87171",
    "neutral": "#fbbf24",
    "visualStyles": {
        "page": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": "#0f1623"}}, "transparency": 0}],
            "outspace": [{"color": {"solid": {"color": "#0a0e17"}}}],
        }},
        "*": {"*": {
            "background": [{"show": False, "transparency": 100}],
            "title": [{"show": True, "color": {"solid": {"color": "#e2e8f0"}}, "fontSize": 11, "fontFamily": "Segoe UI Semibold"}],
            "labels": [{"color": {"solid": {"color": "#94a3b8"}}, "fontSize": 9}],
            "categoryAxis": [{"showAxisTitle": False, "labelColor": {"solid": {"color": "#94a3b8"}}, "fontSize": 9}],
            "valueAxis": [{"showAxisTitle": False, "labelColor": {"solid": {"color": "#64748b"}}, "fontSize": 9, "gridlineColor": {"solid": {"color": "#1e293b"}}, "gridlineStyle": 1}],
            "legend": [{"labelColor": {"solid": {"color": "#94a3b8"}}, "fontSize": 9}],
            "dataPoint": [{}],
        }},
    },
}
add_bin("StaticResources/RegisteredResources/ExecutiveDark.json", json.dumps(dark_theme).encode("utf-8"))

# Pages
add("definition/pages/pages.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["exec"], "activePageName": "exec",
})

# Page with dark background
add("definition/pages/exec/page.json", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
    "name": "exec", "displayName": "Executive Overview", "displayOption": "FitToPage",
    "height": 720, "width": 1280,
    "objects": {
        "background": [{"properties": {
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#0f1623'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
    },
})

# KPI measures from the retail model
kpi_measures = [
    ("Total Revenue", "Sales", "TotalRevenue"),
    ("Gross Profit", "Sales", "GrossProfit"),
    ("Total Cost", "Sales", "TotalCost"),
    ("Gross Margin", "Sales", "GrossMarginPct"),
]

kpi_start_x = 50

# Visual container helper
def vis_container(name, x, y, w, h, z_idx):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z_idx, "width": w, "height": h, "tabOrder": z_idx},
    }

# ===== KPI ROW (4 cards) =====
kpi_width = 270
kpi_height = 100
kpi_gap = 18
kpi_y = 42

# ===== PAGE TITLE =====
title_vis = vis_container("pagetitle", kpi_start_x, 8, 400, 30, 99)
title_vis["visual"] = {
    "visualType": "textbox",
    "objects": {
        "general": [{"properties": {
            "paragraphs": {"expr": {"Literal": {"Value": "[{\"textRuns\":[{\"value\":\"Executive Overview\",\"textStyle\":{\"fontWeight\":\"bold\",\"fontSize\":\"16px\",\"color\":\"#e2e8f0\"}}]}]"}}},
        }}],
    },
    "visualContainerObjects": {
        "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
        "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
        "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
    },
}
add("definition/pages/exec/visuals/pagetitle/visual.json", title_vis)

for i, (label, entity, prop) in enumerate(kpi_measures):
    x = kpi_start_x + i * (kpi_width + kpi_gap)
    vis = vis_container(f"kpi{i+1}", x, kpi_y, kpi_width, kpi_height, i)
    vis["visual"] = {
        "visualType": KPI_GUID,
        "query": {"queryState": {"measure": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop,
        }]}}},
        "visualContainerObjects": {
            "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
            "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
            "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
            "padding": [{"properties": {
                "top": {"expr": {"Literal": {"Value": "0D"}}},
                "bottom": {"expr": {"Literal": {"Value": "0D"}}},
                "left": {"expr": {"Literal": {"Value": "0D"}}},
                "right": {"expr": {"Literal": {"Value": "0D"}}},
            }}],
        },
        "drillFilterOtherVisuals": True,
    }
    add(f"definition/pages/exec/visuals/kpi{i+1}/visual.json", vis)

# ===== HERO LINE CHART (Revenue over time) =====
hero_y = kpi_y + kpi_height + 12
hero_vis = vis_container("hero_line", kpi_start_x, hero_y, 740, 260, 10)
hero_vis["visual"] = {
    "visualType": "areaChart",
    "query": {"queryState": {
        "Category": {"projections": [{
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Date"}}, "Property": "Month"}},
            "queryRef": "Date.Month", "nativeQueryRef": "Month",
        }]},
        "Y": {"projections": [
            {
                "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "TotalRevenue"}},
                "queryRef": "Sales.TotalRevenue", "nativeQueryRef": "TotalRevenue",
            },
            {
                "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "GrossProfit"}},
                "queryRef": "Sales.GrossProfit", "nativeQueryRef": "GrossProfit",
            },
        ]},
    },
    },
    "objects": {
        "categoryAxis": [{"properties": {
            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
            "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#94a3b8'"}}}}},
        }}],
        "valueAxis": [{"properties": {
            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
            "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#64748b'"}}}}},
            "gridlineColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},
        }}],
        "lineStyles": [{"properties": {
            "strokeWidth": {"expr": {"Literal": {"Value": "2D"}}},
        }}],
        "legend": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "showTitle": {"expr": {"Literal": {"Value": "false"}}},
            "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#94a3b8'"}}}}},
        }}],
    },
    "visualContainerObjects": {
        "title": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": "'Revenue Trend'"}}},
            "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#e2e8f0'"}}}}},
            "fontSize": {"expr": {"Literal": {"Value": "12D"}}},
        }}],
        "background": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#151d2e'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
        "border": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},
        }}],
    },
    "drillFilterOtherVisuals": True,
}
add("definition/pages/exec/visuals/hero_line/visual.json", hero_vis)

# ===== DONUT CHART (Revenue by Region) =====
donut_x = kpi_start_x + 740 + 15
donut_vis = vis_container("donut_region", donut_x, hero_y, 440, 260, 11)
donut_vis["visual"] = {
    "visualType": "donutChart",
    "query": {"queryState": {
        "Category": {"projections": [{
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Region"}}, "Property": "RegionName"}},
            "queryRef": "Region.RegionName", "nativeQueryRef": "RegionName",
        }]},
        "Y": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "TotalRevenue"}},
            "queryRef": "Sales.TotalRevenue", "nativeQueryRef": "TotalRevenue",
        }]},
    }},
    "objects": {
        "legend": [{"properties": {
            "showTitle": {"expr": {"Literal": {"Value": "false"}}},
            "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#94a3b8'"}}}}},
        }}],
        "labels": [{"properties": {
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#94a3b8'"}}}}},
        }}],
    },
    "visualContainerObjects": {
        "title": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": "'Revenue by Region'"}}},
            "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#e2e8f0'"}}}}},
            "fontSize": {"expr": {"Literal": {"Value": "12D"}}},
        }}],
        "background": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#151d2e'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
        "border": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},
        }}],
    },
    "drillFilterOtherVisuals": True,
}
add("definition/pages/exec/visuals/donut_region/visual.json", donut_vis)

# ===== BAR CHART (Revenue by Store) - bottom row =====
bar_y = hero_y + 260 + 10
bar_vis = vis_container("bar_stores", kpi_start_x, bar_y, 580, 260, 12)
bar_vis["visual"] = {
    "visualType": "barChart",
    "query": {"queryState": {
        "Category": {"projections": [{
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Product"}}, "Property": "CategoryName"}},
            "queryRef": "Product.CategoryName", "nativeQueryRef": "CategoryName",
        }]},
        "Y": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "TotalRevenue"}},
            "queryRef": "Sales.TotalRevenue", "nativeQueryRef": "TotalRevenue",
        }]},
    }},
    "objects": {
        "categoryAxis": [{"properties": {"showAxisTitle": {"expr": {"Literal": {"Value": "false"}}}, "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#94a3b8'"}}}}},}}],
        "valueAxis": [{"properties": {"showAxisTitle": {"expr": {"Literal": {"Value": "false"}}}, "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#64748b'"}}}}}, "gridlineColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},}}],
    },
    "visualContainerObjects": {
        "title": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": "'Revenue by Category'"}}},
            "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#e2e8f0'"}}}}},
            "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
        }}],
        "background": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#151d2e'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
        "border": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},
        }}],
    },
    "drillFilterOtherVisuals": True,
}
add("definition/pages/exec/visuals/bar_stores/visual.json", bar_vis)

# ===== SECOND BOTTOM PANEL (Gross Profit by Store) =====
bar2_x = kpi_start_x + 580 + 15
bar2_vis = vis_container("bar_profit", bar2_x, bar_y, 600, 260, 13)
bar2_vis["visual"] = {
    "visualType": "columnChart",
    "query": {"queryState": {
        "Category": {"projections": [{
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Region"}}, "Property": "RegionName"}},
            "queryRef": "Region.RegionName", "nativeQueryRef": "RegionName",
        }]},
        "Y": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "GrossProfit"}},
            "queryRef": "Sales.GrossProfit", "nativeQueryRef": "GrossProfit",
        }]},
    }},
    "objects": {
        "categoryAxis": [{"properties": {"showAxisTitle": {"expr": {"Literal": {"Value": "false"}}}, "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#94a3b8'"}}}}},}}],
        "valueAxis": [{"properties": {"showAxisTitle": {"expr": {"Literal": {"Value": "false"}}}, "labelColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#64748b'"}}}}}, "gridlineColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},}}],
    },
    "visualContainerObjects": {
        "title": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": "'Gross Profit by Region'"}}},
            "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#e2e8f0'"}}}}},
            "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
        }}],
        "background": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#151d2e'"}}}}},
            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
        }}],
        "border": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1e293b'"}}}}},
        }}],
    },
    "drillFilterOtherVisuals": True,
}
add("definition/pages/exec/visuals/bar_profit/visual.json", bar2_vis)

# Custom visual resources
add_bin(f"CustomVisuals/{KPI_GUID}/package.json", package_json_bytes)
add_bin(f"CustomVisuals/{KPI_GUID}/resources/{KPI_GUID}.pbiviz.json", pbiviz_json)

# Deploy
print(f"Creating: {DIAG_NAME}")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items", headers=headers,
                  json={"displayName": DIAG_NAME, "type": "Report", "definition": {"parts": parts}}, timeout=60)
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
report_id = next((i["id"] for i in r.json()["value"] if i["displayName"] == DIAG_NAME), None)
print(f"Report ID: {report_id}")

# Screenshot with transparent embed
embed_url = _get_embed_url(workspace_id, report_id, {"Authorization": f"Bearer {token}"})
html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
    '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
    '<style>*{margin:0;padding:0}body{overflow:hidden;background:#0f1623}#r{width:1280px;height:720px}</style>'
    '</head><body><div id="r"></div><script>'
    'const m=window["powerbi-client"].models;'
    f'const c={{type:"report",tokenType:m.TokenType.Aad,accessToken:"{token}",'
    f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"exec",'
    'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
    'background:m.BackgroundType.Transparent,'
    'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
    'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
    'const r=powerbi.embed(document.getElementById("r"),c);'
    'r.on("rendered",()=>{document.title="RENDERED"});'
    'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
    '</script></body></html>'
)
html_path = evidence_dir / '_exec.html'
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
    page.screenshot(path=str(evidence_dir / 'exec_overview_v1.png'))
    browser.close()
html_path.unlink(missing_ok=True)
print("Done! Check exec_overview_v1.png")
