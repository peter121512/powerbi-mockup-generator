---
stage: 07a
status: ready
title: Power BI styling compatibility and design-system graduation
---

# Stage 07a — Power BI Styling Compatibility & Design-System Graduation

## Context

Stage 07 created a reusable `EnterpriseDesignSystem`, improved margins/gutters/page background, and fixed generated slicers so they are visible in a dedicated filter row. All four live pages render headlessly and 373 tests pass.

However, Stage 07 did **not** achieve the intended generic visual-quality uplift. Most card/chart/table formatting policies exist in code but are not applied to deployed visuals because several attempted PBIR formatting properties caused rendering regressions. Only a small safe subset, principally `general.title`, is currently active.

Do not move to dashboard-specific/spec-level optimisation yet.

This stage exists to answer a foundational renderer question:

> **Which native Power BI formatting mechanisms and PBIR/theme properties can we safely generate, and how much of the existing enterprise design system can we graduate onto them?**

The result should be an empirically validated styling compatibility layer backed by real Fabric rendering evidence.

## Objective

Systematically test Power BI styling mechanisms in isolation, establish a machine-readable **known-safe formatting capability matrix**, then wire the Stage 07 enterprise design-system tokens into the proven-safe mechanisms.

The target is not exhaustive Power BI formatting support. The target is the highest-leverage generic styling needed to make generated dashboards materially more polished without runtime/rendering instability.

## Core principle

Do not infer that a PBIR property is safe merely because:

- it appears in a schema;
- Power BI Desktop writes something similar;
- deployment accepts the JSON;
- a unit test passes.

For important formatting properties, **actual Fabric render evidence is the authority**.

A property is "safe" only after the report loads, the visual renders correctly, and the intended formatting is visibly present without collateral defects.

## Read first

1. Read `KIRO.md`.
2. Read Stage 05c, 06 and 07 TASK/REPORT files.
3. Inspect all Stage 07 screenshots and `critique-stage07.json`.
4. Inspect `src/pbi_gen/renderer/design_system.py` and all `renderer/formatting/*` modules.
5. Inspect the currently deployed working PBIR output.
6. Inspect known-good Power BI-generated PBIR examples already available in this repo/archive where relevant.
7. Inspect the generated `theme.json` implementation and Power BI theme capabilities.
8. Reuse the Stage 06/07 headless embed-token + Chromium capture path.
9. Preserve the Stage 02a `DashboardSpec` unchanged for the principal comparison.

## Required work

### 1. Build a minimal formatting compatibility harness

Create a development/test harness that can deploy a deliberately small diagnostic report or diagnostic page containing representative native visuals.

It should make it cheap to test one formatting capability at a time.

Representative visual families should include at least:

- card/KPI;
- line chart;
- clustered bar/column chart;
- table or matrix;
- slicer;
- optionally donut/scatter where useful.

The harness must support:

```text
known-good baseline
  → apply one formatting capability
  → render/deploy
  → headless capture
  → classify safe / unsafe / ineffective
```

Avoid repeatedly redeploying the entire 29-visual retail report for every micro-test if a smaller diagnostic artifact can provide reliable evidence.

### 2. Establish capability categories

Classify each tested capability as one of:

- `safe` — renders correctly and visibly produces intended effect;
- `safe_with_constraints` — works only for certain visual families/property shapes;
- `ineffective` — accepted but has no observable intended effect;
- `unsafe` — causes clipping, rendering artifacts, visual failure, runtime instability, or other regression;
- `unknown` — not yet validated.

Record the exact mechanism used:

- PBIR visual `objects`;
- report `theme.json`;
- page-level formatting;
- visual-type-specific property;
- semantic-model format string where applicable.

### 3. Prefer theme-level styling where appropriate

Stage 07 suggests theme JSON may be safer than direct per-visual PBIR object mutation.

Systematically test whether the enterprise baseline can be expressed through a custom Power BI theme for generic properties such as:

- font family;
- foreground/text colours;
- visual title defaults;
- background/surface defaults;
- border defaults;
- data colours;
- axis text/gridline defaults;
- legend text/default placement where theme supports it;
- table header/body defaults;
- slicer defaults.

Use theme-level styling when it is demonstrably more robust and still allows required semantic variation.

Do not force all styling through PBIR if theme JSON is the better native abstraction.

### 4. Card/KPI compatibility tests — highest priority

Cards are a major contributor to executive polish.

Test in isolation, one capability at a time where practical:

- callout/value font size;
- callout/value font weight;
- callout/value colour;
- category/label font size;
- category/label colour;
- title styling;
- display units;
- decimal precision;
- background/surface;
- border;
- corner radius if supported;
- padding where supported;
- semantic colour overrides where safe.

Determine whether the correct current native card visual schema differs from assumptions in Stage 07.

Do not accept clipping/overflow merely to obtain larger KPI text.

### 5. Typography compatibility tests

Test and validate generic typography controls for:

- visual titles;
- card callout values;
- card labels;
- axis labels;
- legend text;
- table headers;
- table body;
- slicer text.

Determine which controls should come from theme JSON versus visual objects.

The target is a coherent typography hierarchy visible in screenshots.

### 6. Surface/container compatibility tests

Test:

- visual background colour;
- transparency;
- border on/off;
- border colour;
- border width where supported;
- corner radius;
- shadow.

Prefer subtle, stable styling. If radius/shadow remain unreliable, classify them unsafe and use a high-quality flat design instead.

### 7. Chart-axis/gridline compatibility tests

For line/bar/column visuals test:

- axis label font size/colour;
- axis title visibility;
- gridline visibility;
- gridline colour;
- gridline stroke/weight if available;
- display units;
- decimal precision;
- zero-line behaviour where relevant.

The goal is reduced default Power BI clutter, not maximum customization.

### 8. Legend compatibility tests

Test:

- legend visibility;
- position;
- font size;
- font colour;
- title visibility.

Preserve semantic readability. Renderer logic may hide a redundant single-series legend only if that determination is generic and reliable.

### 9. Series/data-colour compatibility tests

Test the safest way to enforce Stage 07 colour discipline:

- theme `dataColors`;
- per-series colour assignment;
- semantic positive/negative overrides;
- categorical palettes.

Prefer theme-level palette control for generic categorical behaviour unless per-series control is demonstrably safe and necessary.

### 10. Table/matrix compatibility tests

Test:

- header background;
- header text colour/font size;
- body text font size/colour;
- row padding/density where supported;
- gridlines/borders;
- alternating rows;
- numeric alignment where controllable;
- total-row styling if relevant.

The goal is a restrained enterprise table, not a heavily formatted spreadsheet.

### 11. Slicer compatibility tests

The Stage 07 placement fix must remain.

Test visual styling for:

- title/header;
- font size/colour;
- background/border;
- dropdown/list style where safely controllable;
- selection text;
- compact treatment appropriate for the top filter row.

Do not compromise slicer functionality for aesthetics.

### 12. Number formatting path

Separate semantic number formatting from visual formatting.

Validate which requirements should be handled through:

- TMDL measure/column `formatString`;
- visual display-unit properties;
- theme defaults.

Ensure generic output supports professional rendering of:

- currency;
- percentage;
- counts;
- large numbers;
- negative values;
- sensible decimal precision.

Do not alter DAX meaning.

### 13. Machine-readable safe-list

Commit a machine-readable capability registry, e.g.:

`src/pbi_gen/renderer/formatting/capabilities.json`

or a typed Python equivalent with serializable evidence.

Each capability should record at least:

- capability ID;
- visual family;
- mechanism;
- status;
- property path/shape or theme section;
- constraints;
- evidence screenshot/test identifier;
- notes.

Renderer formatting code must consume or correspond clearly to this registry so future developers do not accidentally re-enable known-unsafe properties.

### 14. Evidence capture

For each important capability group, capture enough headless evidence to make classification auditable.

Do not commit hundreds of nearly identical screenshots. Prefer contact sheets or a small set of clearly named diagnostic captures where one image demonstrates several independently isolated tests.

Suggested directory:

`docs/stages/07a-styling-compatibility/evidence/`

Include an evidence index/manifest mapping capability IDs to captures.

### 15. Graduate the enterprise design system

After establishing the safe-list, wire as much of the existing Stage 07 `EnterpriseDesignSystem` as possible into actual deployed output.

At minimum attempt to graduate safe styling for:

- typography;
- KPI/card presentation;
- surface/container treatment;
- chart axes/gridlines;
- legends;
- data colours;
- tables/matrices;
- slicers;
- number/display formatting.

Do not keep a design token merely because it exists. Report whether each important token now reaches Power BI output, remains unsupported, or is intentionally deferred.

### 16. Re-render the unchanged retail fixture

After graduation:

1. use the exact unchanged Stage 02a `DashboardSpec`;
2. render with the improved generic design system;
3. deploy through the known-good Stage 05c path;
4. confirm refresh/runtime health;
5. capture all four pages headlessly.

No retail-specific formatting rules are permitted.

### 17. Visual assessment

Use the multimodal critic in **assessment-only** mode again.

Do not allow it to mutate the spec or renderer during this stage except as human-readable diagnosis feeding further **generic compatibility work**.

Evaluate:

- Executive Overview against the same Stage 06 reference image/rubric;
- all four pages against the enterprise-quality rubric.

Because Stage 07 identified critic run-to-run variance, improve evaluation robustness:

- run the Executive assessment at least 3 times using the same screenshot/model/rubric where cost is reasonable;
- report median overall score and range;
- compare Stage 07 and Stage 07a using the same methodology if possible;
- do not cherry-pick the highest run.

### 18. Visual improvement target

The primary goal is visibly better generic styling, not gaming one scalar score.

Nevertheless use a concrete target:

- median Executive score should improve materially over Stage 07;
- target **≥5.5/10 median** without any DashboardSpec changes;
- renderer-controlled dimensions such as typography, KPI prominence, whitespace, colour discipline, filter presentation and visual polish should show clear improvement;
- if spec-level issues still cap the overall score, report the renderer-controlled dimension changes separately.

Do not change month sorting or mixed-scale visual choices in this stage merely to raise the score.

### 19. Runtime safety

Every graduated formatting capability must preserve:

- successful report loading;
- no endless spinner;
- no broken visual icons;
- no clipping introduced by styling;
- all 29 source visuals;
- all generated slicers;
- all four pages;
- all 11 measures;
- valid field bindings;
- successful semantic-model refresh.

If a capability creates instability, mark it unsafe and remove it from active renderer output.

### 20. Generic fixture verification

Run the Stage 07 finance and SaaS/operations fixtures through the graduated design system.

Add or strengthen tests demonstrating that:

- safe styling is visual-family driven rather than retail-specific;
- theme generation works with materially different colour palettes;
- cards/charts/tables/slicers do not depend on retail metric names;
- layouts remain within bounds.

### 21. Documentation

Document the practical Power BI styling contract discovered by this stage.

This should answer:

- what belongs in theme JSON;
- what belongs in PBIR visual objects;
- what belongs in semantic model format strings;
- what is safe by visual family;
- what is unsafe or currently unknown;
- what Power BI/Fabric version/context was tested;
- how to add a new formatting capability safely.

This becomes the foundation for later critic-driven optimisation.

## Suggested execution strategy

Do not attempt every property simultaneously.

Use an empirical progression such as:

```text
baseline diagnostic visual
→ title typography
→ screenshot/check
→ surface
→ screenshot/check
→ callout/labels
→ screenshot/check
→ axes/gridlines
→ screenshot/check
→ legends/colours
→ screenshot/check
→ table/slicer
→ screenshot/check
→ combine only proven-safe properties
→ retail fixture
```

When a combined result fails despite individual properties being safe, test interactions and record constraints.

## Tests

Add automated coverage for at least:

1. capability registry schema/status values;
2. active renderer properties must be marked safe/safe_with_constraints;
3. unsafe capabilities cannot be emitted accidentally;
4. theme JSON generation from design-system tokens;
5. card formatting using only validated capabilities;
6. chart formatting using only validated capabilities;
7. table formatting using only validated capabilities;
8. slicer formatting using only validated capabilities;
9. number formatting path;
10. no retail-specific IDs/names/constants;
11. finance fixture;
12. SaaS/operations fixture;
13. deterministic render;
14. all live visuals/slicers preserved and in bounds;
15. full existing suite remains green.

Live diagnostic/Fabric tests should remain separate from routine unit tests.

## Non-goals

Do NOT expand Stage 07a into:

- changing the DashboardSpec;
- month-sort semantic fixes;
- replacing mixed-axis visual types;
- critic-driven spec mutation;
- automatic dashboard redesign;
- custom visuals;
- pixel-perfect mockup reproduction;
- exhaustive reverse engineering of every Power BI formatting property;
- production multi-tenant deployment/auth architecture.

This is **styling compatibility + generic renderer graduation**.

## Acceptance criteria

Stage 07a is complete when:

- a repeatable isolated formatting compatibility harness exists;
- important card, typography, surface, chart, legend, colour, table, slicer and number-format capabilities have been empirically classified;
- a machine-readable safe/unsafe capability registry is committed;
- evidence links important classifications to actual headless Fabric renders;
- theme JSON is used where testing proves it is the safer native mechanism;
- active renderer formatting is restricted to proven-safe capabilities;
- materially more of `EnterpriseDesignSystem` reaches actual deployed visuals than in Stage 07;
- the unchanged Stage 02a retail spec is rerendered and deployed successfully;
- all four live pages are captured headlessly after graduation;
- all 29 visuals, slicers, 11 measures and runtime behaviour remain healthy;
- finance and SaaS/operations fixtures remain valid;
- Executive critic assessment uses multiple runs and reports median/range;
- target median Executive score is ≥5.5/10, or the report provides strong screenshot evidence of material renderer-controlled improvement plus a precise remaining Power BI limitation;
- full automated suite passes;
- evidence manifest and `REPORT.md` are committed.

## REPORT.md requirements

Include:

- compatibility-harness architecture;
- capabilities tested and count by status;
- safe-list summary by visual family;
- unsafe/ineffective properties and observed failure modes;
- theme-vs-PBIR-vs-TMDL conclusions;
- capability registry path;
- evidence index path;
- design-system tokens successfully graduated to live output;
- tokens still unsupported/deferred;
- before/after screenshots;
- three-run Executive critic scores, median and range;
- all-four-page assessment;
- evidence that Stage 02a DashboardSpec remained unchanged;
- runtime/semantic regression checks;
- finance/SaaS fixture results;
- automated test results;
- known limitations;
- explicit recommendation on whether the renderer's generic visual baseline is now strong enough to proceed to spec-level/critic-driven optimisation.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
