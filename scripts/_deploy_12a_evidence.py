"""Deploy Financial + Customer dashboards for Stage 12A evidence."""
import sys
import time
import shutil
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.renderer.templates.registry import DesignTokens, TemplateRegistry
from pbi_gen.renderer.templates.builder import PageBuilder
from pbi_gen.renderer.templates.financial_config import financial_page_shell, financial_visual_bindings
from pbi_gen.renderer.templates.customer_config import customer_page_shell, customer_visual_bindings
from pbi_gen.renderer.templates.rapid_engine import _auto_load_visual_archives, _capture_screenshot

SM_ID = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
SM_NAME = "ExecutiveRetailPerformanceDashboard"
EVIDENCE = Path("docs/stages/12a-responsive-visual-system-cleanup")
EVIDENCE.mkdir(parents=True, exist_ok=True)

config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

tokens = DesignTokens()
reg = TemplateRegistry.default()


def deploy_dashboard(name, shell_fn, bindings_fn, output_filename):
    print(f"Deploying {name}...")
    t0 = time.time()

    shell = shell_fn()
    builder = PageBuilder(
        shell=shell, tokens=tokens, registry=reg,
        semantic_model_id=SM_ID, semantic_model_name=SM_NAME,
        report_name=f"{name}_v1",
    )
    for b in bindings_fn():
        builder.add_visual(b)

    visual_archives = _auto_load_visual_archives(builder.custom_visual_packages())
    parts = builder.build_pbir_parts_with_visuals(visual_archives)

    report_display = f"{name}_v1"

    # Delete existing
    r = requests.get(
        f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report",
        headers=headers, timeout=30,
    )
    for item in r.json().get("value", []):
        if item["displayName"] == report_display:
            item_id = item["id"]
            requests.delete(
                f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item_id}",
                headers=headers, timeout=30,
            )
            time.sleep(3)
            break

    # Create
    r = requests.post(
        f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items",
        headers=headers,
        json={"displayName": report_display, "type": "Report", "definition": {"parts": parts}},
        timeout=60,
    )
    if r.status_code == 202:
        loc = r.headers.get("Location", "")
        for _ in range(20):
            time.sleep(2)
            poll = requests.get(loc, headers=headers, timeout=30)
            if poll.json().get("status") == "Succeeded":
                break
    else:
        print(f"  Error {r.status_code}: {r.text[:200]}")
        return

    time.sleep(2)
    r = requests.get(
        f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type=Report",
        headers=headers, timeout=30,
    )
    report_id = next(
        (i["id"] for i in r.json()["value"] if i["displayName"] == report_display),
        None,
    )

    if report_id:
        screenshot = _capture_screenshot(
            workspace_id, report_id, SM_ID, shell.page_name, headers, EVIDENCE,
        )
        dest = str(EVIDENCE / output_filename)
        shutil.move(screenshot, dest)
        print(f"  ✓ Done in {time.time()-t0:.1f}s — {dest}")
    else:
        print("  ✗ FAILED")


deploy_dashboard("FinancialPerformance", financial_page_shell, financial_visual_bindings, "financial_v2.png")
deploy_dashboard("CustomerPerformance", customer_page_shell, customer_visual_bindings, "customer_v2.png")

# Also redeploy Product using the updated composite
print("\nDeploying Product (via rapid engine)...")
t0 = time.time()

# Import and run the product deploy which now uses make_donut_composite
# We can't just import it (it runs inline), so let's build manually
from pbi_gen.renderer.templates.rapid_engine import (
    PageSpec, VisualSpec, make_donut_composite, deploy_from_page_spec,
)

CX = 155
GUTTER = 10
kpi_w = (1115 - 3 * GUTTER) // 4

product_spec = PageSpec(
    page_name="product_performance",
    display_name="ProductPerformance_v1",
    title="Product Performance",
    subtitle="Sales · Profitability · Product Mix",
    nav_items=[
        ("\U0001f3e0 Overview", "overview"),
        ("\U0001f4b0 Financial", "financial"),
        ("\U0001f465 Customers", "customers"),
        ("\U0001f4e6 Products", "products"),
    ],
    active_nav="products",
    slicers=[
        {"entity": "Date", "property": "Year"},
        {"entity": "Product", "property": "CategoryName"},
    ],
    semantic_model_id=SM_ID,
    semantic_model_name=SM_NAME,
    visuals=[
        VisualSpec(template_id="premium_kpi", title="TOTAL SALES",
                   bindings={"measure": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}]},
                   position=(CX, 70, kpi_w, 95)),
        VisualSpec(template_id="premium_kpi", title="GROSS PROFIT",
                   bindings={"measure": [{"entity": "Sales", "property": "GrossProfit", "is_measure": True}]},
                   position=(CX + kpi_w + GUTTER, 70, kpi_w, 95)),
        VisualSpec(template_id="premium_kpi", title="GROSS MARGIN %",
                   bindings={"measure": [{"entity": "Sales", "property": "GrossMarginPct", "is_measure": True}]},
                   position=(CX + 2*(kpi_w + GUTTER), 70, kpi_w, 95)),
        VisualSpec(template_id="premium_kpi", title="ACTIVE PRODUCTS",
                   bindings={"measure": [{"entity": "Sales", "property": "ActiveProducts", "is_measure": True}]},
                   position=(CX + 3*(kpi_w + GUTTER), 70, kpi_w, 95)),
        VisualSpec(template_id="premium_trend", title="Sales Trend",
                   bindings={"category": [{"entity": "Date", "property": "Month"}],
                             "values": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True},
                                        {"entity": "Sales", "property": "GrossProfit", "is_measure": True}]},
                   position=(CX, 175, 635, 240)),
        *make_donut_composite(
            donut_position=(CX + 635 + GUTTER, 175, 470, 240),
            donut_title="Product Mix by Category",
            donut_category={"entity": "Product", "property": "CategoryName"},
            donut_measure={"entity": "Sales", "property": "TotalRevenue", "is_measure": True},
            center_title="128",
            center_measure={"entity": "Sales", "property": "ActiveProducts", "is_measure": True},
            center_subtitle="Products",
        ),
        VisualSpec(template_id="premium_bar", title="Top Products by Sales",
                   bindings={"category": [{"entity": "Product", "property": "ProductName"}],
                             "values": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}]},
                   position=(CX, 425, 365, 240)),
        VisualSpec(template_id="premium_bar", title="Gross Margin by Category",
                   bindings={"category": [{"entity": "Product", "property": "CategoryName"}],
                             "values": [{"entity": "Sales", "property": "GrossMarginPct", "is_measure": True}]},
                   position=(CX + 365 + GUTTER, 425, 365, 240)),
        VisualSpec(template_id="premium_bar", title="Sales by Subcategory",
                   bindings={"category": [{"entity": "Product", "property": "SubcategoryName"}],
                             "values": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}]},
                   position=(CX + 2*(365 + GUTTER), 425, 365, 240)),
    ],
)

result = deploy_from_page_spec(product_spec, workspace_id, headers, evidence_dir=EVIDENCE, screenshot=True)
if result.success and result.screenshot_path:
    shutil.move(result.screenshot_path, str(EVIDENCE / "product_v2.png"))
    print(f"  ✓ Done in {time.time()-t0:.1f}s")
else:
    print(f"  ✗ {result.errors}")

print("\nAll deployments complete!")
