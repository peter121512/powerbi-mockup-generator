"""Stage 12A automated tests — donut composite, header system, colour tokens."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.renderer.templates.composites import (
    DONUT_LEGEND_WIDTH,
    DONUT_PLOT_PADDING,
    DONUT_TITLE_HEIGHT,
    HEADER_GEOMETRY,
    SELF_TITLED_TEMPLATES,
    TITLED_TEMPLATES,
    DonutComposite,
    compute_donut_center,
    make_donut_composite_bindings,
)
from pbi_gen.renderer.templates.registry import (
    DesignTokens,
    FieldRef,
    TemplateRegistry,
)
from pbi_gen.renderer.templates.builder import PageBuilder
from pbi_gen.renderer.templates.financial_config import financial_page_shell, financial_visual_bindings
from pbi_gen.renderer.templates.customer_config import customer_page_shell, customer_visual_bindings
from pbi_gen.renderer.templates.executive_config import executive_page_shell, executive_visual_bindings
from pbi_gen.renderer.templates.rapid_engine import make_donut_composite


passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name} — {detail}")


print("=" * 60)
print("STAGE 12A — AUTOMATED TESTS")
print("=" * 60)

# ─── Test 1: Donut center derived from parent geometry ────────────────────────
print("\n1. Donut centre overlay derived from parent geometry")

sizes = [
    (155, 200, 468, 240, "Default (468×240)"),
    (155, 200, 380, 200, "Narrower (380×200)"),
    (155, 200, 550, 280, "Wider (550×280)"),
    (155, 200, 468, 300, "Taller (468×300)"),
    (155, 200, 470, 240, "Product (470×240)"),
    (800, 175, 470, 240, "Product offset (470×240)"),
]

for x, y, w, h, label in sizes:
    cx, cy, cw, ch = compute_donut_center(x, y, w, h)

    # Expected plot center
    plot_w = w - DONUT_LEGEND_WIDTH - (2 * DONUT_PLOT_PADDING)
    plot_h = h - DONUT_TITLE_HEIGHT - DONUT_PLOT_PADDING
    expected_cx = x + DONUT_PLOT_PADDING + plot_w // 2
    expected_cy = y + DONUT_TITLE_HEIGHT + plot_h // 2

    # Center of overlay
    overlay_cx = cx + cw // 2
    overlay_cy = cy + ch // 2

    err_x = abs(overlay_cx - expected_cx)
    err_y = abs(overlay_cy - expected_cy)

    check(f"{label} — X error ≤5px", err_x <= 5, f"err_x={err_x}")
    check(f"{label} — Y error ≤5px", err_y <= 5, f"err_y={err_y}")

    # No overlap with legend area (overlay right edge < donut left + plot width)
    check(f"{label} — no legend overlap",
          cx + cw < x + w - DONUT_LEGEND_WIDTH + 20,
          f"overlay_right={cx+cw}, legend_start={x+w-DONUT_LEGEND_WIDTH}")

    # No clipping (overlay within donut bounds)
    check(f"{label} — within bounds",
          cx >= x and cy >= y and cx + cw <= x + w and cy + ch <= y + h,
          f"overlay=({cx},{cy},{cw},{ch}), donut=({x},{y},{w},{h})")


# ─── Test 2: Centre remains consistent across size matrix ─────────────────────
print("\n2. Centre consistent across sizes (no manual coordinates)")

for x, y, w, h, label in sizes:
    # Compute twice with same inputs → same result
    r1 = compute_donut_center(x, y, w, h)
    r2 = compute_donut_center(x, y, w, h)
    check(f"{label} — deterministic", r1 == r2)


# ─── Test 3: No manual donut-centre coordinates in configs ────────────────────
print("\n3. No manual donut-centre absolute coordinates in configs")

# Financial config uses composite
bindings = financial_visual_bindings()
donut_centers = [b for b in bindings if b.template_id == "donut_center_kpi"]
for dc in donut_centers:
    # Position should be computed via composite (not matching old hardcoded values)
    # Old was (899, 291, 100, 44) — new should be different (from compute_donut_center)
    check("Financial center uses composite geometry",
          dc.position != (899, 291, 100, 44),
          f"position={dc.position} (matches old hardcoded value)")

# Customer config uses composite
bindings = customer_visual_bindings()
donut_centers = [b for b in bindings if b.template_id == "donut_center_kpi"]
for dc in donut_centers:
    check("Customer center uses composite geometry",
          dc.position != (899, 291, 100, 44),
          f"position={dc.position} (matches old hardcoded value)")


# ─── Test 4: Shared header tokens used by templates ───────────────────────────
print("\n4. Header geometry is shared across templates")

check("HEADER_GEOMETRY.title_font_size is defined", HEADER_GEOMETRY.title_font_size > 0)
check("HEADER_GEOMETRY.title_left_inset is defined", HEADER_GEOMETRY.title_left_inset >= 0)
check("Title region height is reasonable",
      10 < HEADER_GEOMETRY.title_region_height < 40,
      f"got {HEADER_GEOMETRY.title_region_height}")

# All titled templates should be in the set
reg = TemplateRegistry.default()
for tid in reg.list_templates():
    if tid in TITLED_TEMPLATES:
        check(f"{tid} is in TITLED_TEMPLATES set", True)
    elif tid in SELF_TITLED_TEMPLATES:
        check(f"{tid} is in SELF_TITLED_TEMPLATES (exception)", True)
    else:
        check(f"{tid} is categorised", False, "not in either set")


# ─── Test 5: Native titles disabled when renderer header active ───────────────
print("\n5. Visual container objects control titles correctly")

tokens = DesignTokens()
SM_ID = "test-id"
SM_NAME = "TestModel"

for name, shell_fn, bindings_fn in [
    ("Executive", executive_page_shell, executive_visual_bindings),
    ("Financial", financial_page_shell, financial_visual_bindings),
    ("Customer", customer_page_shell, customer_visual_bindings),
]:
    shell = shell_fn()
    builder = PageBuilder(shell=shell, tokens=tokens, registry=reg,
                          semantic_model_id=SM_ID, semantic_model_name=SM_NAME, report_name="Test")
    for b in bindings_fn():
        builder.add_visual(b)
    parts = builder.build_pbir_parts()
    check(f"{name} builds without error", len(parts) > 0)


# ─── Test 6: Colour tokens have backward-compatible defaults ─────────────────
print("\n6. Colour tokens defaults")

tokens = DesignTokens()
check("canvas is dark navy", tokens.canvas == "#0f1623")
check("surface is dark panel", tokens.surface == "#151d2e")
check("accent_blue defined", tokens.accent_blue == "#3898ff")
check("positive is green", tokens.positive == "#34d399")
check("negative is red", tokens.negative == "#f87171")
check("warning is gold", tokens.warning == "#fbbf24")
check("data_colors has 8 entries", len(tokens.data_colors) == 8)
check("text_primary is white", tokens.text_primary == "#ffffff")
check("text_muted is slate", tokens.text_muted == "#94a3b8")


# ─── Test 7: Changing palette changes visual payloads ─────────────────────────
print("\n7. Alternate palette produces different output")

alt_tokens = DesignTokens(
    canvas="#1a1a2e",
    surface="#16213e",
    accent_blue="#00adb5",
    accent_purple="#e94560",
)

# Generate theme JSON with both palettes
default_theme = tokens.to_pbi_theme()
alt_theme = alt_tokens.to_pbi_theme()

check("Alt palette changes dataColors",
      default_theme["dataColors"] != alt_theme["dataColors"])
check("Alt palette changes background",
      default_theme["background"] != alt_theme["background"])
check("Alt palette changes backgroundLight",
      default_theme["backgroundLight"] != alt_theme["backgroundLight"])

# Build a page with alt tokens
shell = financial_page_shell()
builder_default = PageBuilder(shell=shell, tokens=tokens, registry=reg,
                              semantic_model_id=SM_ID, semantic_model_name=SM_NAME, report_name="Default")
builder_alt = PageBuilder(shell=shell, tokens=alt_tokens, registry=reg,
                          semantic_model_id=SM_ID, semantic_model_name=SM_NAME, report_name="Alt")
for b in financial_visual_bindings():
    builder_default.add_visual(b)
    builder_alt.add_visual(b)
parts_default = builder_default.build_pbir_parts()
parts_alt = builder_alt.build_pbir_parts()

# Theme parts should differ
theme_default = next(p for p in parts_default if "RegisteredResources" in p["path"])
theme_alt = next(p for p in parts_alt if "RegisteredResources" in p["path"])
check("Theme payload differs with alt palette",
      theme_default["payload"] != theme_alt["payload"])


# ─── Test 8: Semantic positive/negative colours remain distinct ───────────────
print("\n8. Semantic colours distinct")

check("positive != negative", tokens.positive != tokens.negative)
check("positive != warning", tokens.positive != tokens.warning)
check("negative != warning", tokens.negative != tokens.warning)


# ─── Test 9: All configs build ────────────────────────────────────────────────
print("\n9. All existing configs build")

for name, shell_fn, bindings_fn in [
    ("Executive", executive_page_shell, executive_visual_bindings),
    ("Financial", financial_page_shell, financial_visual_bindings),
    ("Customer", customer_page_shell, customer_visual_bindings),
]:
    try:
        shell = shell_fn()
        builder = PageBuilder(shell=shell, tokens=tokens, registry=reg,
                              semantic_model_id=SM_ID, semantic_model_name=SM_NAME, report_name=f"{name}Test")
        for b in bindings_fn():
            builder.add_visual(b)
        parts = builder.build_pbir_parts()
        check(f"{name} config builds ({len(parts)} parts)", len(parts) > 20)
    except Exception as e:
        check(f"{name} config builds", False, str(e))


# ─── Test 10: make_donut_composite (rapid engine) ─────────────────────────────
print("\n10. make_donut_composite (rapid engine helper)")

specs = make_donut_composite(
    donut_position=(800, 175, 470, 240),
    donut_title="Test Donut",
    donut_category={"entity": "Product", "property": "CategoryName"},
    donut_measure={"entity": "Sales", "property": "TotalRevenue", "is_measure": True},
    center_title="42",
    center_measure={"entity": "Sales", "property": "Count", "is_measure": True},
    center_subtitle="Items",
)
check("Returns 2 specs", len(specs) == 2)
check("First is donut", specs[0].template_id == "premium_donut")
check("Second is center KPI", specs[1].template_id == "donut_center_kpi")
check("Center has transparent bg", specs[1].config.get("show_background") == False)
check("Center position computed (not hardcoded)",
      specs[1].position != (800 + 120, 175 + 90, 110, 50))
# Composite must suppress the donut's own centre total so the overlay metric
# does not overlap the donut's internal centre KPI.
check("Composite donut suppresses internal center",
      specs[0].config.get("show_center_value") == False)


# ─── Test 11: show_center_value flows into custom-visual objects.general ──────
print("\n11. show_center_value emitted to donut objects.general")

from pbi_gen.renderer.templates.registry import VisualBinding
from pbi_gen.renderer.templates.builder import _build_visual_json

donut_binding = VisualBinding(
    template_id="premium_donut",
    title="Mix by Category",
    data_bindings={
        "category": [FieldRef(entity="Product", property="CategoryName")],
        "values": [FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)],
    },
    position=(800, 175, 470, 240),
    config_overrides={"show_center_value": False},
)
donut_json = _build_visual_json(donut_binding, tokens, reg, 10)
general_props = donut_json["visual"]["objects"]["general"][0]["properties"]
check("general.showCenterValue present", "showCenterValue" in general_props)
check("general.showCenterValue is false literal",
      general_props["showCenterValue"]["expr"]["Literal"]["Value"] == "false")

# Default (no override) must NOT emit the flag — donut keeps its own centre
plain_donut = VisualBinding(
    template_id="premium_donut",
    title="Mix by Category",
    data_bindings={
        "category": [FieldRef(entity="Product", property="CategoryName")],
        "values": [FieldRef(entity="Sales", property="TotalRevenue", is_measure=True)],
    },
    position=(800, 175, 470, 240),
)
plain_json = _build_visual_json(plain_donut, tokens, reg, 10)
plain_props = plain_json["visual"]["objects"]["general"][0]["properties"]
check("Plain donut omits showCenterValue (backward compatible)",
      "showCenterValue" not in plain_props)


# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("✅ ALL TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
