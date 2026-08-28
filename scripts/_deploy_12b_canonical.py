"""Stage 12B — Deploy canonical combined report + prove persistent identity.

Flow:
1. Build the canonical ExecutiveAnalyticsDemo 4-page ReportSpec.
2. Deploy via the reusable DeploymentService (create-or-update).
3. Perform 3 consecutive in-place updates (visible subtitle change each time)
   and prove the SAME report ID + URL are preserved (no delete/create).
4. After each deploy/update, capture per-page screenshots and verify custom
   visuals render (RENDERED, not ERROR / error placeholder) zero-touch.
5. Emit an identity table + evidence JSON.

Run:
    $env:PYTHONIOENCODING="utf-8"
    .venv\\Scripts\\python.exe scripts/_deploy_12b_canonical.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import get_credential, load_config
from pbi_gen.deploy.service import DeploymentAction, DeploymentService
from pbi_gen.renderer.templates.canonical_report import (
    CANONICAL_REPORT_NAME,
    build_canonical_report_spec,
)
from pbi_gen.renderer.templates.rapid_engine import _auto_load_visual_archives
from pbi_gen.renderer.templates.registry import TemplateRegistry
from pbi_gen.renderer.templates.report_builder import build_report_spec_parts

EVIDENCE = Path("docs/stages/12b-persistent-deployment-and-navigation")
EVIDENCE.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("executive_overview", "Executive Overview"),
    ("financial_performance", "Financial Performance"),
    ("customer_performance", "Customer Performance"),
    ("product_performance", "Product Performance"),
]


def _auth():
    config = load_config()
    ws = config["workspace_id"]
    cred = get_credential(config)
    token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return ws, headers


def _build_parts(subtitle_suffix: str):
    spec = build_canonical_report_spec(subtitle_suffix=subtitle_suffix)
    reg = TemplateRegistry.default()
    guids = spec.custom_visual_guids(reg)
    archives = _auto_load_visual_archives(guids)
    parts = build_report_spec_parts(spec, reg, visual_archives=archives)
    return spec, parts


def _capture_all_pages(report_id: str, sm_id: str, label: str, headers: dict, ws: str):
    """Capture per-page screenshots + verify custom visuals render. Returns
    {page_name: {'ok': bool, 'path': str, 'error': str}}.

    Uses a wider viewport than the 1280 canvas so the powerbi-client's internal
    padding does not clip the left nav rail in the captured image.
    """
    from pbi_gen.critic.screenshot import _get_embed_url, _generate_embed_token
    from playwright.sync_api import sync_playwright

    embed_url = None
    for _ in range(3):
        embed_url = _get_embed_url(ws, report_id, headers)
        if embed_url:
            break
        time.sleep(2)
    token = _generate_embed_token(ws, report_id, sm_id, headers)

    results = {}
    if not embed_url or not token:
        for page_name, _ in PAGES:
            results[page_name] = {"ok": False, "path": "", "error": "embed/token failure"}
        return results

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_name, _disp in PAGES:
            out = EVIDENCE / f"{label}_{page_name}.png"
            html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
                '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
                '<style>*{margin:0;padding:0}body{background:#0f1623}'
                '#r{width:1280px;height:720px}</style></head><body><div id="r"></div><script>'
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
            html_path = EVIDENCE / "_embed12b.html"
            html_path.write_text(html, encoding="utf-8")
            # Viewport wider/taller than the canvas so nothing is clipped.
            page = browser.new_page(viewport={"width": 1320, "height": 760})
            page.goto(f"file:///{html_path.resolve()}")
            ok = False
            err = ""
            try:
                page.wait_for_function(
                    'document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")',
                    timeout=60000,
                )
                title = page.title()
                if title.startswith("ERROR"):
                    err = title[:120]
                else:
                    ok = True
            except Exception as e:
                err = str(e)[:120]
            page.wait_for_timeout(3500)
            # Full-viewport screenshot so the left nav rail is never clipped
            # by the powerbi-client's internal fit/offset.
            page.screenshot(path=str(out))
            page.close()
            results[page_name] = {"ok": ok, "path": str(out) if ok else "", "error": err}
            print(f"      {page_name}: {'OK' if ok else 'FAIL ' + err[:80]}")
            html_path.unlink(missing_ok=True)
        browser.close()
    return results


def main():
    ws, headers = _auth()
    svc = DeploymentService(ws, headers)

    spec0, _ = _build_parts("")
    sm_id = spec0.semantic_model_id

    evidence = {
        "report_name": CANONICAL_REPORT_NAME,
        "semantic_model_id": sm_id,
        "iterations": [],
    }

    print("=" * 64)
    print("STAGE 12B — Canonical persistent deployment proof")
    print("=" * 64)

    # ── Initial deploy (create-or-update) + 3 in-place updates ──
    # iteration 0 = initial deploy; 1..3 = visible in-place updates
    labels = ["v0_initial", "v1_update", "v2_update", "v3_update"]
    suffixes = ["", " · rev1", " · rev2", " · rev3"]

    first_id = None
    first_url = None

    for i, (label, suffix) in enumerate(zip(labels, suffixes)):
        print(f"\n[{label}] building parts (subtitle suffix={suffix!r})")
        spec, parts = _build_parts(suffix)
        t0 = time.time()
        result = svc.deploy(CANONICAL_REPORT_NAME, parts, page_names=spec.page_names)
        elapsed = time.time() - t0
        print(f"   action={result.action.value} id={result.report_id} "
              f"elapsed={result.elapsed_seconds}s")
        print(f"   url={result.report_url}")

        if first_id is None:
            first_id = result.report_id
            first_url = result.report_url

        # let the service settle before render verification
        time.sleep(6)

        print(f"   capturing per-page screenshots + custom-visual gate...")
        page_results = _capture_all_pages(result.report_id, sm_id, label, headers, ws)
        all_pages_ok = all(p["ok"] for p in page_results.values())
        result.render_verified = all_pages_ok

        evidence["iterations"].append({
            "label": label,
            "subtitle_suffix": suffix,
            "action": result.action.value,
            "report_id": result.report_id,
            "report_url": result.report_url,
            "definition_hash": result.definition_hash,
            "elapsed_seconds": round(elapsed, 2),
            "id_preserved": result.id_preserved,
            "render_verified": all_pages_ok,
            "pages": page_results,
        })

    # ── Identity stability analysis ──
    ids = [it["report_id"] for it in evidence["iterations"]]
    urls = [it["report_url"] for it in evidence["iterations"]]
    updates = [it for it in evidence["iterations"] if it["action"] == "UPDATED"]

    id_stable = len(set(ids)) == 1
    url_stable = len(set(urls)) == 1
    three_updates = len(updates) >= 3
    all_rendered = all(it["render_verified"] for it in evidence["iterations"])

    evidence["summary"] = {
        "report_id": ids[0],
        "report_url": urls[0],
        "id_stable_across_all": id_stable,
        "url_stable_across_all": url_stable,
        "update_count": len(updates),
        "three_consecutive_updates": three_updates,
        "all_iterations_rendered_zero_touch": all_rendered,
        "pass": id_stable and url_stable and three_updates and all_rendered,
    }

    print("\n" + "=" * 64)
    print("IDENTITY STABILITY TABLE")
    print("=" * 64)
    print(f"{'iter':<12}{'action':<9}{'id_preserved':<14}{'render':<8}report_id")
    for it in evidence["iterations"]:
        print(f"{it['label']:<12}{it['action']:<9}"
              f"{str(it['id_preserved']):<14}{str(it['render_verified']):<8}{it['report_id']}")
    print(f"\nID stable: {id_stable} | URL stable: {url_stable} | "
          f"updates: {len(updates)} | all rendered: {all_rendered}")
    print(f"RESULT: {'PASS' if evidence['summary']['pass'] else 'FAIL/BLOCKED'}")

    (EVIDENCE / "identity_evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    print(f"\nEvidence saved to {EVIDENCE / 'identity_evidence.json'}")


if __name__ == "__main__":
    main()
