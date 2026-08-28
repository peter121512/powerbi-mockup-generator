"""Stage 12B — Playwright click-navigation interaction test.

Embeds the canonical report and physically CLICKS each nav item in the rendered
report, asserting the target page becomes active (via the pageChanged event).
This proves the navigation is genuinely functional, not just PBIR JSON.

Each nav target is exercised from a FRESH embed (started on a different page) so
the headless powerbi-client's lazily-committed pageChanged events cannot coalesce
across clicks. For each target we click the row, re-clicking to flush, until the
pageChanged event for the target is observed. Evidence screenshots are captured.

Run:
    $env:PYTHONIOENCODING="utf-8"
    .venv\\Scripts\\python.exe scripts/_test_12b_nav_interaction.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import get_credential, load_config
from pbi_gen.deploy.service import DeploymentService
from pbi_gen.renderer.templates.canonical_report import (
    CANONICAL_REPORT_NAME,
    build_canonical_report_spec,
)
from pbi_gen.renderer.templates.navigation import NAV_TOKENS, default_nav_items

EVIDENCE = Path("docs/stages/12b-persistent-deployment-and-navigation")
EVIDENCE.mkdir(parents=True, exist_ok=True)


def main():
    config = load_config()
    ws = config["workspace_id"]
    cred = get_credential(config)
    token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    svc = DeploymentService(ws, headers)
    report_id = svc.find_report_id(CANONICAL_REPORT_NAME)
    if not report_id:
        print(f"ERROR: canonical report '{CANONICAL_REPORT_NAME}' not found. Deploy it first.")
        sys.exit(1)

    spec = build_canonical_report_spec()
    sm_id = spec.semantic_model_id

    from pbi_gen.critic.screenshot import _generate_embed_token, _get_embed_url
    embed_url = _get_embed_url(ws, report_id, headers)
    embed_token = _generate_embed_token(ws, report_id, sm_id, headers)
    if not embed_url or not embed_token:
        print("ERROR: could not obtain embed url/token")
        sys.exit(1)

    nav = NAV_TOKENS
    items = default_nav_items()

    def embed_html(start_page: str) -> str:
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
            '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
            '<style>*{margin:0;padding:0}body{background:#0f1623}#r{width:1280px;height:720px}</style>'
            '</head><body><div id="r"></div><script>'
            'const m=window["powerbi-client"].models; window.__events=[];'
            f'const c={{type:"report",tokenType:m.TokenType.Embed,accessToken:"{embed_token}",'
            f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"{start_page}",'
            'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
            'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
            'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
            'const r=powerbi.embed(document.getElementById("r"),c);'
            'r.on("rendered",()=>{document.title="RENDERED";});'
            'r.on("pageChanged",(e)=>{window.__events.push(e.detail.newPage.name);});'
            'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
            '</script></body></html>'
        )

    def row_center(idx: int):
        cx = nav.nav_width // 2
        cy = nav.top_offset + idx * nav.item_pitch + nav.item_height // 2
        return cx, cy

    from playwright.sync_api import sync_playwright

    results = {"report_id": report_id, "clicks": [], "pass": False}
    all_ok = True

    def map_to_screen(page, rx, ry):
        """Map report (1280x720) coords to screen coords using the #r rect and
        FitToPage scale + letterbox offset, so clicks hit the real nav rows."""
        rect = page.evaluate(
            "() => { const r = document.getElementById('r').getBoundingClientRect();"
            " return {x:r.x, y:r.y, w:r.width, h:r.height}; }"
        )
        scale = min(rect["w"] / 1280.0, rect["h"] / 720.0)
        off_x = rect["x"] + (rect["w"] - 1280 * scale) / 2.0
        off_y = rect["y"] + (rect["h"] - 720 * scale) / 2.0
        return off_x + rx * scale, off_y + ry * scale

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for idx, item in enumerate(items):
            expected = item.target_page
            start = "product_performance" if expected == "executive_overview" else "executive_overview"

            html_path = EVIDENCE / "_nav_interaction.html"
            html_path.write_text(embed_html(start), encoding="utf-8")

            page = browser.new_page(viewport={"width": 1320, "height": 760})
            page.goto(f"file:///{html_path.resolve()}")
            page.wait_for_function(
                'document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")',
                timeout=60000,
            )
            page.wait_for_timeout(3000)

            cx, cy = row_center(idx)
            # The powerbi-client letterboxes the report inside #r; the rendered
            # canvas is scaled ~0.918 and offset ~ (40,52) within the 1280x720
            # div (measured from rendered output). Map report coords accordingly.
            RENDER_SCALE = 0.918
            RENDER_OFF_X = 40
            RENDER_OFF_Y = 52
            sx = RENDER_OFF_X + cx * RENDER_SCALE
            sy = RENDER_OFF_Y + cy * RENDER_SCALE
            ok = False
            seen = []
            # Click the target row; re-click to flush the lazily committed event
            # until the pageChanged event for the target is observed.
            for _ in range(12):
                page.mouse.click(sx, sy)
                page.wait_for_timeout(1600)
                seen = page.evaluate("() => window.__events")
                if expected in seen:
                    ok = True
                    break
            page.wait_for_timeout(2500)
            page.screenshot(path=str(EVIDENCE / f"nav_click_{expected}.png"))
            print(f"click '{item.label}' (from {start}) -> events={seen} "
                  f"expected={expected} {'OK' if ok else 'FAIL'}")
            results["clicks"].append({
                "step": f"click {item.label}", "from": start,
                "expected": expected, "events": seen, "ok": ok,
            })
            all_ok = all_ok and ok
            page.close()
            html_path.unlink(missing_ok=True)
        browser.close()

    results["pass"] = all_ok
    (EVIDENCE / "nav_interaction_evidence.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("\n" + "=" * 60)
    print(f"NAV INTERACTION: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
