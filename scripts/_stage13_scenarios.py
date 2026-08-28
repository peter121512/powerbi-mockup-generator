"""Stage 13 — end-to-end Scenarios A-F with live OpenAI image generation + live
Power BI deployment via the persistent DeploymentService.

Requires OPENAI_API_KEY in the environment (never hard-coded). Falls back to the
deterministic stub adapter if the key is absent (records that in evidence).

Run:
    $env:OPENAI_API_KEY="..."      # do not commit
    $env:PYTHONIOENCODING="utf-8"
    .venv\\Scripts\\python.exe scripts/_stage13_scenarios.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import get_credential, load_config
from pbi_gen.deploy.service import DeploymentService
from pbi_gen.design import (
    DashboardMockupService,
    DesignWorkflow,
    ImplementationClass,
    StubImageAdapter,
    context_from_description,
    default_adapter,
    profile_spreadsheet,
    resolve_url,
)
from pbi_gen.design.build_handoff import spec_to_report_spec
from pbi_gen.renderer.templates.rapid_engine import _auto_load_visual_archives
from pbi_gen.renderer.templates.registry import TemplateRegistry
from pbi_gen.renderer.templates.report_builder import build_report_spec_parts

EVIDENCE = Path("docs/stages/13-conversational-image-mockup-workflow/evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)

USING_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))


def _service(subdir: str) -> DashboardMockupService:
    out = EVIDENCE / subdir
    return DashboardMockupService(default_adapter(), output_dir=out)


def _dump(name: str, obj) -> None:
    (EVIDENCE / name).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario A — description only
# ─────────────────────────────────────────────────────────────────────────────

def scenario_a() -> dict:
    print("\n=== Scenario A — description only ===")
    req = ("I have SaaS subscription data with customer, plan, ARR, MRR, churn date, "
           "region and sales owner. Build me an executive retention dashboard.")
    ctx = context_from_description(req)
    wf = DesignWorkflow(_service("A"))
    s = wf.start_session(req, data_context=ctx)
    r0 = wf.generate_initial_mockup(s)
    r1 = wf.revise(s, "make the KPI cards the same width and more executive")
    out = {
        "data_context": ctx.to_dict(),
        "audience": s.audience,
        "kpis": s.inferred_kpis,
        "initial_mockup": r0.to_dict(),
        "revised_mockup": r1.to_dict(),
        "no_design_drift": [v.title for v in s.proposed_visuals],
        "assumptions": ctx.assumptions,
    }
    print(f"  ctx confidence={ctx.confidence} kpis={s.inferred_kpis} mockups={len(s.revisions)}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Scenario B — spreadsheet upload (multi-sheet)
# ─────────────────────────────────────────────────────────────────────────────

def scenario_b() -> dict:
    print("\n=== Scenario B — spreadsheet upload ===")
    from openpyxl import Workbook
    wbpath = EVIDENCE / "B" / "finance_workbook.xlsx"
    wbpath.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active; ws.title = "Invoices"
    ws.append(["InvoiceDate", "Customer", "Product", "Region", "Revenue", "Cost", "Budget"])
    ws.append(["2024-01-05", "Acme", "Widget", "London", 1200.50, 800.00, 1000])
    ws.append(["2024-02-11", "Globex", "Gadget", "Scotland", 2400.00, 1500.00, 2200])
    ws.append(["2024-03-08", "Initech", "Widget", "Wales", 900.25, 600.00, 950])
    ws2 = wb.create_sheet("Targets")
    ws2.append(["Region", "AnnualTarget"])
    ws2.append(["London", 50000])
    wb.save(wbpath)

    ctx = profile_spreadsheet(wbpath)
    wf = DesignWorkflow(_service("B"))
    s = wf.start_session("CFO finance performance dashboard from this workbook", data_context=ctx)
    r0 = wf.generate_initial_mockup(s)
    # ground check: proposed KPIs should come from actual columns
    grounded = all(any(k.lower() in f.lower() for f in ctx.field_names()) or k in ctx.candidate_measures
                   for k in s.inferred_kpis) if s.inferred_kpis else False
    out = {
        "data_context": ctx.to_dict(),
        "entities": ctx.entities,
        "kpis": s.inferred_kpis,
        "kpis_grounded_in_columns": grounded,
        "mockup": r0.to_dict(),
    }
    print(f"  entities={ctx.entities} measures={ctx.candidate_measures} grounded={grounded}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Scenario C — online file / URL
# ─────────────────────────────────────────────────────────────────────────────

def scenario_c() -> dict:
    print("\n=== Scenario C — online file (URL) ===")
    # Small, stable, public CSV.
    url = "https://raw.githubusercontent.com/plotly/datasets/master/2014_apple_stock.csv"
    result: dict = {"url": url}
    try:
        ctx = resolve_url(url)
        wf = DesignWorkflow(_service("C"))
        s = wf.start_session("executive trend dashboard from this online dataset", data_context=ctx)
        r0 = wf.generate_initial_mockup(s)
        result.update({
            "resolved": True,
            "data_context": ctx.to_dict(),
            "mockup": r0.to_dict(),
        })
        print(f"  resolved fields={ctx.field_names()} confidence={ctx.confidence}")
    except Exception as e:
        result.update({"resolved": False, "error": str(e)[:300]})
        print(f"  URL resolve failed (non-fatal): {e}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Scenario D — multi-turn revision with deliberate template deviation
# ─────────────────────────────────────────────────────────────────────────────

def scenario_d() -> tuple[dict, "DesignWorkflow", object]:
    print("\n=== Scenario D — multi-turn revision + deliberate deviation ===")
    req = "Executive retail performance dashboard: revenue, gross profit, margin, region, category, monthly date"
    ctx = context_from_description(req)
    wf = DesignWorkflow(_service("D"))
    s = wf.start_session(req, data_context=ctx)
    steps = [("initial", None)]
    wf.generate_initial_mockup(s)
    revisions = [
        "switch the comparison visual from column to donut",           # within capability
        "make the margin visual a bespoke radial bar with an outer target ring",  # deviation
        "use teal instead of purple",                                  # colour only
        "add a regional filter and move the filters to the top right", # layout only
    ]
    before_titles = [v.title for v in s.proposed_visuals]
    for r in revisions:
        wf.revise(s, r)
    cvrs = [c.to_dict() for c in s.custom_visual_requirements]
    classes = [v.classification.implementation_class.value for v in s.proposed_visuals]
    out = {
        "revision_count": len(s.revisions),
        "titles_before": before_titles,
        "titles_after": [v.title for v in s.proposed_visuals],
        "classes": classes,
        "custom_visual_requirements": cvrs,
        "teal_applied": s.palette["accent"] == "#14b8a6",
        "bespoke_preserved": any(
            v.classification.implementation_class == ImplementationClass.CUSTOM_VISUAL_REQUIRED
            for v in s.proposed_visuals),
    }
    print(f"  revisions={len(s.revisions)} CVRs={[c['requirement_id'] for c in cvrs]} teal={out['teal_applied']}")
    return out, wf, s


# ─────────────────────────────────────────────────────────────────────────────
# Scenario E — approved mockup -> real Power BI (live deploy)
# ─────────────────────────────────────────────────────────────────────────────

def scenario_e(wf, s) -> dict:
    print("\n=== Scenario E — approval -> real Power BI (live deploy) ===")
    spec = wf.approve(s, page_title="Designed Retail Performance",
                      page_subtitle="From approved mockup")
    _dump("E_design_spec.json", spec.to_dict())

    report_spec, br = spec_to_report_spec(spec, page_name="designed_dashboard")

    # Live deploy via persistent DeploymentService.
    config = load_config()
    ws = config["workspace_id"]
    cred = get_credential(config)
    token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    reg = TemplateRegistry.default()
    archives = _auto_load_visual_archives(report_spec.custom_visual_guids(reg))
    parts = build_report_spec_parts(report_spec, reg, visual_archives=archives)

    svc = DeploymentService(ws, headers)
    logical = report_spec.report_name
    dres = svc.deploy(logical, parts, page_names=report_spec.page_names)
    br.report_id = dres.report_id
    br.report_url = dres.report_url
    br.action = dres.action.value
    print(f"  deploy action={dres.action.value} id={dres.report_id}")

    # Capture the deployed report screenshot for actual-vs-approved comparison.
    time.sleep(6)
    try:
        from pbi_gen.critic.screenshot import _generate_embed_token, _get_embed_url
        from playwright.sync_api import sync_playwright
        embed_url = _get_embed_url(ws, dres.report_id, headers)
        etoken = _generate_embed_token(ws, dres.report_id, spec_sm(report_spec), headers)
        if embed_url and etoken:
            html = _embed_html(etoken, embed_url, dres.report_id, report_spec.default_page)
            hp = EVIDENCE / "_e.html"; hp.write_text(html, encoding="utf-8")
            shot = EVIDENCE / "E_deployed_report.png"
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                pg = b.new_page(viewport={"width": 1320, "height": 760})
                pg.goto(f"file:///{hp.resolve()}")
                try:
                    pg.wait_for_function(
                        'document.title.startsWith("RENDERED")||document.title.startsWith("ERROR")',
                        timeout=60000)
                except Exception:
                    pass
                pg.wait_for_timeout(4000)
                pg.screenshot(path=str(shot))
                b.close()
            hp.unlink(missing_ok=True)
            br.screenshot_path = str(shot)
            print(f"  screenshot -> {shot}")
    except Exception as e:
        br.errors.append(f"screenshot failed: {e}")
        print(f"  screenshot failed (non-fatal): {e}")

    out = {"build_result": br.to_dict(), "deploy": {
        "action": dres.action.value, "report_id": dres.report_id,
        "report_url": dres.report_url, "id_preserved": dres.id_preserved,
    }}
    _dump("E_build_result.json", out)
    return out


def spec_sm(report_spec) -> str:
    return report_spec.semantic_model_id


def _embed_html(token, embed_url, report_id, page_name) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
        '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
        '<style>*{margin:0;padding:0}body{background:#0f1623}#r{width:1280px;height:720px}</style>'
        '</head><body><div id="r"></div><script>'
        'const m=window["powerbi-client"].models;'
        f'const c={{type:"report",tokenType:m.TokenType.Embed,accessToken:"{token}",'
        f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"{page_name}",'
        'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
        'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
        'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
        'const r=powerbi.embed(document.getElementById("r"),c);'
        'r.on("rendered",()=>{document.title="RENDERED"});'
        'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
        '</script></body></html>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario F — Power BI feasibility guardrail
# ─────────────────────────────────────────────────────────────────────────────

def scenario_f() -> dict:
    print("\n=== Scenario F — feasibility guardrail ===")
    ctx = context_from_description("revenue, cost, region, monthly date")
    wf = DesignWorkflow(_service("F"))
    s = wf.start_session("executive dashboard", data_context=ctx)
    wf.generate_initial_mockup(s)
    wf.revise(s, "add a rotating 3D globe with real-time physics that users can spin with gestures")
    last = s.proposed_visuals[-1]
    out = {
        "requested": "rotating 3D globe with real-time physics + gesture control",
        "classification": last.classification.to_dict(),
        "not_falsely_promised": last.classification.implementation_class == ImplementationClass.NEEDS_REDESIGN,
    }
    print(f"  classified as {last.classification.implementation_class.value}")
    return out


def main():
    print("=" * 64)
    print(f"STAGE 13 SCENARIOS  (image adapter: {'OpenAI gpt-image-1' if USING_OPENAI else 'STUB'})")
    print("=" * 64)
    evidence = {"using_openai": USING_OPENAI, "scenarios": {}}

    evidence["scenarios"]["A"] = scenario_a()
    evidence["scenarios"]["B"] = scenario_b()
    evidence["scenarios"]["C"] = scenario_c()
    d_out, wf, s = scenario_d()
    evidence["scenarios"]["D"] = d_out
    evidence["scenarios"]["E"] = scenario_e(wf, s)
    evidence["scenarios"]["F"] = scenario_f()

    _dump("scenarios_evidence.json", evidence)
    print("\n" + "=" * 64)
    print("SCENARIO SUMMARY")
    print("=" * 64)
    print(f"  A description-only:      mockups={len(evidence['scenarios']['A']['no_design_drift'])} visuals")
    print(f"  B spreadsheet:           grounded={evidence['scenarios']['B']['kpis_grounded_in_columns']}")
    print(f"  C url:                   resolved={evidence['scenarios']['C'].get('resolved')}")
    print(f"  D deviation:             CVRs={len(evidence['scenarios']['D']['custom_visual_requirements'])} "
          f"bespoke_preserved={evidence['scenarios']['D']['bespoke_preserved']}")
    e = evidence["scenarios"]["E"]["deploy"]
    print(f"  E deploy:                action={e['action']} id={e['report_id']}")
    print(f"  F guardrail:             not_falsely_promised={evidence['scenarios']['F']['not_falsely_promised']}")
    print(f"\nEvidence -> {EVIDENCE / 'scenarios_evidence.json'}")


if __name__ == "__main__":
    main()
