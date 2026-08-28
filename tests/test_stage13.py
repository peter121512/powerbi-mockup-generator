"""Stage 13 unit tests — conversational image-first design workflow.

Standalone runnable script (repo style). Uses the deterministic StubImageAdapter
so no network / OpenAI key is required. Live OpenAI + deploy evidence lives in
scripts/_stage13_scenarios.py.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.design import (
    ApprovalState,
    DashboardMockupService,
    DesignWorkflow,
    ImplementationClass,
    StubImageAdapter,
    classify_visual,
    context_from_description,
    is_approval_intent,
    profile_spreadsheet,
)
from pbi_gen.design.build_handoff import spec_to_report_spec
from pbi_gen.renderer.templates.registry import TemplateRegistry
from pbi_gen.renderer.templates.report_builder import build_report_spec_parts

passed = 0
failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  \u2713 {label}")
    else:
        failed += 1
        print(f"  \u2717 {label}  {detail}")


def _wf():
    return DesignWorkflow(DashboardMockupService(StubImageAdapter()))


# ─── 1. DataContext from description ──────────────────────────────────────────
print("\n1. DataContext from description")
ctx = context_from_description(
    "I have invoice-level finance data with customer, product, region, invoice date, "
    "revenue, cost, budget and currency. I want a CFO dashboard."
)
names = [f.lower() for f in ctx.field_names()]
check("fields extracted", len(ctx.fields) >= 4, f"{ctx.field_names()}")
check("revenue is a measure", "revenue" in [m.lower() for m in ctx.candidate_measures])
check("invoice date is a date field", any("date" in d.lower() for d in ctx.date_fields))
check("records assumptions", len(ctx.assumptions) >= 1)
check("confidence in (0,1]", 0 < ctx.confidence <= 1.0)


# ─── 2. Spreadsheet profiler (CSV) ────────────────────────────────────────────
print("\n2. Spreadsheet profiler (CSV)")
csv_text = (
    "InvoiceDate,Region,Product,Revenue,Cost,Units\n"
    "2024-01-15,London,Widget,1200.50,800.00,10\n"
    "2024-02-10,Scotland,Gadget,2400.00,1500.00,20\n"
    "2024-03-05,London,Widget,900.25,600.00,7\n"
)
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "sales.csv"
    p.write_text(csv_text, encoding="utf-8")
    dc = profile_spreadsheet(p)
    fmap = {f.name: f for f in dc.fields}
    check("all columns profiled", set(fmap) == {"InvoiceDate", "Region", "Product", "Revenue", "Cost", "Units"})
    check("InvoiceDate -> date", fmap["InvoiceDate"].field_type.value == "date")
    check("Revenue -> measure", fmap["Revenue"].role.value == "measure")
    check("Region -> dimension", fmap["Region"].role.value == "dimension")
    check("row_count captured", dc.sources[0].row_count == 3)
    check("Revenue in candidate_measures", "Revenue" in dc.candidate_measures)
    check("Region in candidate_dimensions", "Region" in dc.candidate_dimensions)


# ─── 3. Spreadsheet profiler (XLSX, multi-sheet) ──────────────────────────────
print("\n3. Spreadsheet profiler (XLSX multi-sheet)")
try:
    from openpyxl import Workbook
    with tempfile.TemporaryDirectory() as td:
        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Sales"
        ws1.append(["Date", "Region", "Amount"])
        ws1.append(["2024-01-01", "London", 100])
        ws1.append(["2024-02-01", "Wales", 200])
        ws2 = wb.create_sheet("Customers")
        ws2.append(["CustomerID", "Segment", "LTV"])
        ws2.append([1, "Enterprise", 5000])
        xp = Path(td) / "book.xlsx"
        wb.save(xp)
        dc = profile_spreadsheet(xp)
        entities = set(dc.entities)
        check("two sheets as entities", entities == {"Sales", "Customers"}, f"{entities}")
        check("LTV is a measure", "LTV" in dc.candidate_measures)
        check("Segment is a dimension", "Segment" in dc.candidate_dimensions)
except ImportError:
    check("openpyxl available", False, "openpyxl not installed")


# ─── 4. Feasibility classifier — four classes ────────────────────────────────
print("\n4. Feasibility classifier — four classes")
c1 = classify_visual("time_trend", "line chart")
check("trend -> EXISTING_TEMPLATE", c1.implementation_class == ImplementationClass.EXISTING_TEMPLATE)
check("trend -> premium_trend", c1.candidate_template == "premium_trend")
c2 = classify_visual("geospatial", "scatter map")
check("scatter map -> NATIVE_POWERBI", c2.implementation_class == ImplementationClass.NATIVE_POWERBI)
c3 = classify_visual("variance", "bespoke variance bridge with outer target ring", user_forced_deviation=True)
check("bespoke -> CUSTOM_VISUAL_REQUIRED", c3.implementation_class == ImplementationClass.CUSTOM_VISUAL_REQUIRED)
c4 = classify_visual("globe", "rotating 3D globe with real-time physics")
check("3D globe -> NEEDS_REDESIGN", c4.implementation_class == ImplementationClass.NEEDS_REDESIGN)
check("feasibility confidence tracked", 0 < c1.confidence <= 1.0)
# 'bar' must not trigger the AR infeasible signal
cbar = classify_visual("ranking", "horizontal bar chart")
check("'bar' not falsely infeasible", cbar.implementation_class != ImplementationClass.NEEDS_REDESIGN)


# ─── 5. Approval gate ─────────────────────────────────────────────────────────
print("\n5. Approval gate")
check("'approved' is approval", is_approval_intent("approved"))
check("'build it' is approval", is_approval_intent("ok build it"))
check("'go ahead with this' is approval", is_approval_intent("go ahead with this"))
check("'make the kpis smaller' is NOT approval", not is_approval_intent("make the kpis smaller"))


# ─── 6. Session: no PBI artifact before approval; state preserved ─────────────
print("\n6. Conversational session + incremental revisions")
wf = _wf()
s = wf.start_session("executive retention dashboard for SaaS ARR MRR churn",
                     data_context=context_from_description(
                         "SaaS data with customer, plan, ARR, MRR, churn date, region, sales owner"))
r0 = wf.generate_initial_mockup(s)
check("approval state DESIGNING before approval", s.approval_state == ApprovalState.DESIGNING)
check("no design_spec before approval", s.design_spec is None)
check("initial revision created", r0.revision_number == 1)
n_visuals_before = len(s.proposed_visuals)
kpi_titles_before = [v.title for v in s.proposed_visuals if v.region == "kpi_row"]

# colour change preserves visuals
wf.revise(s, "use teal instead of purple")
check("palette changed to teal", s.palette["accent"] == "#14b8a6")
check("visuals preserved on colour change", len(s.proposed_visuals) == n_visuals_before)
check("KPIs unchanged on colour change",
      [v.title for v in s.proposed_visuals if v.region == "kpi_row"] == kpi_titles_before)

# revision count grows
check("two revisions now", len(s.revisions) == 2)


# ─── 7. Deliberate template deviation -> CustomVisualRequirement ──────────────
print("\n7. Deliberate deviation produces CustomVisualRequirement")
wf.revise(s, "make the margin visual a bespoke radial bar with an outer target ring")
check("a CVR was produced", len(s.custom_visual_requirements) >= 1)
cvr = s.custom_visual_requirements[-1]
check("CVR has an id", cvr.requirement_id.startswith("cvr_"))
check("CVR has data roles", len(cvr.data_roles) >= 1)
check("CVR records reason templates insufficient", bool(cvr.reason_templates_insufficient))
bespoke_visuals = [v for v in s.proposed_visuals
                   if v.classification and v.classification.implementation_class == ImplementationClass.CUSTOM_VISUAL_REQUIRED]
check("bespoke NOT downgraded to a standard template", len(bespoke_visuals) >= 1)


# ─── 8. Feasibility guardrail ─────────────────────────────────────────────────
print("\n8. Feasibility guardrail (no false promise)")
wf.revise(s, "add a rotating 3D globe with real-time physics")
last = s.proposed_visuals[-1]
check("infeasible request -> NEEDS_REDESIGN", last.classification.implementation_class == ImplementationClass.NEEDS_REDESIGN)


# ─── 9. Approval -> DashboardDesignSpec ──────────────────────────────────────
print("\n9. Approval produces a structured DashboardDesignSpec")
check("approval intent detected", is_approval_intent("approved, build it"))
spec = wf.approve(s, page_title="SaaS Retention", page_subtitle="Executive retention")
check("approval state APPROVED", s.approval_state == ApprovalState.APPROVED)
check("design_spec created", spec is not None)
check("spec has visuals", len(spec.visuals) >= 5)
check("spec maps every visual to a class",
      all(v.classification for v in spec.visuals))
check("spec carries CVRs", len(spec.custom_visual_requirements) >= 1)
check("spec surfaces NEEDS_REDESIGN gap", len(spec.feasibility_gaps) >= 1)
summary = spec.implementation_summary()
check("impl summary covers classes", "EXISTING_TEMPLATE" in summary)


# ─── 10. Handoff builds a valid 12B ReportSpec ───────────────────────────────
print("\n10. Approved spec -> buildable 12B ReportSpec")
rspec, br = spec_to_report_spec(spec)
parts = build_report_spec_parts(rspec, TemplateRegistry.default())
check("report parts generated", len(parts) > 15)
check("one page", len([p for p in parts if p["path"].endswith("/page.json")]) == 1)
check("built visuals recorded", len(br.built_visuals) >= 5)
check("pending custom visuals recorded", len(br.pending_custom_visuals) >= 1)
check("redesign gaps recorded", len(br.redesign_gaps) >= 1)
check("bound to shared semantic model",
      rspec.semantic_model_id == "b731eda9-c402-42c4-ad27-f4641c7d6bcd")


# ─── 11. Stub determinism ────────────────────────────────────────────────────
print("\n11. Stub image adapter determinism")
a = StubImageAdapter()
img1 = a.generate("prompt X")
img2 = a.generate("prompt X")
img3 = a.generate("different prompt")
check("same prompt -> same bytes", img1 == img2)
check("different prompt -> different bytes", img1 != img3)
check("valid PNG signature", img1[:8] == b"\x89PNG\r\n\x1a\n")


# ─── 12. Stage 12A/12B systems intact ────────────────────────────────────────
print("\n12. Stage 12A/12B systems intact")
from pbi_gen.renderer.templates.canonical_report import build_canonical_report_spec
from pbi_gen.deploy.service import DeploymentService, DeploymentAction
cspec = build_canonical_report_spec()
cparts = build_report_spec_parts(cspec, TemplateRegistry.default())
check("canonical report still builds (4 pages)",
      len([p for p in cparts if p["path"].endswith("/page.json")]) == 4)
check("DeploymentService importable", DeploymentAction.UPDATED.value == "UPDATED")


# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("\u2705 ALL TESTS PASSED" if failed == 0 else "\u274c SOME TESTS FAILED")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
