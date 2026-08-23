# Stage 12A — Responsive Visual-System Cleanup

## Purpose

Improve the shared visual system used by all generated dashboards before changing deployment architecture or replacing Kiro as the runtime reasoner.

This stage is deliberately limited to three cross-cutting presentation concerns:

1. **donut + centre KPI centring at all supported sizes/resolutions**;
2. **one consistent visual-title/header system across all visual families**;
3. **parameterised colour configuration for reusable visuals**.

Then apply the shared fixes to the existing Executive, Financial, Customer and Product dashboards and prove there are no regressions.

Do not start Stage 12B deployment/navigation work in this stage.

---

## Context

The current system has successfully demonstrated:

- zero-touch private custom-visual delivery;
- reusable premium templates;
- rapid page generation from compact specs;
- four dashboard domains: Executive, Financial, Customer and Product.

However, visual-system consistency still has several recurring defects:

- `premium_donut` + `donut_center_kpi` has relied on manually positioned overlays and can drift from the actual donut centre when size/resolution changes;
- titles/headers are inconsistently placed/aligned across native and custom visuals;
- colours remain too tightly coupled to template implementation and should be driven by shared tokens/configuration.

These are generic renderer/template-system issues. Fix them once at the shared level.

## Read first

Review:

- `KIRO.md`;
- `docs/TEMPLATE_INVENTORY.md`;
- Stage 08, 09, 10 and 11 TASK/REPORT files;
- current `DesignTokens`, `TemplateRegistry`, `PageBuilder`, `rapid_engine.py`;
- native visual builders and custom visual source/configuration;
- existing Executive, Financial, Customer and Product page configs/screenshots.

Do not introduce domain-specific rendering branches.

---

# Part A — Responsive donut + centred KPI

## 1. Treat donut + centre KPI as a logical composite

The current `premium_donut` + `donut_center_kpi` pairing must no longer depend on caller-authored absolute coordinates that happen to look centred at one size.

Introduce a generic composite-layout mechanism, helper, or equivalent abstraction such that a donut visual can declare a centre overlay and the renderer computes the overlay geometry from the donut container.

The caller should conceptually specify:

- donut bounds;
- centre overlay template/content/binding;
- optional centre-overlay width/height policy.

The renderer should derive the overlay x/y automatically.

Do not hard-code coordinates for Executive, Financial, Customer or Product.

## 2. Centre against the rendered donut plot, not merely the panel

A key requirement is that the KPI appears visually centred in the actual donut hole.

Native Power BI donut visuals may reserve space for:

- title/header;
- legend;
- labels;
- internal padding.

Therefore simply centring the KPI inside the visual rectangle is not sufficient if the donut plot shifts due to legend/title layout.

Choose a robust generic strategy. Options may include:

- standardising donut legend placement and plot geometry so the hole centre is deterministic;
- computing an explicit plot-region offset from known Power BI formatting/layout rules;
- adjusting the native donut template so the chart occupies a predictable sub-region;
- another generic renderer-owned method backed by rendered evidence.

Document the approach and why it remains stable.

## 3. Responsive test matrix

Test the donut + centre KPI combination at multiple realistic sizes rather than one screenshot.

At minimum test:

- 470×240 (current default);
- a narrower supporting-panel size;
- a wider supporting-panel size;
- at least one taller/shorter variant if supported by the page system;
- the sizes currently used by Executive, Financial, Customer and Product.

If practical, include at least two screenshot viewport/resolution scenarios as well, while preserving the report canvas dimensions/scaling behaviour.

## 4. Donut centring acceptance gate

For every supported test case:

- centre KPI must lie visually inside the donut hole;
- horizontal centre error should be **<=5 px** relative to the intended donut-hole centre in the unscaled 1280×720 canvas coordinate system;
- vertical centre error should be **<=5 px**;
- no overlap with donut arcs, legend or labels;
- no clipping;
- resizing must not require page-specific coordinate overrides.

If automated pixel/geometry measurement is difficult, provide annotated rendered evidence plus deterministic geometry assertions. Do not accept “looks close on one screenshot”.

---

# Part B — Unified visual header/title system

## 5. Choose and enforce one header grammar

Audit all registered templates and determine the strongest consistent rule for visual titles.

The goal is that all visuals appear to share one design system, regardless of whether the underlying visual is native Power BI or custom.

Prefer one of these strategies unless evidence supports another:

### Preferred approach: title inside the panel, renderer-controlled

Each visual panel owns a predictable header region with:

- identical left inset;
- identical baseline alignment;
- consistent title font size/weight/colour;
- optional subtitle/legend region where applicable;
- fixed spacing between title and plot area.

Native visual built-in titles should be disabled when renderer-owned headers are used.

### Alternative: external renderer-owned title

If inside-panel consistency cannot be made robust across the current visual set, place all visual titles immediately above visual containers using one shared geometry rule.

Do **not** leave some templates with internal titles and others with page-level labels unless there is a clearly documented semantic exception.

## 6. Header alignment requirements

Across a page:

- visual titles in the same row must share a common baseline;
- title left padding should be identical for panels using the same surface grammar;
- title-to-plot spacing must be visually consistent;
- native/custom visual differences should not be obvious from header placement;
- no duplicated titles (renderer title + Power BI native title);
- titles must not clip at current supported sizes.

Centralise header geometry/tokens. Do not copy constants across templates.

## 7. Template coverage

Apply the header system to every template where a title is relevant, including at minimum:

- premium_trend;
- premium_bar;
- premium_column;
- premium_donut;
- premium_table;
- premium_waterfall;
- premium_gauge;
- premium_insights;
- KPI cards only where their internal label grammar is intentionally different.

Document deliberate exceptions.

---

# Part C — Parameterised visual colours

## 8. Centralise colour semantics

Extend the shared design-token/template configuration system so visual colours can be changed through configuration rather than editing template code.

At minimum support generic concepts such as:

- canvas;
- panel/surface;
- border;
- primary text;
- secondary/muted text;
- primary accent;
- secondary accent;
- categorical series palette;
- positive;
- negative;
- warning;
- neutral comparison/prior-period series;
- gridline/axis colour.

Do not expose only raw hard-coded hex values scattered across call sites. Use named semantic tokens.

## 9. Template colour configuration

Ensure existing templates consume shared colour configuration wherever technically feasible.

Cover at minimum:

- premium KPI accents/icons;
- premium trend current/comparison series and fill;
- native bar/column series;
- donut categorical palette;
- waterfall positive/negative/total semantics;
- gauge accents where configurable without changing its functional contract;
- insights accents if supported by current implementation.

If a custom visual currently hardcodes a colour internally, refactor it generically to receive formatting/configuration values where feasible.

This is allowed because it is a **generic improvement to an existing template**, not a new template.

## 10. Backward-compatible defaults

The default token set must reproduce the current accepted dark executive theme closely enough that existing dashboards do not unexpectedly change colour simply because parameterisation was introduced.

Add at least one alternate test palette/configuration proving the system is genuinely parameterised. The alternate palette is test evidence only; do not permanently restyle the four accepted dashboards unless explicitly requested.

---

# Part D — Existing-dashboard retrofit

## 11. Regenerate all four dashboards

Apply the shared Stage 12A improvements to:

- Executive Overview;
- Financial Performance;
- Customer Performance;
- Product Performance.

For dashboards containing a donut + centre KPI, use the new composite placement path.

For every dashboard, use the unified header rules and default shared colour tokens.

Do not redesign the analytical content.

## 12. Preserve semantics and layout

This stage is visual-system cleanup, not a business-analysis rewrite.

Do not change:

- measure definitions except where required to fix a regression;
- chart families;
- page information architecture;
- established navigation behaviour (functional nav comes in Stage 12B);
- semantic model content unless necessary for regression repair.

The dashboards should look like cleaner, more consistent versions of themselves.

---

# Part E — Automated tests

Add/extend tests covering at least:

1. donut-centre overlay position is derived from parent donut geometry;
2. overlay remains centred across the supported donut size matrix;
3. no dashboard config contains manual donut-centre absolute coordinates where the composite mechanism should be used;
4. shared header tokens/geometry are used by applicable templates;
5. native visual titles are disabled when renderer-owned header is active;
6. custom visual title/header spacing follows the shared contract where applicable;
7. colour tokens have backward-compatible defaults;
8. changing a palette/config changes visual colour payloads without editing template source;
9. semantic positive/negative colours remain distinct;
10. Executive, Financial, Customer and Product configs/builds remain valid;
11. all existing tests remain green.

---

# Part F — Rendered acceptance evidence

## 13. Required screenshots

Capture final headless screenshots for all four dashboards.

Additionally capture a donut-centre test/contact sheet or equivalent evidence showing the composite at multiple sizes.

If practical, create a header-alignment comparison sheet demonstrating at least one row containing multiple visual families aligned to the same header baseline.

## 14. Human visual inspection questions

REPORT must explicitly answer:

- Is the centre KPI visually centred in the donut hole at every supported tested size?
- Does changing donut width/height require any page-specific overlay coordinates?
- Are headers/titles aligned consistently across native and custom visuals?
- Is there any obvious duplicate-title or title-to-plot spacing inconsistency?
- Can visual colours now be changed via configuration/tokens without editing visual source?
- Do the four existing dashboards retain their accepted visual identity?

Any “no” to the first five means Stage 12A is not complete.

---

# Hard acceptance criteria

Stage 12A is complete only if:

- [ ] donut centre KPI positioning is derived generically from donut/composite geometry;
- [ ] centre error <=5 px horizontally and vertically across all supported tested sizes;
- [ ] no overlap/clipping at those sizes;
- [ ] no page-specific centre-coordinate hacks remain for existing dashboards;
- [ ] one shared header/title grammar is applied across all relevant visual templates;
- [ ] same-row title baselines are visibly aligned;
- [ ] duplicate native/renderer titles are eliminated;
- [ ] visual colours are driven by shared semantic configuration/tokens;
- [ ] at least one alternate-palette test proves parameterisation works;
- [ ] default palette remains visually compatible with current dashboards;
- [ ] Executive, Financial, Customer and Product all build, deploy and render zero-touch;
- [ ] semantic/model correctness is unchanged;
- [ ] existing automated tests plus new Stage 12A tests pass.

Do not mark complete on code inspection alone. Rendered evidence is mandatory.

---

# Evidence package

Commit under `docs/stages/12a-responsive-visual-system-cleanup/`:

- donut responsive test evidence/contact sheet;
- final Executive screenshot;
- final Financial screenshot;
- final Customer screenshot;
- final Product screenshot;
- optional header-alignment evidence sheet;
- alternate-palette test screenshot/evidence;
- `REPORT.md`.

Source changes belong in the appropriate renderer/template/custom-visual directories.

## REPORT.md requirements

Include:

- previous donut-centre failure mode;
- new composite/geometry architecture;
- supported size test matrix and measured centre offsets;
- final header/title architecture and exceptions;
- colour-token/configuration architecture;
- alternate-palette proof;
- automated test results;
- screenshots for all four dashboards;
- zero-touch deployment results;
- any known template-specific limitations;
- explicit PASS/FAIL against every hard acceptance criterion;
- conclusion: `PASS` or `FAIL`.

Do not begin persistent-report update/navigation implementation until this stage has passed.