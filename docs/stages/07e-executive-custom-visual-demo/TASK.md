---
stage: 07e
status: ready
title: Executive custom visual demo — Mockup 1 parity
---

# Stage 07e — Executive Custom Visual Demo: Mockup 1 Parity

## Context

Stage 07d-b proved a viable zero-touch private custom visual delivery path in PBIP/PBIR:

```text
CustomVisuals/{GUID}/package.json
CustomVisuals/{GUID}/resources/{GUID}.pbiviz.json
report.json -> resourcePackages[type=CustomVisual]
```

Fresh reports deployed through Fabric REST render private custom visuals immediately with data and no viewer consent step.

This removes the principal platform blocker. The next objective is no longer infrastructure discovery. It is to prove that the generator can produce an **Executive Overview** that reaches the visual standard originally targeted by the project.

## Approved visual reference

The approved reference is **Mockup 1** from the preceding ChatGPT design review. Treat it as the gold-standard visual contract for this stage.

Its defining characteristics are:

- dark navy executive canvas;
- premium, restrained, modern enterprise aesthetic;
- left navigation rail with clear active state;
- strong page identity/header region;
- compact top-row filters;
- five coherent KPI cards with subtle sparklines;
- one dominant revenue-over-time hero chart;
- secondary regional donut and business-unit bar chart;
- lower-row product/customer/geographic detail panels;
- generous but disciplined spacing;
- sophisticated typography hierarchy;
- subtle card borders/surfaces rather than heavy boxes;
- disciplined blue/teal/purple/gold/orange accent palette;
- excellent density: data-rich without feeling crowded;
- the overall impression of a bespoke executive software product rather than a default Power BI report.

Do not reproduce the mockup's fictitious values or labels. Preserve the real frozen Stage 02a analytical content and data. Emulate the **design quality, composition, proportions, hierarchy and component treatment**.

## Product target

The target reaction is:

> “Wow — this looks like a premium executive dashboard product. We could demo this to the C-suite or show it company-wide.”

The following reactions are NOT sufficient:

- “Looks good for Power BI”;
- “Professional and functional”;
- “Much better than before”;
- “Clean and readable”.

The stage succeeds only when the actual rendered Power BI page is materially comparable in design standard to Mockup 1.

## Scope

Focus only on the **Executive Overview demo page**.

Do not spend this stage upgrading every secondary page or building an exhaustive custom visual library.

Build the minimum coherent premium custom visual system needed to make this one page convincing.

## Frozen analytical scope

Do not use this stage to redesign analytical intent. Preserve the current Stage 02a metrics, dimensions and valid visual purposes as closely as practical.

Do not improve score by changing business questions or inventing unsupported metrics.

Renderer-owned presentation and custom visual implementation are fully in scope.

## Required custom visual components

At minimum implement and use real private-embedded Power BI custom visuals for:

### 1. Premium KPI

Upgrade the existing KPI prototype into a reusable production-quality component supporting:

- measure label;
- prominent formatted value;
- optional comparison/delta only where bound data supports it;
- optional compact sparkline where bound time-series data supports it;
- semantic positive/negative treatment;
- precise typography;
- deliberate internal spacing;
- subtle accent identity;
- responsive sizing;
- polished hover state where appropriate.

A KPI row should read as one coherent designed system, not five unrelated cards.

### 2. Premium Time-Series / Line-Area Chart

Build a hero-quality custom chart with full rendering control over:

- plot padding;
- typography;
- x/y axes;
- gridlines;
- line stroke;
- optional area fill;
- comparison series where data supports it;
- legend;
- tooltip;
- hover/focus state;
- selection/cross-filter identity;
- title/subtitle integration if useful;
- responsive layout.

The hero chart should be the visual focal point of the page.

### 3. Premium Horizontal Bar Chart

Build a polished ranked/category comparison visual with:

- clean horizontal bars;
- concise category labels;
- direct value labels where useful;
- disciplined accent colouring;
- optional comparison context where supported;
- selection/cross-filter behaviour;
- tooltips;
- responsive sizing.

### 4. Premium Donut / Breakdown

Implement a restrained executive breakdown visual with:

- clean donut geometry;
- limited, curated categorical colours;
- center total where appropriate;
- compact legend/value treatment;
- hover and selection behaviour;
- responsive spacing.

### 5. Premium Detail/Table Component

Implement either a custom table/detail visual or a sufficiently styled existing path that can convincingly match the lower-row detail treatment in Mockup 1.

Requirements include:

- strong header hierarchy;
- restrained row separators;
- professional numeric alignment;
- concise density;
- semantic highlights only where meaningful;
- no spreadsheet-like default appearance.

If a native table remains, it must not visually break the premium composition.

## Page composition target

Build the Executive Overview around a deliberate composition inspired by Mockup 1:

```text
LEFT NAVIGATION RAIL

MAIN CANVAS
  page title / subtitle         compact filters
  ------------------------------------------------
  KPI  KPI  KPI  KPI  KPI
  ------------------------------------------------
  HERO TIME SERIES | DONUT | BAR
  ------------------------------------------------
  DETAIL / PRODUCTS | CUSTOMER / SUMMARY | GEO / DETAIL
```

Exact content placement may vary to fit the real spec, but visual hierarchy should remain equivalent:

1. identity/context;
2. KPI summary;
3. dominant hero analysis;
4. supporting comparisons;
5. lower-detail context.

Avoid equal-sized grid tiles and wall-of-rectangles layouts.

## Navigation rail

Create a premium left-side navigation rail treatment inspired by Mockup 1.

It may be implemented through native shapes/text/navigation buttons or other safe primitives if a custom visual is unnecessary.

Requirements:

- dark integrated surface;
- clear active page state;
- consistent icon/text alignment where icons are feasible;
- restrained secondary navigation;
- does not dominate data content;
- feels like product navigation, not a random stack of buttons.

Do not add fake functionality that does not work.

## Header and filters

The page header should include:

- strong Executive Overview title;
- restrained subtitle/context;
- compact, aligned visible filters/slicers;
- optional refresh/context text only if genuine data exists.

Filters should visually integrate into the design language and remain fully functional.

## Design tokens

Create or extend a premium dark design language inspired by Mockup 1.

Use generic semantic tokens rather than hard-coded fixture styling:

- canvas/background;
- navigation surface;
- card/surface background;
- elevated/hero surface;
- border/divider;
- primary text;
- secondary text;
- muted text;
- primary accent;
- secondary accents;
- positive;
- negative;
- warning;
- spacing scale;
- type scale;
- radius scale;
- shadow/depth policy.

Suggested visual direction:

- deep navy canvas;
- slightly lighter navy surfaces;
- bright but controlled electric blue as primary accent;
- teal, purple, gold and orange as limited secondary accents;
- white/off-white primary text;
- desaturated blue-grey secondary text;
- subtle 1px borders;
- modest corner radius;
- very restrained glow/shadow only if it genuinely survives Power BI rendering cleanly.

Do not create a neon gaming dashboard.

## Typography

Typography is a major acceptance dimension.

The page must show deliberate hierarchy between:

- page title;
- page subtitle/context;
- KPI label;
- KPI value;
- KPI comparison/delta;
- section/visual title;
- axis labels;
- legend;
- data labels;
- table headers/body;
- navigation labels;
- filter labels/values.

Use responsive sizing where helpful, but prevent clipping at the target 16:9 page size.

## Interaction requirements

This remains a real Power BI report.

Custom visuals should support, where relevant:

- slicer/filter response;
- selection identities;
- cross-filter or cross-highlight behaviour;
- tooltips;
- responsive resize;
- correct empty/null states;
- deterministic rendering.

At minimum prove that the hero chart and one supporting chart participate correctly in Power BI selection/filter interactions.

Do not sacrifice functionality for screenshot aesthetics.

## Private custom visual delivery

Use the **proven Stage 07d-b zero-touch private PBIP structure**.

Do not revert to `organizationCustomVisuals` or `publicCustomVisuals`.

For every custom visual used:

```text
CustomVisuals/{GUID}/package.json
CustomVisuals/{GUID}/resources/{GUID}.pbiviz.json
```

and declare the appropriate `resourcePackages` item in `report.json`.

Fresh deployment must render the custom visuals without any manual consent or edit-mode activation.

## Screenshot-driven iteration

This stage is explicitly iterative.

Use:

```text
implement
→ package custom visuals
→ generate PBIP/PBIR
→ deploy fresh report
→ headless screenshot
→ compare directly to Mockup 1
→ identify largest visual gaps
→ refine generic custom visual/page rules
→ repeat
```

Do not stop at the first functioning version.

Perform at least **three materially meaningful visual iterations** after the first integrated build unless the hard acceptance gates are already exceeded earlier.

Commit representative iteration screenshots or a contact sheet.

## Critic evaluation

Use the strongest practical multimodal critic available.

The rubric must compare the actual deployed Executive Overview against Mockup 1 for **design quality**, not data/content identity.

Explicitly ignore analytical differences that are frozen by the real dashboard spec.

Score 0–10 on:

- first-impression professionalism;
- executive credibility;
- composition/hierarchy;
- typography;
- whitespace/rhythm;
- KPI treatment;
- hero-chart quality;
- supporting-chart quality;
- colour discipline;
- surface/container quality;
- navigation/header integration;
- consistency/cohesion;
- premium/brand feel;
- demo readiness;
- company-wide presentation readiness.

Also score 0–100:

> Relative visual-quality parity with Mockup 1, where 100 means equal overall design standard rather than pixel-perfect identity.

## Final assessment methodology

For the final screenshot:

- run the same critic rubric **3 times**;
- use the same model/configuration where practical;
- report every run;
- calculate median and range;
- do not cherry-pick.

Also ask on each run:

1. “Judging visual presentation only, would you be comfortable presenting this exact dashboard design to the executive committee of a large enterprise?”
2. “Would this look highly professional full-screen in a company-wide leadership presentation or town hall?”
3. “Does this feel materially closer to a bespoke premium executive dashboard product than to a well-formatted Power BI report?”

## Hard acceptance gates

Stage 07e is complete only if the final actual Power BI Executive Overview meets **all** of the following:

- median overall visual score ≥ **7.5/10**;
- executive credibility ≥ **8.0/10**;
- demo readiness ≥ **8.0/10**;
- company-wide presentation readiness ≥ **8.0/10**;
- premium/brand feel ≥ **7.5/10**;
- composition/hierarchy ≥ **7.5/10**;
- typography ≥ **7.5/10**;
- whitespace/rhythm ≥ **7.0/10**;
- KPI treatment ≥ **8.0/10**;
- hero-chart quality ≥ **7.5/10**;
- supporting-chart quality ≥ **7.0/10**;
- colour discipline ≥ **7.5/10**;
- surface/container quality ≥ **7.5/10**;
- navigation/header integration ≥ **7.0/10**;
- no core dimension median below **7.0/10**;
- Mockup 1 relative visual-quality parity ≥ **80/100 median**;
- at least **2/3 YES** for executive committee presentation;
- at least **2/3 YES** for company-wide presentation;
- at least **2/3 YES** for bespoke-premium-vs-formatted-Power-BI.

Do not average away a visibly weak component.

## Fresh deployment gate

The final evidence must come from a **freshly created report** using the private custom visual embedding path.

Requirements:

- no report has been previously opened/primed;
- no edit-mode interaction;
- no viewer consent prompt;
- all custom visuals receive data immediately;
- screenshot captured headlessly;
- report loads without spinner or broken visual states.

## Human visual inspection gate

REPORT.md must explicitly answer:

- Is the focal hierarchy obvious within one second?
- Do the KPI cards feel like bespoke UI components?
- Is the hero chart clearly dominant and premium?
- Do secondary visuals feel subordinate but coherent?
- Does the navigation rail feel integrated and intentional?
- Is typography authoritative and consistent?
- Is whitespace deliberate?
- Are colours restrained and sophisticated?
- Are surfaces subtle rather than boxy?
- Is there any obvious default-Power-BI residue that custom rendering could still remove?
- Would this page look credible on a large screen in an executive meeting?
- What remains visibly behind Mockup 1?

If the answer to any of the first nine is “no”, continue iterating unless a concrete host limitation is demonstrated.

## Genericity requirement

Although this is one demo page, do not implement retail-specific styling branches.

Custom visuals and composition behaviour must derive from generic inputs such as:

- visual family;
- visual priority;
- semantic colour roles;
- page archetype;
- measure/field metadata;
- data role;
- visual count/density;
- design-language tokens.

No branches on specific metric names, retail fields, displayed values or Stage 02a IDs.

## Tests

Add automated coverage for at least:

1. all custom visual packages build reproducibly;
2. private PBIP embedding structure for each visual;
3. resourcePackages declaration;
4. KPI data mapping/formatting;
5. KPI optional sparkline/delta states;
6. line/area chart data transformation;
7. bar chart data transformation;
8. donut data transformation;
9. selection identities where implemented;
10. null/empty states;
11. resize behaviour where practical;
12. design-token application;
13. no retail-specific constants;
14. deterministic generated PBIP;
15. existing Python suite remains green;
16. fresh headless smoke test remains separate from unit tests.

## Evidence package

Commit under `docs/stages/07e-executive-custom-visual-demo/`:

- reference description / design contract;
- first integrated screenshot;
- iteration screenshots or contact sheet;
- final Executive Overview screenshot;
- custom visual inventory and GUIDs;
- interaction test evidence;
- `EXECUTIVE_MOCKUP1_ASSESSMENT.json` with all 3 critic runs, medians and ranges;
- Mockup 1 relative-parity scoring;
- runtime/fresh-deployment evidence;
- `REPORT.md`.

## REPORT.md requirements

Include:

- implementation summary;
- custom visual architecture;
- which components are custom vs native primitives;
- private PBIP embedding implementation;
- design token system;
- page composition decisions;
- KPI implementation;
- hero chart implementation;
- supporting visual implementation;
- navigation/header/filter treatment;
- interaction behaviour;
- screenshot iteration history;
- final screenshot;
- all three critic runs;
- medians/ranges for every required dimension;
- Mockup 1 parity score;
- binary executive/company-wide/bespoke judgments;
- fresh-deployment zero-touch result;
- automated test results;
- remaining visual gaps;
- any genuine Power BI host limitations;
- explicit answer to:

> **Does the actual generated Executive Overview now meet approximately the same visual standard as Mockup 1 and feel suitable for an executive or company-wide demo?**

Do not answer yes unless the hard gates are met.
