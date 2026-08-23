"""Stage 10 timed rehearsal — full model discovery + report deployment.

Uses the existing semantic model (ExecutiveRetailPerformanceDashboard) and
exercises the rapid engine end-to-end:
  1. Authenticate
  2. Discover existing model metadata
  3. Build a PageSpec from a ReferenceSpec (generic, non-Product)
  4. Run preflight validation
  5. Deploy report via Fabric REST API
  6. Capture headless screenshot
  7. Report timing breakdown

This is NOT a Product dashboard. It uses the existing Sales/Customer model
to prove the engine can execute rapidly.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE
from pbi_gen.renderer.templates.rapid_engine import (
    ReferenceSpec,
    ReferenceVisual,
    TimingRecord,
    deploy_from_page_spec,
    discover_model,
    reference_to_page_spec,
    run_preflight,
    validate_page_spec,
)

# ─── Configuration ───────────────────────────────────────────────────────────
SM_ID = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"
SM_NAME = "ExecutiveRetailPerformanceDashboard"
REPORT_NAME = "Stage10_Rehearsal_v1"
EVIDENCE_DIR = Path("docs/stages/10-product-dashboard-readiness")

print("=" * 60)
print("STAGE 10 — TIMED REHEARSAL (Full Model+Report Path)")
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
print(f"✓ Authentication: {timing.phases['authentication']:.1f}s")

# ─── Phase 2: Model Discovery ───────────────────────────────────────────────
t0 = time.time()
model = discover_model(workspace_id, SM_ID, headers)
timing.record("model_discovery", time.time() - t0)
print(f"✓ Model discovery: {timing.phases['model_discovery']:.1f}s")
print(f"  Tables: {[t.name for t in model.tables]}")
print(f"  Measures: {[m.name for m in model.all_measures()][:8]}...")
print(f"  Relationships: {len(model.relationships)}")
print()

# ─── Phase 3: Build ReferenceSpec (simulate minimal-prompt input) ────────────
t0 = time.time()

# This simulates what the reference-to-spec mapper would produce from
# a terse instruction. Using existing Sales model data.
ref = ReferenceSpec(
    title="Sales Overview",
    subtitle="Revenue · Volume · Regional Performance",
    visuals=[
        # KPI row — 4 metrics
        ReferenceVisual(
            intent="headline_metric", title="Total Revenue",
            row="kpi", measures=["TotalRevenue"],
        ),
        ReferenceVisual(
            intent="headline_metric", title="Gross Profit",
            row="kpi", measures=["GrossProfit"],
        ),
        ReferenceVisual(
            intent="headline_metric", title="Total Cost",
            row="kpi", measures=["TotalCost"],
        ),
        ReferenceVisual(
            intent="headline_metric", title="Gross Margin",
            row="kpi", measures=["GrossMarginPct"],
        ),
        # Hero — revenue trend by category (column chart since no date axis)
        ReferenceVisual(
            intent="categorical_comparison", title="Revenue by Category",
            row="hero", measures=["TotalRevenue"], dimensions=["CategoryName"],
            width_fraction=0.57,
        ),
        # Hero companion — composition donut
        ReferenceVisual(
            intent="composition_share", title="Revenue Share by Region",
            row="hero", measures=["TotalRevenue"], dimensions=["RegionName"],
            width_fraction=0.43,
        ),
        # Bottom row
        ReferenceVisual(
            intent="ranking", title="Revenue by Region",
            row="bottom", measures=["TotalRevenue"], dimensions=["RegionName"],
            prefer_horizontal=True,
        ),
        ReferenceVisual(
            intent="categorical_comparison", title="Revenue by Store",
            row="bottom", measures=["TotalRevenue"], dimensions=["StoreName"],
        ),
        ReferenceVisual(
            intent="narrative_insight", title="Key Insights",
            row="bottom", measures=["TotalRevenue"],
        ),
    ],
    slicer_fields=["Year"],
)

# Convert reference to page spec
page_spec = reference_to_page_spec(
    ref, model,
    semantic_model_id=SM_ID,
    semantic_model_name=SM_NAME,
    page_name="sales_overview_rehearsal",
    active_nav="overview",
)
page_spec.display_name = REPORT_NAME  # Override for unique report name

timing.record("spec_generation", time.time() - t0)
print(f"✓ Spec generation: {timing.phases['spec_generation']:.1f}s")
print(f"  Visuals: {len(page_spec.visuals)}")
for v in page_spec.visuals:
    print(f"    {v.template_id}: {v.title}")

# ─── Phase 4: Preflight Validation ──────────────────────────────────────────
t0 = time.time()
preflight = run_preflight(page_spec, model_metadata=model)
timing.record("preflight", time.time() - t0)
print(f"\n✓ Preflight: {timing.phases['preflight']:.1f}s")
print(f"  {preflight.summary()}")

if not preflight.passed:
    print("\n❌ PREFLIGHT FAILED — aborting deployment")
    print(timing.summary())
    sys.exit(1)

# ─── Phase 5: Deploy ────────────────────────────────────────────────────────
print(f"\n→ Deploying: {REPORT_NAME}")
t0 = time.time()

deploy_result = deploy_from_page_spec(
    page_spec,
    workspace_id,
    headers,
    evidence_dir=EVIDENCE_DIR,
    screenshot=True,
)

timing.record("deployment_total", time.time() - t0)

# Merge deployment sub-timings
for phase, elapsed in deploy_result.timing.phases.items():
    timing.record(f"  deploy.{phase}", elapsed)

print(f"✓ Deployment: {timing.phases['deployment_total']:.1f}s")
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
    if not phase.startswith("  "):
        pct = (elapsed / total_elapsed) * 100
        print(f"  {phase:25s} {elapsed:6.1f}s ({pct:4.1f}%)")
print()

target = 300  # 5 minutes
if total_elapsed < target:
    print(f"✅ UNDER 5-MINUTE TARGET ({total_elapsed:.0f}s < {target}s)")
else:
    print(f"⚠️ OVER 5-MINUTE TARGET ({total_elapsed:.0f}s > {target}s)")
    print(f"   Bottleneck: {max(timing.phases, key=timing.phases.get)}")

print()
print(f"Result: {'SUCCESS' if deploy_result.success else 'FAILED'}")
