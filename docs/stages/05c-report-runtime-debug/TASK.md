---
stage: 05c
status: ready
title: Report runtime debugging and spinner isolation
---

# Stage 05c — Report Runtime Debugging

## Context

Stage 05b proved that:

- the semantic model is deployed;
- all six tables are populated;
- refresh succeeds;
- all 11 measures evaluate without errors;
- the report item exists with all four pages.

However, the user has now manually opened the generated report in Fabric and observed an **endless loading spinner**. That means platform acceptance and semantic queryability are not sufficient: the PBIR report still has a runtime/rendering defect.

This stage exists to isolate and fix that defect.

## Hard acceptance criterion

Stage 05c is complete only when the **live deployed report opens normally in the user's browser and the Executive Overview finishes rendering without an endless spinner**.

A deployment API success, page enumeration success, or semantic-model query success is not enough.

## Read first

1. Read `KIRO.md`.
2. Read Stage 04, 05, 05a and 05b TASK/REPORT files.
3. Inspect the current live PBIR output, especially Executive Overview visual JSON and page/report JSON.
4. Inspect Stage 04 visual/query-state builders, slicer generation, interaction metadata and page layout logic.
5. Inspect available Power BI/Fabric APIs for report metadata, page metadata, visual metadata and runtime/query errors.
6. Reuse the existing deployed report/model where practical; do not proliferate unrelated duplicates.
7. Do not claim success until the browser runtime is actually observed working.

## Symptom

Manual user observation:

> Opening the live Fabric report results in an endless loading state.

Treat this as the primary source-of-truth runtime symptom.

## Objective

Systematically determine which report/PBIR construct causes the Fabric report shell to hang, fix it generically in the renderer, redeploy, and prove the live report loads.

## Required debugging strategy

### 1. Determine scope of the hang

Use any available metadata/API/browser evidence to determine whether:

- only the default/Executive Overview page hangs;
- all four pages hang;
- the report shell itself fails before page rendering;
- specific visuals or generated slicers cause the hang.

If direct browser automation remains unavailable, use deployment variants and user-verifiable outcomes.

### 2. Establish a minimal known-good report baseline

Create a diagnostic render/deployment variant against the **same semantic model** with:

- one page;
- no data visuals initially, or only a minimal textbox/card known to be safe;
- no slicers;
- no drill-through/navigation/interactions beyond essentials;
- no optional theme/formatting complexity unless required.

Deploy it to a clearly named diagnostic report or update the existing development report only if that does not destroy useful debugging state.

The purpose is to answer: **Can a generated PBIR report shell from this renderer load at all?**

If even the blank/minimal report spins, focus on report/page/PBIR root structure rather than individual visuals.

### 3. Bisect visual/runtime complexity

If a minimal report loads, add constructs back incrementally or in batches until the spinner reappears.

Prioritize isolation in approximately this order:

1. KPI cards
2. line/bar/column charts
3. tables
4. slicers
5. donut/scatter
6. map
7. drill-through/navigation metadata
8. theme/formatting extras
9. interaction metadata

A binary/batched bisection is preferred over one-by-one random edits.

Record exactly which variant loads/hangs.

### 4. Suspect generated slicers/layout early

Stage 04 currently creates slicers from `FilterSpec` and appends them below the main content area rather than integrating them into the declared page grid.

Check whether generated slicer visuals:

- are positioned off-canvas;
- have invalid query states;
- reference roles/projections incorrectly;
- cause page initialization to hang.

If slicers are implicated, fix the renderer generically rather than deleting filtering from the product.

### 5. Inspect visual query-state validity

The highest-probability defect domain is PBIR query/visual configuration that Fabric accepted structurally but cannot execute/render.

For each visual type used by the live fixture, verify against known-good Power BI PBIR structures:

- `visualType` value;
- `query.queryState` roles;
- projections/select structure;
- field/measure references;
- aggregations;
- sort metadata;
- measure/column property naming;
- map/scatter-specific role requirements;
- table/card role requirements.

Prefer comparison against a real exported PBIR sample from Power BI or official Microsoft schemas/examples where available.

### 6. Query runtime errors through APIs where possible

Investigate available Power BI/Fabric endpoints or diagnostic metadata that may reveal:

- visual query errors;
- invalid binding/projection messages;
- page load errors;
- semantic query failures triggered by visuals;
- correlation/request IDs.

Capture non-sensitive diagnostic evidence in the report.

### 7. Validate individual visual queries semantically

For visuals on Executive Overview, execute representative equivalent DAX/query checks against the deployed semantic model to prove the underlying data requests are valid.

At minimum validate:

- TotalRevenue card
- GrossMarginPct card
- YoYGrowthPct card
- RiskCount card
- revenue trend grouping by Date/Month
- regional comparison
- category comparison

If semantic queries work but the visual still hangs, the issue is PBIR binding/config rather than model/data.

### 8. Treat complex visuals as suspects, not scapegoats

Map and scatter visuals are plausible runtime-risk areas because their role requirements are more specific.

If one of these is the culprit:

- confirm it through isolation;
- fix the visual mapper if possible;
- otherwise implement an explicit temporary analytical fallback with fidelity diagnostics;
- do not silently delete the visual.

### 9. Inspect page/report metadata

If the hang occurs even with a blank page, inspect:

- report schema/version;
- `definition.pbir` dataset reference;
- `report.json` resource packages;
- theme registration;
- page ordering/active page metadata;
- page dimensions/display options;
- visual container IDs;
- duplicate/stale IDs;
- unsupported properties surviving from newer PBIR schema versions.

### 10. Add runtime-safe renderer validation

Once the cause is known, add deterministic regression validation where possible so the same invalid construct cannot be emitted again.

Examples:

- unsupported query-state role combinations;
- missing required visual role bindings;
- off-canvas generated slicers;
- invalid projection structure;
- duplicate visual/container IDs;
- unsupported interaction properties.

### 11. Preserve fidelity accounting

Any debugging fallback must be recorded in the fidelity manifest.

For each source visual, maintain one of:

- exact render;
- explicit fallback;
- unsupported/failed diagnostic.

Do not make the report load by silently dropping source visuals.

### 12. Redeploy and verify iteratively

After each meaningful fix:

- regenerate PBIP;
- deploy/update diagnostic/live report;
- preserve the populated semantic model where possible;
- verify report existence/pages;
- ask for/obtain actual browser-runtime outcome where automation is unavailable.

Continue until the live Executive Overview loads normally.

### 13. User-verification checkpoint

Because the decisive symptom is observed in the user's authenticated Fabric browser, the final stage result must include one of:

- automated browser evidence that the page loaded; or
- explicit user confirmation after opening the corrected live report.

If automation cannot observe the browser, do not claim full success before user confirmation.

## Acceptance criteria

### Full success

- root cause of the endless spinner isolated with evidence;
- generic renderer/runtime fix implemented;
- regression tests added;
- semantic model remains populated and measures queryable;
- corrected report redeployed;
- Executive Overview opens and finishes rendering;
- no endless spinner on the live report;
- source visuals are preserved or explicit fallbacks documented;
- full automated test suite passes;
- `REPORT.md` documents the isolation sequence, root cause and final proof.

### Honest partial/blocked outcome

If the stage cannot reach a browser-confirmed load state:

- document every diagnostic variant attempted;
- identify the narrowest remaining suspect;
- distinguish code blocker from external/browser limitation;
- do not report deployment/page enumeration as equivalent to runtime success.

## Tests

Add regression tests for the discovered defect and any renderer change, while keeping normal tests independent of live Fabric credentials.

The complete Stage 01–05b suite must remain green.

## REPORT.md requirements

Include:

- exact runtime symptom;
- whether all pages or only some were affected;
- diagnostic variants deployed and their load/hang result;
- isolated culprit construct/visual/property;
- semantic query checks for Executive Overview visuals;
- code changes made;
- fidelity impact/fallbacks if any;
- deployment result;
- automated test result;
- final browser/runtime verification method;
- explicit answer: **Does the live Executive Overview now load normally without an endless spinner?**
- recommended next stage only after runtime success.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
