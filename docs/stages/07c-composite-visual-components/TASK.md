---
stage: 07c
status: ready
title: Composite visual components for premium executive design
---

# Stage 07c — Composite Visual Components for Premium Executive Design

## Context

Stages 07–07b established that:

- the functional Power BI pipeline is working end-to-end;
- report composition, layout, themes, filters and native visual formatting can be controlled reliably;
- native Power BI reports still visually read too strongly as “Power BI with formatting” when compared with high-end reference mockups;
- the first 07b completion pass reached only ~2–3/10 on a strict visual-only rubric against the target references;
- simply styling stock visuals more aggressively does not close the gap.

Do **not** accept “native Power BI visuals are the ceiling” until we test a different architectural approach.

The key hypothesis for this stage is:

> Treat native Power BI visuals as **data-rendering primitives** embedded inside renderer-owned composite components, rather than as complete UI components.

Example:

```text
Current KPI
  = one native Power BI card visual

Composite KPI
  = renderer-owned background/surface
  + renderer-owned label textbox
  + stripped native card showing value only
  + renderer-owned accent/divider/context
```

Likewise:

```text
Current chart tile
  = native chart with title, legend, axes, container chrome

Composite chart module
  = renderer-owned section/title/subtitle/surface
  + stripped native chart used primarily for the plot
  + renderer-owned supporting labels/dividers/context
```

This could materially reduce the default-Power-BI appearance while preserving native interactivity and query behaviour.

## Product goal

The visual target remains **strictly the same standard as the three premium executive dashboard examples/reference images previously selected for this project**.

The required reaction remains:

> “Wow — this looks like a bespoke executive dashboard we could proudly demo to senior leadership or show company-wide.”

The target is **not**:

- “better than default Power BI”;
- “professional enough”;
- “clean and functional”;
- “the best Power BI can reasonably do” unless that ceiling is demonstrated empirically after testing the composite-component approach.

## Objective

Determine whether composite visual components built from native Power BI data visuals + native shapes/textboxes/backgrounds can substantially close the visual gap to the three premium references.

If the hypothesis works, implement a reusable composite-component system for the highest-impact visual families and prove a major improvement on the Executive Overview.

If it does not work, produce concrete evidence that this approach cannot achieve the target, rather than asserting a platform limitation abstractly.

## Scope freeze

Do not change:

- analytical content;
- DAX;
- semantic model;
- month sorting;
- mixed-axis logic;
- chart type selection;
- business story;
- Stage 02a source visual inventory.

This is a **presentation architecture** experiment only.

## Read first

1. Read `KIRO.md`.
2. Read Stage 07a, 07b TASK/CONTINUE/REPORT files.
3. Inspect the three premium reference mockups created for 07b.
4. Inspect the current 07b screenshots and visual-only assessments.
5. Inspect all known-safe PBIR/theme capabilities from 07a.
6. Inspect existing primitives/textbox/shape generation code.
7. Inspect working PBIR examples for card visuals, text boxes, shapes, chart visuals and z-order behaviour.
8. Reuse the Stage 05c direct Fabric report deployment path and Stage 06 headless screenshot pipeline.

## Core design hypothesis

The renderer should control the visual shell.

Native Power BI visuals should be stripped down where possible to their data-rendering essence, while the renderer owns:

- titles;
- labels;
- subtitles/context;
- surfaces;
- borders/accent rules;
- spacing;
- grouping;
- section hierarchy;
- decorative structure;
- page-level visual identity.

This is analogous to using a charting library inside a product UI, rather than accepting the chart library’s default container as the whole product experience.

## Required work

### 1. Build a composite component abstraction

Introduce a reusable renderer-level abstraction for composite visual modules.

Conceptually:

```text
CompositeComponent
  ├── background/surface primitives
  ├── title/subtitle/context primitives
  ├── one or more native Power BI data visuals
  ├── optional accent/divider primitives
  └── deterministic z-order/layout
```

The component must own a single logical bounding box and place its internal parts deterministically within it.

Do not hard-code retail IDs or labels.

### 2. Composite KPI component — highest priority

Build and test a premium KPI component where the native card visual is responsible primarily for rendering the value.

Renderer-owned shell should handle, where useful and safe:

- label;
- visual hierarchy;
- surface/background;
- border/accent rule;
- optional subtitle/context only when already present in structured metadata;
- spacing/padding;
- priority emphasis;
- semantic colour accents.

Native card should be stripped of redundant elements where possible:

- hide category label if external label exists;
- hide title if external title exists;
- remove unnecessary background/container chrome;
- make value fill the intended value region without clipping.

Test at least 3 materially different KPI shell designs inspired by the premium references.

Do not invent arrows, trends or deltas absent from the spec/model.

### 3. Composite chart component

Build a reusable chart module where the renderer owns the surrounding UI and the native chart is used primarily for the plot.

Test externalizing:

- chart title;
- subtitle/context;
- section label;
- surface/container;
- accent rule;
- plot-area framing;
- legend context where practical;
- supporting footnote/source/context if structured metadata exists.

Native chart should suppress redundant title/container chrome and use restrained axes/gridlines.

Goal: make the chart feel embedded in a bespoke dashboard module rather than displayed as a stock Power BI tile.

### 4. Composite filter component

Evaluate whether the current slicer strip can be improved using composite shells:

- external compact label;
- stripped slicer body;
- consistent surface;
- tighter spacing;
- clearer context hierarchy;
- less default slicer chrome.

Do not break selection behaviour.

### 5. Section / content-block component

Create reusable structural containers for page sections so that multiple related visuals can read as a single designed block.

Examples:

- hero analysis block;
- KPI summary block;
- supporting insights block;
- detail block.

Use native shapes/textboxes as the shell and position the existing data visuals inside.

Avoid heavy card-within-card nesting.

### 6. Strip stock visual chrome aggressively but safely

Systematically test which native visual elements can be hidden because the composite shell replaces them:

- native visual titles;
- category labels;
- backgrounds;
- borders;
- legend titles;
- axis titles;
- redundant labels;
- internal headers where appropriate.

Do not hide information necessary to interpret the visual.

Document the safe “stripped visual” configuration for each family.

### 7. Z-order and hit-testing validation

Composite shells must not block visual interaction.

Validate:

- shape/text layers do not intercept slicer/chart interaction where that matters;
- z-order keeps data visuals interactable;
- external text does not obscure hover/click regions;
- cross-filtering still works;
- visual selection remains functional where relevant.

If Power BI layering causes interaction conflicts, design around them rather than silently accepting broken UX.

### 8. Pixel-geometry discipline

Composite components require more precise geometry than current high-level regions.

Introduce reusable internal layout tokens for:

- shell padding;
- title block height;
- subtitle gap;
- value region;
- plot region;
- footer/context region;
- accent width;
- component gutters.

Use deterministic geometry derived from component size/archetype, not fixture-specific coordinates.

### 9. Build three Executive composite prototypes

Using the same frozen Executive Overview content, generate three materially distinct but generic composite designs, each inspired by one of the premium references:

1. **Boardroom Light Composite**
2. **Editorial Composite**
3. **Modern Enterprise Composite**

All three must use the same underlying source visuals/data.

Capture each headlessly.

The purpose is to test whether the composite approach—not tiny style tweaks—can materially change the perceived design quality.

### 10. Visual-only evaluation against the three example/reference standards

Use the same strict visual-only rubric from 07b.

Explicitly ignore analytical-choice defects.

For each composite prototype run at least one evaluation covering:

- first-impression professionalism;
- executive credibility;
- composition/hierarchy;
- typography;
- whitespace/rhythm;
- KPI treatment;
- colour discipline;
- surface/container quality;
- chart presentation;
- section coherence;
- visual consistency;
- premium/brand feel;
- demo readiness;
- company-wide presentation readiness.

Also score visual-quality parity against each of the three premium references on a 0–100 basis.

### 11. Prototype selection gate

Select the strongest composite direction based on evidence, not intuition.

Selection requires:

- highest median/combined visual score;
- strongest premium/brand feel;
- best executive/demo readiness;
- no interaction/runtime regression;
- genericity across visual families;
- reasonable implementation complexity.

Do not select purely because it is easiest to code.

### 12. Mature the winning composite language

After choosing the strongest direction, iterate it materially using the headless loop until it converges or a hard Power BI limitation is demonstrated.

Focus especially on:

- bespoke KPI feel;
- hero chart integration;
- title/subtitle typography;
- whitespace and module spacing;
- surface hierarchy;
- accent discipline;
- removal of native tile residue;
- cohesive page rhythm.

### 13. Executive acceptance gates — unchanged and strict

The final Executive Overview must meet:

- median overall visual-design score ≥ **7.5/10** over 3 runs;
- executive credibility ≥ **8.0**;
- demo readiness ≥ **8.0**;
- company-wide presentation readiness ≥ **8.0**;
- premium/brand feel ≥ **7.5**;
- composition/hierarchy ≥ **7.5**;
- typography ≥ **7.0**;
- whitespace/rhythm ≥ **7.0**;
- KPI treatment ≥ **7.5**;
- colour discipline ≥ **7.0**;
- surface/container quality ≥ **7.0**;
- no core visual dimension median below **7.0**.

These thresholds are intentionally hard because the target is the same quality class as the three premium example images.

### 14. Binary reaction gates

Across the 3 final runs require YES in at least 2/3 for each:

1. Would you present this exact visual design to the executive committee of a large enterprise?
2. Would it look highly professional on a large screen in a company-wide town hall/leadership presentation?
3. Does it feel materially closer to a bespoke executive dashboard than to a well-formatted default Power BI report?
4. Does it look like it belongs in the same visual-quality class as the three premium reference examples, allowing for native Power BI constraints?

### 15. Reference parity gate

Against the best/most feasible of the three premium references, require median relative visual-quality parity ≥ **80/100**.

This is stricter than 07b because the entire purpose of 07c is to test whether composite components can close the structural visual gap.

Do not lower the threshold because native Power BI is difficult.

### 16. Native Power BI limitation standard

If the gates are not met, Stage 07c may conclude “blocked by native Power BI” only if the report demonstrates the limitation **after** composite-component experimentation.

For each remaining gap provide:

- the visual effect shown in the reference;
- the composite/native approach attempted;
- actual rendered evidence;
- exact Power BI limitation encountered;
- whether interaction or rendering safety prevents further approximation;
- closest achievable treatment;
- estimated remaining visual gap.

A generic statement like “Power BI has fixed internals” is not enough.

### 17. Cross-page rollout if successful

If Executive meets the target, apply the winning composite system to:

- Regional Analysis;
- Category Analysis;
- Risk Analysis.

Secondary page visual-only target: ≥ **7.0/10** each.

They must clearly belong to the same premium product language.

### 18. Cross-domain proof

Render actual visual evidence for:

- finance executive fixture;
- SaaS/operations executive fixture.

Use the same composite component system.

Each should score ≥ **7.0/10** visual-only or document a renderer-only limitation.

No retail-specific logic.

### 19. Runtime/functionality gates

Preserve throughout:

- report loads without spinner;
- all four retail pages;
- all 29 source visuals represented;
- slicers functional;
- all 11 measures;
- refresh success;
- valid bindings;
- no broken visual icons;
- no interaction blocked by decorative overlays;
- no clipping;
- deterministic output.

### 20. No fixture hacks

Implementation may not branch on:

- retail page names;
- retail metric names;
- field names;
- Stage 02a IDs;
- displayed values;
- UK labels;
- hard-coded coordinates tuned only to the retail screenshot.

Composite behaviour must derive from generic page archetype, visual family, priority, count/density and design-language tokens.

## Evidence package

Commit under `docs/stages/07c-composite-visual-components/`:

- screenshots for all 3 composite prototypes;
- prototype assessment JSON;
- winning-prototype rationale;
- iteration screenshots/contact sheet;
- final Executive screenshot;
- final 3-run assessment JSON;
- reference-parity scores;
- interaction/runtime verification notes;
- final secondary-page screenshots if Executive passes;
- finance/SaaS screenshots if Executive passes;
- `COMPOSITE_COMPONENT_MANIFEST.json` describing component structure and stripped-native settings;
- documented native limitations if blocked.

## Tests

Add coverage for at least:

1. composite component geometry;
2. deterministic internal layout;
3. z-order correctness;
4. data visual remains interactable where required;
5. stripped card config;
6. stripped chart config;
7. composite KPI shell;
8. composite chart shell;
9. composite filter shell;
10. no overlaps/out-of-bounds internal parts;
11. genericity/no retail-specific branches;
12. finance fixture;
13. SaaS fixture;
14. all retail source visuals preserved;
15. full existing suite remains green.

## Completion definition

Stage 07c is complete only if one of these is true:

### Success

The composite-component architecture produces a native Power BI Executive Overview that meets the strict visual gates and sits in the same visual-quality class as the three premium reference examples.

### Evidence-based blocked outcome

After genuine composite experimentation, concrete screenshots and interaction tests demonstrate that remaining visual gaps are caused by specific native Power BI rendering/interaction constraints that cannot reasonably be closed by renderer-owned composition.

Do not claim success because the architecture is elegant. Do not claim blocked because stock visuals look limited. The evidence must come from the composite approach itself.

## REPORT.md requirements

Include:

- hypothesis tested;
- composite component architecture;
- stripped-native configurations by visual family;
- 3 prototype designs and screenshots;
- prototype scores and selection rationale;
- winning-direction iterations;
- final Executive 3-run scores/medians/ranges;
- all binary judgments;
- reference-parity scores against all three premium references;
- interaction/z-order findings;
- runtime/semantic regression checks;
- secondary pages and cross-domain proof if successful;
- concrete native Power BI limitations if blocked;
- automated test results;
- explicit answer:

> **Does the composite-component approach allow our native Power BI dashboards to meet the visual standard of the three premium reference examples?**

Do not answer yes unless the hard gates are met.
