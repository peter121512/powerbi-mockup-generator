"""Run formatting compatibility tests against live Fabric.

Tests properties in batches to minimize deployments while still isolating failures.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.critic.harness import (
    CompatibilityHarness, CapabilityTest,
    make_card_visual, make_bar_visual,
    _lit, _str_lit, _num_lit, _bool_lit, _color_lit,
)

evidence_dir = Path("docs/stages/07a-styling-compatibility/evidence")
evidence_dir.mkdir(parents=True, exist_ok=True)

results: list[dict] = []

harness = CompatibilityHarness.create()
print(f"Harness ready. SM: {harness.semantic_model_id}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Card with title only (baseline - known safe)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Test 1: Card title (baseline) ===")
card = make_card_visual("card1", objects={
    "general": [{"properties": {"title": _str_lit("Revenue Total")}}]
})
bar = make_bar_visual("bar1", objects={
    "general": [{"properties": {"title": _str_lit("By Category")}}]
})
rid = harness.deploy_diagnostic("DiagStyle01", [card, bar])
ok = harness.capture(evidence_dir / "test01-title-only.png")
results.append({"id": "title-only", "family": "card,chart", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "general.title"})
print(f"  Result: {'safe' if ok else 'UNSAFE'}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Card labels (fontSize, displayUnits)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Test 2: Card labels fontSize + displayUnits ===")
card = make_card_visual("card1", objects={
    "general": [{"properties": {"title": _str_lit("Revenue")}}],
    "labels": [{"properties": {
        "show": _bool_lit(True),
        "fontSize": _num_lit(20),
        "labelDisplayUnits": _num_lit(0),
    }}],
    "categoryLabels": [{"properties": {"show": _bool_lit(True)}}],
})
bar = make_bar_visual("bar1", objects={
    "general": [{"properties": {"title": _str_lit("By Category")}}]
})
rid = harness.deploy_diagnostic("DiagStyle01", [card, bar])
ok = harness.capture(evidence_dir / "test02-card-labels.png")
results.append({"id": "card-labels-fontSize", "family": "card", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "labels.fontSize"})
results.append({"id": "card-labels-displayUnits", "family": "card", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "labels.labelDisplayUnits"})
results.append({"id": "card-categoryLabels-show", "family": "card", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "categoryLabels.show"})
print(f"  Result: {'safe' if ok else 'UNSAFE'}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Card labels with colour
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Test 3: Card labels colour ===")
card = make_card_visual("card1", objects={
    "general": [{"properties": {"title": _str_lit("Revenue")}}],
    "labels": [{"properties": {
        "show": _bool_lit(True),
        "fontSize": _num_lit(22),
        "color": _color_lit("#1B3A5C"),
    }}],
})
bar = make_bar_visual("bar1", objects={
    "general": [{"properties": {"title": _str_lit("By Category")}}]
})
rid = harness.deploy_diagnostic("DiagStyle01", [card, bar])
ok = harness.capture(evidence_dir / "test03-card-color.png")
results.append({"id": "card-labels-color", "family": "card", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "labels.color"})
print(f"  Result: {'safe' if ok else 'UNSAFE'}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Chart axis/gridline formatting
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Test 4: Chart axis + gridlines ===")
card = make_card_visual("card1", objects={
    "general": [{"properties": {"title": _str_lit("Revenue")}}],
})
bar = make_bar_visual("bar1", objects={
    "general": [{"properties": {"title": _str_lit("By Category")}}],
    "categoryAxis": [{"properties": {
        "show": _bool_lit(True),
        "showAxisTitle": _bool_lit(False),
    }}],
    "valueAxis": [{"properties": {
        "show": _bool_lit(True),
        "showAxisTitle": _bool_lit(False),
        "gridlineShow": _bool_lit(True),
    }}],
})
rid = harness.deploy_diagnostic("DiagStyle01", [card, bar])
ok = harness.capture(evidence_dir / "test04-axis-gridlines.png")
results.append({"id": "chart-categoryAxis-show", "family": "chart", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "categoryAxis.show"})
results.append({"id": "chart-valueAxis-gridlineShow", "family": "chart", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "valueAxis.gridlineShow"})
results.append({"id": "chart-axis-showAxisTitle", "family": "chart", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "categoryAxis.showAxisTitle"})
print(f"  Result: {'safe' if ok else 'UNSAFE'}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Visual background/border
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Test 5: Visual background ===")
card = make_card_visual("card1", objects={
    "general": [{"properties": {
        "title": _str_lit("Revenue"),
        "background": _color_lit("#FFFFFF"),
        "backgroundTransparency": _num_lit(0),
    }}],
})
bar = make_bar_visual("bar1", objects={
    "general": [{"properties": {"title": _str_lit("By Category")}}],
})
rid = harness.deploy_diagnostic("DiagStyle01", [card, bar])
ok = harness.capture(evidence_dir / "test05-background.png")
results.append({"id": "visual-background", "family": "card,chart", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "general.background"})
results.append({"id": "visual-backgroundTransparency", "family": "card,chart", "status": "safe" if ok else "unsafe", "mechanism": "pbir_objects", "prop": "general.backgroundTransparency"})
print(f"  Result: {'safe' if ok else 'UNSAFE'}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Theme JSON approach
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Test 6: Custom theme JSON ===")
theme = {
    "name": "DiagTheme",
    "dataColors": ["#1B3A5C", "#C8963E", "#4A7C8F", "#7B5EA7", "#D17B4A"],
    "background": "#F8F9FA",
    "foreground": "#212121",
    "tableAccent": "#1B3A5C",
    "textClasses": {
        "callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": "#1B3A5C"},
        "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": "#212121"},
        "header": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": "#212121"},
        "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": "#605E5C"},
    },
}
card = make_card_visual("card1", objects={
    "general": [{"properties": {"title": _str_lit("Revenue")}}],
})
bar = make_bar_visual("bar1", objects={
    "general": [{"properties": {"title": _str_lit("By Category")}}],
})
rid = harness.deploy_diagnostic("DiagStyle01", [card, bar], theme=theme)
ok = harness.capture(evidence_dir / "test06-theme.png")
results.append({"id": "theme-dataColors", "family": "all", "status": "safe" if ok else "unsafe", "mechanism": "theme_json", "prop": "dataColors"})
results.append({"id": "theme-textClasses-callout", "family": "card", "status": "safe" if ok else "unsafe", "mechanism": "theme_json", "prop": "textClasses.callout"})
results.append({"id": "theme-textClasses-title", "family": "all", "status": "safe" if ok else "unsafe", "mechanism": "theme_json", "prop": "textClasses.title"})
results.append({"id": "theme-textClasses-label", "family": "all", "status": "safe" if ok else "unsafe", "mechanism": "theme_json", "prop": "textClasses.label"})
results.append({"id": "theme-background", "family": "all", "status": "safe" if ok else "unsafe", "mechanism": "theme_json", "prop": "background"})
results.append({"id": "theme-foreground", "family": "all", "status": "safe" if ok else "unsafe", "mechanism": "theme_json", "prop": "foreground"})
print(f"  Result: {'safe' if ok else 'UNSAFE'}")

# ─────────────────────────────────────────────────────────────────────────────
# Save results
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n=== Results: {len(results)} capabilities tested ===")
safe_count = sum(1 for r in results if r["status"] == "safe")
unsafe_count = sum(1 for r in results if r["status"] == "unsafe")
print(f"  Safe: {safe_count}, Unsafe: {unsafe_count}")

output_path = Path("docs/stages/07a-styling-compatibility/test-results.json")
output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"  Saved to {output_path}")
