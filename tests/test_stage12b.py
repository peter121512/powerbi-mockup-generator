"""Stage 12B unit tests — persistent deployment + multi-page navigation.

Standalone runnable script (matches the repo's test_stage12a.py style). Uses a
mock HTTP session for the DeploymentService so create-or-update logic is proven
without a live Fabric workspace. Live Fabric/Playwright checks live in the
separate scripts under scripts/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.service import (
    DeploymentAction,
    DeploymentService,
    definition_hash,
)
from pbi_gen.renderer.templates.canonical_report import (
    CANONICAL_REPORT_NAME,
    build_canonical_report_spec,
)
from pbi_gen.renderer.templates.navigation import (
    NAV_TOKENS,
    NavItem,
    default_nav_items,
    has_emoji,
    icon_data_uri,
)
from pbi_gen.renderer.templates.registry import DesignTokens, TemplateRegistry
from pbi_gen.renderer.templates.report_builder import (
    ReportPage,
    ReportSpec,
    build_report_spec_parts,
)

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


# ─────────────────────────────────────────────────────────────────────────────
# Mock HTTP session for DeploymentService
# ─────────────────────────────────────────────────────────────────────────────


class MockResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json


class MockSession:
    """Records calls and returns queued responses. Tracks whether delete was called."""

    def __init__(self, existing_reports=None):
        # existing_reports: list of {"id","displayName"}
        self.existing = existing_reports or []
        self.calls = []
        self.deleted = []
        self.created = []
        self.updated = []
        self._next_created_id = "new-report-id-001"

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("GET", url))
        if "items?type=Report" in url:
            return MockResponse(200, {"value": self.existing})
        if "/reports/" in url:
            rid = url.rstrip("/").split("/")[-1]
            return MockResponse(200, {
                "webUrl": f"https://app.powerbi.com/groups/ws/reports/{rid}",
                "id": rid,
            })
        return MockResponse(200, {})

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(("POST", url))
        if url.endswith("/items"):
            new = {"id": self._next_created_id, "displayName": json["displayName"]}
            self.created.append(new)
            self.existing.append(new)  # now discoverable
            return MockResponse(201, {"id": self._next_created_id})
        if "updateDefinition" in url:
            self.updated.append(url)
            return MockResponse(200, {})
        return MockResponse(200, {})

    def delete(self, url, headers=None, timeout=None):
        self.deleted.append(url)
        return MockResponse(200, {})


HEADERS = {"Authorization": "Bearer x", "Content-Type": "application/json"}
PARTS = [{"path": "a", "payload": "AA", "payloadType": "InlineBase64"}]


# ─── Test 1: create when absent ───────────────────────────────────────────────
print("\n1. Create-or-update: create when report absent")
sess = MockSession(existing_reports=[])
svc = DeploymentService("ws", HEADERS, session=sess)
res = svc.deploy("MyReport", PARTS)
check("action is CREATED", res.action == DeploymentAction.CREATED)
check("report_id set", res.report_id == "new-report-id-001")
check("no previous id", res.previous_report_id is None)
check("no delete called", len(sess.deleted) == 0, f"deleted={sess.deleted}")
check("used create endpoint", any(u.endswith('/items') for _, u in sess.calls if _ == 'POST'))
check("success", res.success)


# ─── Test 2: update when present (stable ID) ─────────────────────────────────
print("\n2. Create-or-update: update in place when present")
sess = MockSession(existing_reports=[{"id": "existing-123", "displayName": "MyReport"}])
svc = DeploymentService("ws", HEADERS, session=sess)
res = svc.deploy("MyReport", PARTS)
check("action is UPDATED", res.action == DeploymentAction.UPDATED)
check("report_id preserved", res.report_id == "existing-123")
check("previous id == report id", res.previous_report_id == "existing-123")
check("id_preserved property true", res.id_preserved)
check("updateDefinition called", len(sess.updated) == 1)
check("no delete called", len(sess.deleted) == 0)


# ─── Test 3: update path does not call delete by default ─────────────────────
print("\n3. Update path never deletes")
check("zero deletes across create+update", len(sess.deleted) == 0)


# ─── Test 4: stable report ID across repeated (mocked) updates ───────────────
print("\n4. Stable report ID across 3 mocked updates")
sess = MockSession(existing_reports=[{"id": "canon-abc", "displayName": CANONICAL_REPORT_NAME}])
svc = DeploymentService("ws", HEADERS, session=sess)
ids = []
urls = []
for _ in range(3):
    r = svc.deploy(CANONICAL_REPORT_NAME, PARTS)
    ids.append(r.report_id)
    urls.append(r.report_url)
check("all 3 IDs identical", len(set(ids)) == 1 and ids[0] == "canon-abc", f"ids={ids}")
check("all 3 URLs identical", len(set(urls)) == 1, f"urls={urls}")
check("3 updateDefinition calls, 0 deletes", len(sess.updated) == 3 and len(sess.deleted) == 0)


# ─── Test 5: deterministic logical report lookup ─────────────────────────────
print("\n5. Deterministic logical report lookup")
sess = MockSession(existing_reports=[
    {"id": "zzz", "displayName": "Dup"},
    {"id": "aaa", "displayName": "Dup"},
    {"id": "mmm", "displayName": "Other"},
])
svc = DeploymentService("ws", HEADERS, session=sess)
check("case-insensitive match", svc.find_report_id("dup") == "aaa")
check("smallest id chosen deterministically", svc.find_report_id("Dup") == "aaa")
check("absent returns None", svc.find_report_id("missing") is None)


# ─── Test 6: definition hash stable + sensitive ──────────────────────────────
print("\n6. Definition hash")
h1 = definition_hash(PARTS)
h2 = definition_hash(list(PARTS))
h3 = definition_hash([{"path": "a", "payload": "BB", "payloadType": "InlineBase64"}])
check("hash deterministic", h1 == h2)
check("hash changes with payload", h1 != h3)


# ─── Test 7: multi-page ReportSpec generation ────────────────────────────────
print("\n7. Multi-page ReportSpec generation")
spec = build_canonical_report_spec()
reg = TemplateRegistry.default()
parts = build_report_spec_parts(spec, reg)
page_json = [p["path"] for p in parts if p["path"].endswith("/page.json")]
check("four pages generated", len(page_json) == 4, f"{page_json}")
check("report name is canonical", spec.report_name == CANONICAL_REPORT_NAME)
check("default page is executive_overview", spec.default_page == "executive_overview")


# ─── Test 8: deterministic page IDs/names ────────────────────────────────────
print("\n8. Deterministic page IDs")
expected = ["executive_overview", "financial_performance",
            "customer_performance", "product_performance"]
check("page names match expected order", spec.page_names == expected, f"{spec.page_names}")
# Rebuild → identical names (deterministic)
spec2 = build_canonical_report_spec()
check("page names stable across rebuilds", spec2.page_names == expected)


# ─── Test 9: navigation actions target valid pages ───────────────────────────
print("\n9. Navigation targets valid pages")
import base64, json as _json
targets = set()
for p in parts:
    if "/nav_item_" in p["path"]:
        v = _json.loads(base64.b64decode(p["payload"]))
        vl = v["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
        typ = vl["type"]["expr"]["Literal"]["Value"]
        tgt = vl["navigationSection"]["expr"]["Literal"]["Value"].strip("'")
        check(f"{p['path'].split('/')[3]} nav is PageNavigation", typ == "'PageNavigation'")
        targets.add(tgt)
check("all nav targets are real pages", targets == set(expected), f"{targets}")


# ─── Test 10: exactly one active nav item per page ───────────────────────────
print("\n10. Exactly one active nav item per page")
from pbi_gen.renderer.templates.report_builder import build_nav_visuals
for page in spec.pages:
    navs = build_nav_visuals(spec.nav_items, page.shell.active_nav, NAV_TOKENS, 720)
    # active pill + indicator present exactly once each
    names = [n for n, _ in navs]
    check(f"{page.page_name}: one active pill", names.count("nav_active_pill") == 1)
    check(f"{page.page_name}: one active indicator", names.count("nav_indicator") == 1)
    # exactly one active (bold) label
    bold_count = 0
    for n, v in navs:
        if n.startswith("nav_label_"):
            b = v["visual"]["visualContainerObjects"]["title"][0]["properties"]["bold"]["expr"]["Literal"]["Value"]
            if b == "true":
                bold_count += 1
    check(f"{page.page_name}: exactly one active (bold) label", bold_count == 1, f"bold={bold_count}")
    # each item has icon + label + clickable button layer
    item_count = sum(1 for n, _ in navs if n.startswith("nav_item_"))
    label_count = sum(1 for n, _ in navs if n.startswith("nav_label_"))
    icon_count = sum(1 for n, _ in navs if n.startswith("nav_icon_"))
    check(f"{page.page_name}: 4 icons/labels/buttons",
          item_count == 4 and label_count == 4 and icon_count == 4)


# ─── Test 11: no emoji in nav config/source ──────────────────────────────────
print("\n11. No emoji in navigation")


def _rejects_emoji():
    try:
        NavItem("\U0001f4b0 Money", "executive_overview", "financial")
        return False
    except ValueError:
        return True


for item in default_nav_items():
    check(f"label '{item.label}' has no emoji", not has_emoji(item.label))
    check(f"tooltip has no emoji", not has_emoji(item.tooltip))
# has_emoji sanity: it should detect an actual emoji
check("has_emoji detects real emoji", has_emoji("\U0001f4b0 Financial"))
check("NavItem rejects emoji label", _rejects_emoji())


# ─── Test 12: all four configs assemble into one report ──────────────────────
print("\n12. Four configs assemble into one report")
check("spec has 4 pages", len(spec.pages) == 4)
check("all bind to one semantic model",
      spec.semantic_model_id == "b731eda9-c402-42c4-ad27-f4641c7d6bcd")


# ─── Test 13: custom visuals packaged once per report ────────────────────────
print("\n13. Custom visuals packaged once per report")
pkg_paths = [p["path"] for p in parts if p["path"].endswith("/package.json")]
guids_in_pkgs = [p.split("/")[1] for p in pkg_paths]
check("no duplicate custom-visual packages",
      len(guids_in_pkgs) == len(set(guids_in_pkgs)), f"{guids_in_pkgs}")
check("package count matches distinct guids",
      len(pkg_paths) == len(spec.custom_visual_guids(reg)))


# ─── Test 14: Stage 12A systems intact ───────────────────────────────────────
print("\n14. Stage 12A systems intact")
from pbi_gen.renderer.templates.composites import (
    HEADER_GEOMETRY,
    compute_donut_center,
)
tokens = DesignTokens()
check("header geometry present", HEADER_GEOMETRY.title_font_size == 12)
check("donut center still computable", compute_donut_center(800, 175, 470, 240)[2] == 100)
check("semantic pos/neg distinct", tokens.positive != tokens.negative)
# theme still generates
theme = tokens.to_pbi_theme("ExecutiveDark")
check("theme has dataColors", "dataColors" in theme)


# ─── Test 15: icon data URIs are SVG (not emoji/raster) ──────────────────────
print("\n15. Nav icons are outline SVG data URIs")
for key in ("overview", "financial", "customers", "products"):
    uri = icon_data_uri(key, "#8b98ad")
    check(f"{key} icon is svg data uri", uri.startswith("data:image/svg+xml;base64,"))
    decoded = base64.b64decode(uri.split(",", 1)[1]).decode()
    check(f"{key} svg has stroke (outline)", "stroke=" in decoded and "fill=\"none\"" in decoded)
    check(f"{key} svg has no emoji", not has_emoji(decoded))


# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("\u2705 ALL TESTS PASSED" if failed == 0 else "\u274c SOME TESTS FAILED")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
