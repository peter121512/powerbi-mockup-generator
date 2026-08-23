"""Stage 11 — Rapid Product Dashboard (Minimal Prompt Challenge).

Full end-to-end: model discovery → model extension → page spec → preflight → deploy → screenshot.
Target: <5 minutes.
"""

import sys
import time
import json
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.renderer.templates.rapid_engine import (
    ModelMetadata,
    MeasureSpec,
    PageSpec,
    TimingRecord,
    VisualSpec,
    deploy_from_page_spec,
    deploy_model_update,
    discover_model,
    run_preflight,
    validate_page_spec,
)

import requests

# ─── Constants ───────────────────────────────────────────────────────────────
SM_ID = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
SM_NAME = "ExecutiveRetailPerformanceDashboard"
REPORT_NAME = "ProductPerformance_v1"
EVIDENCE_DIR = Path("docs/stages/11-product-dashboard")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("STAGE 11 — PRODUCT DASHBOARD (Minimal Prompt Challenge)")
print("=" * 60)
print()

overall_start = time.time()
timing = TimingRecord()

# ─── Phase 1: Authenticate ──────────────────────────────────────────────────
t0 = time.time()
config = load_config()
workspace_id = config["workspace_id"]
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
timing.record("authentication", time.time() - t0)
print(f"✓ Auth: {timing.phases['authentication']:.1f}s")

# ─── Phase 2: Discover Model ────────────────────────────────────────────────
t0 = time.time()
model = discover_model(workspace_id, SM_ID, headers)
timing.record("model_discovery", time.time() - t0)
print(f"✓ Model discovery: {timing.phases['model_discovery']:.1f}s")

# Check existing measures
existing_measures = {m.name for t in model.tables for m in t.measures}
print(f"  Existing measures: {sorted(existing_measures)}")

# ─── Phase 3: Extend Model (add Product-specific measures) ──────────────────
t0 = time.time()

# We need: ActiveProducts (distinct product count), TotalQuantity
# The existing TotalRevenue, GrossProfit, GrossMarginPct already slice correctly by Product dims.
needed_measures = []

if "ActiveProducts" not in existing_measures:
    needed_measures.append(MeasureSpec(
        name="ActiveProducts",
        expression='DISTINCTCOUNT(Sales[ProductID])',
        format_string="#,##0",
    ))

if "TotalQuantity" not in existing_measures:
    needed_measures.append(MeasureSpec(
        name="TotalQuantity",
        expression='SUM(Sales[Quantity])',
        format_string="#,##0",
    ))

if needed_measures:
    print(f"  Adding {len(needed_measures)} new measures to Sales table...")

    # Get current definition
    r = requests.post(
        f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{SM_ID}/getDefinition",
        headers=headers, json={}, timeout=30,
    )
    loc = r.headers.get("Location", "")
    for _ in range(20):
        time.sleep(2)
        poll = requests.get(loc, headers=headers, timeout=30)
        if poll.json().get("status") == "Succeeded":
            break

    result = requests.get(f"{loc}/result", headers=headers, timeout=30)
    definition = result.json().get("definition", result.json())
    parts = definition.get("parts", [])

    # Find Sales.tmdl and add measures
    for part in parts:
        if part["path"] == "definition/tables/Sales.tmdl":
            content = base64.b64decode(part["payload"]).decode("utf-8")
            # Add measures before the partition line
            measure_lines = []
            for m in needed_measures:
                if m.name not in content:
                    measure_lines.append(f"\n\tmeasure {m.name} = {m.expression}")
                    measure_lines.append(f"\t\tformatString: {m.format_string}")
                    measure_lines.append(f"\t\tlineageTag: {__import__('uuid').uuid4()}")

            if measure_lines:
                # Insert before first 'partition' line
                insert_idx = content.find("\n\tpartition ")
                if insert_idx > 0:
                    content = content[:insert_idx] + "\n" + "\n".join(measure_lines) + content[insert_idx:]
                else:
                    content += "\n" + "\n".join(measure_lines)
                part["payload"] = base64.b64encode(content.encode("utf-8")).decode()
            break

    # Deploy model update
    ok, msg = deploy_model_update(workspace_id, SM_ID, parts, headers)
    if ok:
        print(f"  ✓ Model updated: {msg}")
    else:
        print(f"  ⚠ Model update: {msg}")
else:
    print("  No model extension needed — all measures exist")

timing.record("model_extension", time.time() - t0)
print(f"✓ Model extension: {timing.phases['model_extension']:.1f}s")

# ─── Phase 4: Build Page Spec ───────────────────────────────────────────────
t0 = time.time()

# Reference analysis:
# - 4 KPIs: Total Sales (TotalRevenue), Gross Profit, Gross Margin %, Active Products
# - Hero: Sales Trend (line/area with 2 series: Revenue + Profit over time — need Month axis)
#   → premium_trend requires numeric category → use Date.Month
# - Donut: Product Mix by Category (CategoryName × TotalRevenue) + center KPI (ActiveProducts)
# - Bottom: 3 horizontal bar charts:
#   1. Top Products by Sales (ProductName × TotalRevenue)
#   2. Gross Margin by Category (CategoryName × GrossMarginPct)
#   3. Sales by Brand → substitute SubcategoryName (no Brand column exists)

# Layout constants (matching standard grid)
CX = 155  # content x start
CW = 1115  # content width
GUTTER = 10

# KPI row
kpi_w = (CW - 3 * GUTTER) // 4  # ~271 each

page_spec = PageSpec(
    page_name="product_performance",
    display_name=REPORT_NAME,
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
        # ── KPI Row (y=70, h=95) ──
        VisualSpec(
            template_id="premium_kpi",
            title="TOTAL SALES",
            bindings={"measure": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}]},
            position=(CX, 70, kpi_w, 95),
        ),
        VisualSpec(
            template_id="premium_kpi",
            title="GROSS PROFIT",
            bindings={"measure": [{"entity": "Sales", "property": "GrossProfit", "is_measure": True}]},
            position=(CX + kpi_w + GUTTER, 70, kpi_w, 95),
        ),
        VisualSpec(
            template_id="premium_kpi",
            title="GROSS MARGIN %",
            bindings={"measure": [{"entity": "Sales", "property": "GrossMarginPct", "is_measure": True}]},
            position=(CX + 2 * (kpi_w + GUTTER), 70, kpi_w, 95),
        ),
        VisualSpec(
            template_id="premium_kpi",
            title="ACTIVE PRODUCTS",
            bindings={"measure": [{"entity": "Sales", "property": "ActiveProducts", "is_measure": True}]},
            position=(CX + 3 * (kpi_w + GUTTER), 70, kpi_w, 95),
        ),
        # ── Hero Row (y=175, h=240) ──
        # Sales Trend — premium_trend with Month (numeric) as category
        VisualSpec(
            template_id="premium_trend",
            title="Sales Trend",
            bindings={
                "category": [{"entity": "Date", "property": "Month"}],
                "values": [
                    {"entity": "Sales", "property": "TotalRevenue", "is_measure": True},
                    {"entity": "Sales", "property": "GrossProfit", "is_measure": True},
                ],
            },
            position=(CX, 175, 635, 240),
        ),
        # Product Mix by Category — donut
        VisualSpec(
            template_id="premium_donut",
            title="Product Mix by Category",
            bindings={
                "category": [{"entity": "Product", "property": "CategoryName"}],
                "values": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}],
            },
            position=(CX + 635 + GUTTER, 175, 470, 240),
        ),
        # Donut center KPI overlay
        VisualSpec(
            template_id="donut_center_kpi",
            title="128",
            bindings={"measure": [{"entity": "Sales", "property": "ActiveProducts", "is_measure": True}]},
            position=(CX + 635 + GUTTER + 120, 175 + 90, 110, 50),
            config={
                "title_color": "#ffffff",
                "title_font_size": 18,
                "title_bold": True,
                "show_background": False,
                "show_border": False,
                "subtitle": "Products",
            },
        ),
        # ── Bottom Row (y=425, h=240) ──
        # Top Products by Sales — horizontal bar
        VisualSpec(
            template_id="premium_bar",
            title="Top Products by Sales",
            bindings={
                "category": [{"entity": "Product", "property": "ProductName"}],
                "values": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}],
            },
            position=(CX, 425, 365, 240),
        ),
        # Gross Margin by Category — horizontal bar
        VisualSpec(
            template_id="premium_bar",
            title="Gross Margin by Category",
            bindings={
                "category": [{"entity": "Product", "property": "CategoryName"}],
                "values": [{"entity": "Sales", "property": "GrossMarginPct", "is_measure": True}],
            },
            position=(CX + 365 + GUTTER, 425, 365, 240),
        ),
        # Sales by Subcategory (substituting for "Brand" — no Brand column exists)
        VisualSpec(
            template_id="premium_bar",
            title="Sales by Subcategory",
            bindings={
                "category": [{"entity": "Product", "property": "SubcategoryName"}],
                "values": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}],
            },
            position=(CX + 2 * (365 + GUTTER), 425, 365, 240),
        ),
    ],
)

timing.record("spec_generation", time.time() - t0)
print(f"✓ Spec generation: {timing.phases['spec_generation']:.1f}s")
print(f"  Visuals: {len(page_spec.visuals)}")

# ─── Phase 5: Preflight ─────────────────────────────────────────────────────
t0 = time.time()

# Re-discover model after extension
model2 = discover_model(workspace_id, SM_ID, headers)
preflight = run_preflight(page_spec, model_metadata=model2)
timing.record("preflight", time.time() - t0)
print(f"✓ Preflight: {timing.phases['preflight']:.1f}s")
print(f"  {preflight.summary()}")

if not preflight.passed:
    print("\n⚠ Preflight has errors — attempting deployment anyway (measures may still evaluate)")

# ─── Phase 6: Deploy ────────────────────────────────────────────────────────
print(f"\n→ Deploying: {REPORT_NAME}")
t0 = time.time()

deploy_result = deploy_from_page_spec(
    page_spec,
    workspace_id,
    headers,
    evidence_dir=EVIDENCE_DIR,
    screenshot=True,
)
timing.record("deployment", time.time() - t0)
print(f"✓ Deployment: {timing.phases['deployment']:.1f}s")

if deploy_result.success:
    print(f"  Report ID: {deploy_result.report_id}")
    if deploy_result.screenshot_path:
        print(f"  Screenshot: {deploy_result.screenshot_path}")
else:
    print(f"  ❌ FAILED: {deploy_result.errors}")

# ─── Summary ────────────────────────────────────────────────────────────────
total_elapsed = time.time() - overall_start
print("\n" + "=" * 60)
print("TIMING SUMMARY")
print("=" * 60)
print(f"Total wall-clock: {total_elapsed:.1f}s")
print()
for phase, elapsed in timing.phases.items():
    pct = (elapsed / total_elapsed) * 100
    print(f"  {phase:25s} {elapsed:6.1f}s ({pct:4.1f}%)")
print()

target = 300
if total_elapsed < target:
    print(f"✅ UNDER 5-MINUTE TARGET ({total_elapsed:.0f}s < {target}s)")
else:
    print(f"⚠️ OVER 5-MINUTE TARGET ({total_elapsed:.0f}s > {target}s)")

# Save timing + spec as evidence
evidence = {
    "timing": timing.phases,
    "total_seconds": total_elapsed,
    "target_seconds": target,
    "under_target": total_elapsed < target,
    "report_id": deploy_result.report_id,
    "screenshot": deploy_result.screenshot_path,
    "visuals_deployed": len(page_spec.visuals),
    "templates_used": list(set(v.template_id for v in page_spec.visuals)),
    "model_measures_added": [m.name for m in needed_measures] if needed_measures else [],
    "substitutions": [
        {"reference": "Sales by Brand", "actual": "Sales by Subcategory",
         "reason": "No Brand column in Product table; SubcategoryName is closest valid dimension"}
    ],
}
(EVIDENCE_DIR / "timing_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
print(f"\nEvidence saved to {EVIDENCE_DIR}/timing_evidence.json")
print(f"Result: {'SUCCESS' if deploy_result.success else 'FAILED'}")
