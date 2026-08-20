---
stage: 07
status: ready
title: Enterprise visual quality baseline
---

# Stage 07 — Enterprise Visual Quality Baseline

## Context

Stage 06 proved the full headless visual-quality loop:

```text
DashboardSpec
  → visual reference image
  → rendered Fabric report
  → headless screenshot
  → multimodal critic
  → structured revision
  → redeploy
  → screenshot/re-score
```

The loop worked, but it also exposed a more fundamental problem: the renderer's default visual-design floor is too low. The Executive Overview initially scored 3.4/10 and reached only 4.3/10 after adding visual titles and cross-filter behaviour.

Before allowing an autonomous critic to make dashboard-specific spec/model changes, raise the **generic baseline quality of every generated Power BI report**.

This stage is deliberately **not** a critic-driven optimisation stage. It is a renderer/design-system stage.

## Objective

Create a reusable enterprise visual-design baseline so that a valid `DashboardSpec` produces a materially more polished, coherent, C-suite-credible Power BI report **without dashboard-specific hacks and without changing the analytical specification**.

Use the existing Stage 06 retail dashboard as the principal before/after fixture, but every rule introduced must be defensible as a generic default for professional Power BI dashboards across domains such as finance, SaaS, operations, sales, retail and executive reporting.

## Core principle

The renderer should behave like a strong enterprise BI designer executing a specification, not like a serializer that leaves Power BI defaults untouched.

A new report should have a deliberate visual system before any screenshot critic sees it.

## Read first

1. Read `KIRO.md`.
2. Read Stage 04–06 TASK/REPORT files.
3. Inspect the Stage 06 reference image, `actual-before.png`, `actual-after.png`, and both critique JSON files.
4. Inspect the current renderer/theme/layout implementation in full.
5. Inspect the committed live PBIR output and working report definitions recovered during Stage 05c.
6. Inspect Power BI native formatting structures already known to work in the repository before inventing new PBIR property shapes.
7. Keep the Stage 02a `DashboardSpec` unchanged during the primary Stage 07 before/after comparison.

## Non-negotiable scope rule

**Do not improve the retail dashboard by special-casing retail.**

Do not add rules based on IDs, page names, metric names, specific values, or the contents of the Stage 02a fixture.

Improvements must derive from generic concepts such as:

- page role;
- visual type;
- visual priority;
- layout position;
- theme roles;
- semantic data type;
- measure format string;
- title presence;
- number of categories/series;
- dashboard density;
- filter role.

The retail fixture is evidence, not the implementation target.

## Required work

### 1. Introduce an explicit enterprise design system

Create a renderer-level design-system abstraction rather than scattering formatting constants through visual mappers.

It should define coherent reusable tokens/policies for at least:

- page background;
- surface/card background;
- primary text;
- secondary/muted text;
- accent colour;
- positive/negative/warning roles;
- border colour;
- typography scale;
- corner radius where Power BI supports it;
- border/shadow policy;
- spacing/gutter scale;
- title styling;
- KPI styling;
- chart styling;
- table/matrix styling;
- slicer styling.

Theme colours from `ThemeSpec` remain authoritative. The enterprise baseline should transform those semantic colour roles into a coherent presentation system rather than replacing them with fixture-specific colours.

### 2. Page composition and background

Improve report-level/page-level presentation generically.

Investigate and implement supported native Power BI formatting for:

- deliberate page background rather than raw/default white where appropriate;
- consistent canvas treatment;
- safe outer margins;
- page-level visual breathing room;
- consistent alignment boundaries.

Do not fake Power BI application chrome inside the report canvas.

### 3. Executive hierarchy

Use `VisualSpec.priority`, visual type, and page role to create stronger information hierarchy.

Generic behaviour should include:

- priority-1 KPI/summary visuals receiving strongest emphasis;
- secondary analysis visually subordinate to headline metrics;
- consistent title hierarchy;
- avoiding every visual looking equally important;
- preserving analytical layout while improving presentation.

Do not change which metrics or charts exist in the primary comparison fixture.

### 4. KPI/card baseline

Cards/KPIs are central to executive dashboards and must not look like unformatted Power BI defaults.

Implement a polished generic baseline covering where supported:

- clear metric label/title;
- prominent callout value;
- appropriate display units;
- consistent decimal precision;
- restrained card surface/background;
- padding/spacing;
- label/value contrast;
- subtle border or shadow rather than heavy boxes;
- semantic positive/negative emphasis where the spec/data supports it;
- consistent sizing across KPI rows.

Avoid decorative features that imply data not present in the spec.

### 5. Typography system

Establish a coherent typography hierarchy across the report.

At minimum differentiate:

- page/report headings where representable;
- visual titles;
- KPI values;
- KPI labels;
- axis labels;
- legends;
- table headers;
- table body text;
- slicer labels.

Use a safe Power BI-supported professional font stack. Typography must remain readable in headless screenshots at the target canvas size.

### 6. Number formatting

Improve visual display formatting based on semantic type and measure format strings.

Examples of generic expectations:

- currency values use sensible compact units when large;
- percentages use consistent precision;
- integer counts avoid meaningless decimals;
- negative values use standard readable formatting;
- axes do not show excessive precision;
- KPI cards do not display raw long numbers where compact notation is more appropriate.

Do not alter underlying DAX semantics.

### 7. Chart baseline by visual family

Create systematic formatting policies for common visual families used by the renderer.

#### Line/time-series
- restrained gridlines;
- readable time axis;
- sensible stroke/marker defaults;
- minimal clutter;
- clear series distinction;
- titles and legends positioned consistently.

#### Bar/column
- sensible axis/gridline defaults;
- category labels readable;
- data labels used selectively rather than everywhere;
- restrained gaps/padding;
- consistent series colouring.

#### Donut/pie where retained
- limited visual chrome;
- readable legend/data labels;
- no unnecessary 3D/decorative effects;
- avoid colour overload.

#### Scatter
- readable axes;
- sensible marker treatment;
- legend clarity;
- minimal grid clutter.

#### Map
- restrained surrounding chrome and title treatment using only known-safe properties.

Formatting must be generic and native-Power-BI compatible.

### 8. Colour discipline

Improve colour usage so generated dashboards do not look like default categorical rainbow charts.

Implement generic policies such as:

- dominant neutral/primary series treatment;
- accent colour reserved for emphasis;
- semantic negative/positive colours used deliberately;
- categorical palettes remain restrained and distinguishable;
- avoid using every theme colour simultaneously merely because it exists;
- maintain accessible contrast.

Do not hard-code the retail reference palette.

### 9. Container treatment

Create a consistent surface/container language across visuals.

Where supported by native PBIR formatting:

- consistent backgrounds;
- subtle border policy;
- restrained corner rounding;
- shadow only if robustly supported and visually appropriate;
- consistent internal title spacing;
- no heavy boxed-dashboard appearance.

If shadows/radius are unreliable in PBIR, prefer a clean flat system over fragile formatting.

### 10. Spacing and grid discipline

Improve the layout translator's generic spacing behaviour without changing the canonical analytical layout.

Requirements:

- consistent gutters;
- consistent outer page margin;
- no edge-to-edge visual collisions;
- visually aligned rows/columns;
- KPI cards align as a coherent group;
- titles have breathing room;
- avoid tiny gaps caused by direct grid arithmetic;
- deterministic output.

The same logical `LayoutSpec` must still produce the same broad composition; Stage 07 is refinement, not redesign.

### 11. Slicer/filter placement baseline

Stage 06 found that filters exist but are positioned off-screen. Fix this generically.

A generated dashboard with report/page filters must have a predictable visible filter treatment.

Implement a generic strategy, for example a compact filter row/rail, that:

- remains within canvas bounds;
- does not cover analytical visuals;
- uses consistent sizing;
- clearly identifies filter fields;
- respects page dimensions;
- handles multiple filters deterministically;
- works without knowing retail-specific filter names.

If necessary, reserve layout space for generated slicers rather than appending them after the main grid.

This is a functional and visual baseline defect and should be fixed in Stage 07.

### 12. Table/matrix baseline

Implement enterprise defaults for tables/matrices where supported:

- clear header styling;
- readable row density;
- restrained grid/border treatment;
- appropriate numeric alignment;
- sensible font sizing;
- alternating rows only if subtle and supported;
- semantic formatting for negative/risk values only when the spec provides that intent.

### 13. Titles and subtitles

Stage 06 added visual titles. Improve the generic title system further.

Titles should be:

- consistently positioned;
- typographically subordinate to page-level hierarchy;
- concise and readable;
- visually separated from plot area;
- not oversized or repeated unnecessarily.

Use `VisualSpec.title` as canonical content; do not rewrite analytical titles in the renderer.

### 14. Legend and axis discipline

Implement sensible generic defaults so charts are immediately legible.

Examples:

- hide legends for single-series visuals where they add no information;
- keep legends for genuine series distinctions;
- avoid redundant axis titles where visual title/category context is sufficient;
- use restrained gridlines;
- avoid label crowding;
- maintain readable font sizes.

Do not remove information required to interpret a visual.

### 15. Preserve semantic correctness

Stage 07 must not improve aesthetics by breaking analysis.

After changes verify:

- all six tables remain populated;
- refresh remains successful;
- all 11 measures still evaluate;
- all four pages remain present;
- all 29 source visuals remain represented;
- field bindings remain valid;
- no visual hangs or runtime regression;
- no filters disappear.

### 16. Before/after evidence

Use the existing Stage 06 `actual-after.png` as the primary **before** baseline for Executive Overview.

After Stage 07 changes:

1. rerender the **same unchanged Stage 02a DashboardSpec**;
2. redeploy using the known-good Stage 05c deployment strategy;
3. capture a new Executive Overview screenshot headlessly;
4. capture screenshots of Regional Analysis, Category Analysis and Risk Analysis as well;
5. commit the screenshots if safe.

Suggested names:

- `executive-baseline-after.png`
- `regional-baseline-after.png`
- `category-baseline-after.png`
- `risk-baseline-after.png`

### 17. Independent visual assessment

Use the Stage 06 multimodal critic in **assessment mode only**.

It may score and describe the before/after result, but **must not drive iterative dashboard-specific amendments during this stage**.

Run at least:

- Stage 06 Executive screenshot/reference → baseline score;
- Stage 07 Executive screenshot/same reference → new score.

Use the same rubric/model/prompt configuration as far as practical so the comparison is meaningful.

Also obtain an absolute assessment of all four Stage 07 pages against the enterprise-quality rubric even where no page-specific image reference exists.

### 18. Required improvement

A Stage 07 success requires evidence of material generic improvement.

Target:

- Executive Overview critic score improves by **at least +1.0** from the Stage 06 post-revision 4.3/10 baseline, OR reaches ≥6.0/10;
- no critical regression in analytical correctness or runtime behaviour;
- visual assessment identifies clear improvements in hierarchy, spacing, typography, colour discipline and filter visibility.

If the score does not improve materially, do not manipulate the critic prompt to obtain a higher score. Inspect the screenshots, diagnose why the design-system changes failed, and continue improving **generic renderer rules** within Stage 07.

Do not use dashboard-specific spec changes to hit the target.

### 19. Generic regression fixtures

The retail dashboard alone cannot prove generality.

Add at least two lightweight renderer fixtures/tests representing materially different dashboard shapes, for example:

- finance/variance dashboard;
- SaaS/operations dashboard.

These do not need live Fabric deployment if costly, but structural/render tests should verify that the enterprise design system applies without retail assumptions and that layout/slicer logic remains valid.

### 20. Design-system documentation

Document the resulting baseline clearly enough that future critic/revision stages know what is already guaranteed by the renderer.

Include:

- token definitions;
- visual-family policies;
- layout spacing policy;
- slicer placement policy;
- colour policy;
- number-formatting policy;
- supported PBIR formatting properties;
- known Power BI limitations.

Avoid a giant style guide. Document the executable design contract.

## Architecture expectation

Prefer a structure conceptually similar to:

```text
renderer/
  design_system.py
      EnterpriseDesignSystem
      TypographyTokens
      SpacingTokens
      SurfaceTokens
      ColourPolicy
      VisualFormattingPolicy

  formatting/
      cards.py
      charts.py
      tables.py
      slicers.py

  layout.py
      grid translation
      reserved filter area
      gutters/margins
```

Exact modules are implementation decisions. The important requirement is that generic visual-quality policy is explicit, testable and separated from dashboard-specific analytical intent.

## Tests

Add meaningful automated tests covering at minimum:

1. design-system token generation from ThemeSpec;
2. no retail-specific constants/IDs in design-system logic;
3. KPI/card formatting structure;
4. chart-family formatting structure;
5. table/matrix formatting structure;
6. slicer formatting and within-canvas placement;
7. gutter/margin layout behaviour;
8. priority-driven hierarchy where implemented;
9. number/display formatting rules;
10. legend/axis defaults;
11. deterministic repeated render;
12. all 29 live-fixture visuals preserved;
13. all live-fixture slicers visible/in-bounds;
14. finance fixture structural render;
15. SaaS/operations fixture structural render;
16. full existing suite remains green.

Any new PBIR formatting property used must have regression coverage based on a known-working schema/structure where practical.

## Non-goals

Do NOT expand Stage 07 into:

- critic-driven spec mutation;
- changing the Stage 02a analytical design to improve its score;
- automatic visual-type replacement;
- adding semantic columns solely for the retail fixture;
- conversational revisions;
- production service-principal auth;
- custom Power BI visuals;
- pixel-perfect reproduction of the Stage 06 image mockup;
- fake application chrome;
- exhaustive Power BI formatting support.

The goal is a **strong generic starting point**, not perfection on one report.

## Acceptance criteria

Stage 07 is complete when:

- an explicit reusable enterprise design system exists in the renderer;
- generic page/surface/typography/colour/spacing policies are implemented;
- KPI cards have a polished default treatment;
- major chart families have coherent enterprise formatting defaults;
- tables/matrices and slicers have coherent defaults;
- slicers are visible and remain within canvas bounds;
- layout gutters/margins/alignment are materially improved;
- number formatting and visual chrome are more disciplined;
- the unchanged Stage 02a spec is rerendered and deployed successfully;
- headless screenshots exist for all four pages;
- all 29 source visuals remain present;
- all 11 measures remain functional;
- report runtime remains healthy;
- Executive visual-quality score improves by ≥1.0 from 4.3 OR reaches ≥6.0 using a comparable critic assessment;
- finance and SaaS/operations regression fixtures demonstrate generic applicability;
- full automated suite passes;
- Stage 07 evidence/manifest is committed;
- `REPORT.md` is committed and pushed.

## REPORT.md requirements

Include:

- implementation summary;
- design-system architecture;
- generic design principles implemented;
- exact renderer/PBIR formatting areas changed;
- page/layout spacing policy;
- slicer placement solution;
- KPI/card treatment;
- typography hierarchy;
- colour policy;
- chart-family defaults;
- table/matrix defaults;
- number-formatting behaviour;
- before/after Executive screenshots;
- screenshots for all four Stage 07 pages;
- comparable Executive critic scores before and after;
- four-page visual assessment;
- evidence that the Stage 02a DashboardSpec was not changed to obtain the improvement;
- finance/SaaS fixture results;
- semantic/runtime regression checks;
- automated test results;
- known Power BI formatting limitations;
- recommended next stage.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
