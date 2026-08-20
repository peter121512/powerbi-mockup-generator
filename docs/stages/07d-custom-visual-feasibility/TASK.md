---
stage: 07d
status: ready
title: Custom visual feasibility spike for premium executive design
---

# Stage 07d — Custom Visual Feasibility Spike

## Context

Stages 07–07c established a strong functional Power BI generation pipeline and materially improved generic formatting, layout, filters and design-system architecture. However, native built-in visuals and composite assemblies of shapes/text/native visuals have not approached the required visual standard. Stage 07c's composite experiment scored approximately 2.1/10 and only ~22/100 relative to the premium reference standard.

Do **not** interpret this as proof that Power BI itself cannot reach the target. It demonstrates that the current built-in-native-visual approach has reached a practical ceiling.

Stage 07d is a narrow feasibility spike to answer one question:

> Can a small library of Power BI custom visuals provide the rendering control required to make generated dashboards genuinely comparable in visual quality to the premium executive dashboard references that define this project's target?

This is not an incremental styling pass and not yet a full custom-visual rewrite.

## Product target — non-negotiable

The target remains the same standard as the three premium executive dashboard examples/reference directions established during Stage 07b:

- premium executive / boardroom quality;
- sophisticated modern enterprise dashboard design;
- corporate-editorial level typography and composition;
- visually impressive enough to demo to senior executives;
- visually impressive enough to show company-wide;
- clearly closer to bespoke premium product design than to default Power BI.

“Good for Power BI”, “professional”, “clean”, or “better than the native version” are **not sufficient acceptance standards**.

The spike must determine whether custom visuals can plausibly close the gap to that reference level.

## Read first

1. Read `KIRO.md`.
2. Read Stage 05c, 06, 07, 07a, 07b and 07c TASK/REPORT files.
3. Inspect the premium reference images/evidence produced during 07b/07c, if present.
4. Inspect the best native Executive Overview screenshot and the Stage 07c composite screenshot.
5. Inspect the current PBIR renderer, deployment pipeline, headless embed-token capture path and design-system implementation.
6. Review current Microsoft Power BI custom visual architecture/tooling and repository implications before implementing.
7. Preserve the existing functional pipeline and frozen Stage 02a analytical intent.

## Scope freeze

Do not use this stage to fix:

- month sorting;
- mixed-scale axes;
- chart-type selection;
- DAX semantics;
- semantic-model analytical design;
- Stage 02a analytical content;
- conversational revision;
- generic critic-driven spec mutation.

Those remain outside the experiment. This stage tests **rendering freedom and visual quality**.

## Required spike

Build only enough custom-visual capability to test the hypothesis convincingly.

At minimum implement and integrate:

1. one **Premium KPI** custom visual/component;
2. one **Premium Chart** custom visual/component suitable for a major Executive Overview analytical visual.

If technically necessary, a small shared custom-visual package/library architecture may support both. Do not build a complete visual suite before feasibility is demonstrated.

## 1. Establish custom visual toolchain

Set up the minimum reproducible development/build path for Power BI custom visuals.

Document:

- toolchain/runtime versions;
- package structure;
- build command;
- resulting `.pbiviz` artifact(s);
- capabilities/data roles;
- formatting model;
- how visuals are installed/registered/deployed for the test report;
- whether tenant/admin settings affect deployment or rendering;
- any certification/security implications relevant to future productization.

Keep generated/build artifacts out of source control where appropriate, but commit all source and reproducible configuration.

## 2. Premium KPI prototype

Build a KPI visual that owns its internal rendering surface rather than accepting the stock Power BI Card layout.

It should support, where data permits:

- primary metric value;
- concise metric label;
- professional numeric formatting;
- optional secondary context only when bound/provided;
- renderer/design-language-controlled typography;
- precise internal spacing;
- background/surface treatment;
- subtle border/radius/depth;
- accent treatment;
- semantic positive/negative styling when genuinely supported by bound data;
- responsive behaviour across expected KPI dimensions.

Do not fabricate trend arrows, deltas, icons or context not provided by the data/spec.

The design should deliberately aim at the KPI quality visible in the premium references.

## 3. Premium Chart prototype

Build one high-value analytical custom visual appropriate to the Executive Overview. Prefer a chart family already required by the frozen dashboard so the comparison is meaningful.

The custom chart should demonstrate rendering control over the dimensions that stock visuals have constrained:

- typography;
- plot margins/padding;
- axis rendering;
- gridline treatment;
- legend placement;
- series styling;
- data labels/tooltips where appropriate;
- visual title/context integration if owned by the component;
- sophisticated whitespace;
- surface/container integration;
- hover/selection states;
- Power BI cross-filter/selection behaviour where feasible.

Do not create a visually attractive static SVG that fails to behave as a BI visual. Functional interaction is part of feasibility.

## 4. Design from the premium references

Before coding final styling, explicitly extract the relevant KPI and chart visual language from the same three premium reference directions used as the project target.

The custom prototypes should intentionally reproduce their **level of refinement**:

- confident type hierarchy;
- deliberate spacing;
- restrained palette;
- polished surfaces;
- coherent chart chrome;
- executive density;
- premium micro-layout.

Do not optimize against ordinary Power BI screenshots.

## 5. Integrate into the real Executive Overview

Create a test variant of the frozen Stage 02a Executive Overview in which:

- at least the KPI area uses the custom KPI visual for enough metrics to judge the system, preferably the full KPI band if feasible;
- at least one major/hero analytical visual uses the custom chart;
- the remaining report can use the strongest existing native baseline;
- analytical bindings remain equivalent;
- the page still runs as a real Power BI report in Fabric.

Do not fake the screenshot outside Power BI.

## 6. Deployment feasibility

Prove the custom visual(s) can be included in the generated/deployed report path used by this project.

Investigate and document:

- PBIP/PBIR representation of the custom visual;
- how the visual package/resource is referenced;
- whether REST deployment preserves it;
- tenant settings/admin dependencies;
- whether headless embedded rendering loads it consistently;
- whether report consumers require separate installation or organizational visual registration;
- implications for generated reports across tenants.

A beautiful prototype that cannot participate in the automated deployment architecture does not prove product feasibility.

## 7. Functional interaction test

For the custom chart and KPI where applicable, verify:

- correct bound values;
- filter response;
- slicer response;
- selection/cross-filter behaviour where relevant;
- tooltip behaviour if implemented;
- resizing/layout stability;
- no broken state during headless load;
- deterministic rendering.

Record which interactions are supported and which would require further engineering.

## 8. Headless screenshot evidence

Use the existing embed-token + headless Chromium pipeline to capture the real deployed Fabric Executive Overview containing the custom visuals.

Capture at least:

- best native baseline for comparison;
- Stage 07c composite result if useful;
- initial custom-visual integration;
- final custom-visual spike result.

Commit a compact comparison/contact sheet if practical.

## 9. Visual-only assessment

Use a critic rubric that explicitly ignores frozen analytical defects such as month sorting, mixed-scale axes and visual-type preference.

Assess only visual presentation, with dimensions including:

- first-impression professionalism;
- executive credibility;
- composition/hierarchy;
- typography;
- whitespace/rhythm;
- KPI treatment;
- colour discipline;
- surface/container quality;
- chart presentation;
- visual consistency;
- premium/brand feel;
- demo readiness;
- company-wide presentation readiness.

The principal comparison is against the **same premium reference standard**, not against the prior Power BI output.

## 10. Three-run final assessment

For the final custom-visual screenshot:

- run the same visual-only assessment at least 3 times;
- same model/configuration where practical;
- record every run;
- report median and range;
- no cherry-picking.

Ask on each run:

> Ignoring analytical-choice defects and judging visual presentation only, would you be comfortable presenting this exact dashboard design to the executive committee of a large enterprise?

> If shown full-screen at a company-wide town hall or leadership presentation, would its visual quality make the product/team look highly professional?

> Does this visually feel materially closer to a premium bespoke executive dashboard than to a well-formatted default Power BI report?

## 11. Reference-relative scoring

Compare the final custom-visual result against the same feasible premium references on a 0–100 design-quality scale, where 100 means equal overall design quality, not pixel identity.

Exclude clearly impossible/non-BI fantasy elements from the comparison.

Report:

- score against each reference;
- median/best-feasible reference score;
- specific remaining visual gaps;
- which gaps are now demonstrably solvable with custom rendering versus still constrained by the Power BI host/report canvas.

## Feasibility decision gates

This stage has three possible conclusions.

### A. Strong positive — proceed to custom visual library

Recommend building a reusable custom visual system only if the spike demonstrates a **step-change**, not an incremental improvement.

Strong-positive evidence should include:

- median overall visual score **≥7.0/10**, with a credible path to ≥7.5;
- KPI treatment **≥7.5/10**;
- chart presentation **≥7.0/10**;
- premium/brand feel **≥7.0/10**;
- executive credibility **≥7.5/10**;
- demo readiness **≥7.5/10**;
- at least 2/3 YES for executive presentation;
- at least 2/3 YES for bespoke-vs-default-Power-BI;
- reference-relative quality **≥70/100** against the best feasible reference;
- clear evidence that remaining gaps are addressable by expanding the custom visual library;
- deployment and interaction architecture is viable.

### B. Promising but incomplete — one bounded follow-up justified

Use this only if:

- custom visuals materially outperform native/composite approaches;
- visual score is approximately **5.5–6.9**;
- reference parity is approximately **55–69/100**;
- the report identifies a small number of concrete engineering gaps that plausibly explain the remaining difference;
- automated deployment remains viable.

The REPORT must propose one tightly bounded follow-up experiment, not a broad rewrite.

### C. Negative — reconsider Power BI-native delivery constraint

Recommend against investing in a custom visual library if:

- custom rendering still produces <5.5/10 visual quality;
- reference parity remains <55/100;
- executive/bespoke binary judgments remain predominantly NO;
- or deployment/tenant/security constraints make generated custom visuals operationally unsuitable.

A negative result is valuable if supported by evidence. Do not keep iterating merely because custom visuals are theoretically flexible.

## Ultimate product standard remains higher

The thresholds above determine whether custom visuals are a viable **route**, not whether the final product is done.

If the spike is positive, the subsequent custom-visual-library stage must still target the original premium dashboard bar:

- overall ≥7.5/10;
- executive/demo/company-wide readiness ≥8.0;
- no core visual dimension below 7.0;
- reference-relative quality ≥80/100;
- actual rendered dashboard comparable in standard to the three premium examples.

Do not lower the final product goal because the spike threshold is lower.

## Security and productization considerations

Because custom visuals introduce executable code into reports, document at minimum:

- whether visuals need certification;
- tenant policy dependencies;
- organizational visual deployment options;
- external service/network access, if any;
- sandbox restrictions;
- CSP/API limitations;
- accessibility requirements;
- future maintenance/versioning implications.

Do not add unnecessary external network dependencies to the prototypes.

## Genericity

The KPI and chart prototypes must be reusable components driven by data roles and design-system tokens.

No branching on retail-specific:

- metric names;
- field names;
- page names;
- values;
- IDs;
- UK labels;
- coordinates.

The goal is evidence for a future reusable visual library.

## Tests

Add appropriate automated tests for:

1. custom visual build succeeds reproducibly;
2. capabilities/data-role definitions;
3. formatting/design token mapping;
4. KPI data transformation/formatting;
5. chart data transformation;
6. selection/filter identity handling where implemented;
7. safe empty/null data states;
8. resize behaviour where testable;
9. no retail-specific constants;
10. renderer/PBIR integration references the correct custom visual identity;
11. existing Python suite remains green;
12. deployment artifacts are deterministic where practical.

Keep live Fabric/browser tests separate from routine unit tests.

## Evidence package

Commit under `docs/stages/07d-custom-visual-feasibility/`:

- custom KPI source/build notes;
- custom chart source/build notes;
- deployment/integration notes;
- native-vs-composite-vs-custom comparison screenshots/contact sheet;
- final Executive screenshot;
- `CUSTOM_VISUAL_ASSESSMENT.json` with all critic runs and medians/ranges;
- reference-relative comparison;
- interaction test evidence;
- tenant/deployment feasibility notes;
- `REPORT.md`.

Custom visual source code should live in an appropriate source directory, not under docs.

## REPORT.md requirements

The report must include:

- exact hypothesis tested;
- custom visual architecture/toolchain;
- KPI prototype implementation;
- chart prototype implementation;
- PBIR/deployment integration method;
- live Fabric rendering result;
- functional interaction results;
- screenshots/comparison evidence;
- all three critic runs;
- median/range by visual dimension;
- binary executive/company-wide/bespoke judgments;
- reference-relative scores against the same premium standards;
- comparison with best native and Stage 07c composite approaches;
- operational/security/tenant constraints;
- automated test results;
- remaining gaps;
- one explicit conclusion: `STRONG_POSITIVE`, `PROMISING_BOUNDED_FOLLOWUP`, or `NEGATIVE`;
- explicit recommendation on whether to invest in a reusable Power BI custom visual library.

Do not claim success because a `.pbiviz` builds. The experiment succeeds only if it produces convincing evidence about whether this architecture can reach the premium visual standard.
