---
stage: 07d-a
status: ready
title: Custom visual auto-binding forensics
---

# Stage 07d-a — Custom Visual Auto-Binding Forensics

## Context

Stage 07d established that Power BI custom visuals can materially improve presentation quality and may be the viable route to the premium executive dashboard standard required by this project. However, the automated product flow is still blocked by one critical issue:

> Fresh REST/API-deployed custom visuals do not receive bound data on first load until a user manually edits the report and “touches” the field binding (for example untick/retick or rebind).

That manual step is incompatible with the target product experience.

Do not build out the broader custom visual library until this is solved or conclusively demonstrated to be impossible within the current deployment architecture.

## Objective

Determine exactly what the Power BI editor changes when a custom visual binding is manually activated, reproduce that state programmatically, and prove this end-to-end flow:

```text
render PBIR with custom KPI + custom chart bindings
→ deploy by API
→ zero human/editor interaction
→ open report headlessly
→ custom visuals receive data on first render
→ screenshot confirms populated visuals
```

The stage is complete only when the above works reliably, or when a concrete platform limitation is demonstrated with exhaustive evidence.

## Read first

1. Read `KIRO.md`.
2. Read Stage 07d TASK/CONTINUE/REPORT files.
3. Inspect the working Premium KPI custom visual source and any Premium Chart prototype/source currently present.
4. Inspect the exact PBIR `visual.json` for:
   - a fresh API-deployed unbound/blank custom visual;
   - the same visual after manual binding activation.
5. Inspect report-level metadata, custom visual registrations and query metadata before/after activation.
6. Inspect current Fabric report-definition get/update APIs and the project’s direct REST deployment logic.
7. Preserve secrets/tokens outside committed artifacts.

## Core principle

Do not guess at binding metadata. Treat the Power BI editor as an oracle and perform controlled before/after forensics.

The primary task is to discover the minimal state delta required to turn a blank custom visual into a data-bound custom visual.

## Required work

### 1. Create a controlled diagnostic report

Use the smallest possible reproducible report containing:

- one Premium KPI custom visual bound to a known measure such as `TotalRevenue`;
- one Premium Chart custom visual bound to a known category + measure if the chart exists;
- the same semantic model used in prior live tests;
- no unnecessary decorative parts.

Name/identify this diagnostic artifact clearly so before/after exports can be compared without ambiguity.

### 2. Capture PRE-activation report definition

Immediately after API deployment, before any manual editor interaction:

- export/fetch the complete report definition from Fabric/Power BI;
- preserve all report parts relevant to the custom visuals;
- save a normalized non-secret snapshot under the stage evidence directory.

Capture at minimum:

- report.json;
- page JSON;
- target custom visual `visual.json` files;
- custom visual package/resource references;
- semantic query/queryState sections;
- projection/order/select structures;
- `dataTransforms` if present;
- any queryMetadata/prototypeQuery metadata;
- report extensions/custom visual registrations;
- relevant resource package metadata.

### 3. Perform one controlled manual activation

Using the Power BI editor, make the smallest possible action known to activate binding:

- untick/retick the bound field;
- or remove/re-add the same field;
- make no formatting/layout changes.

Record exactly which action was performed.

Do not make any unrelated report edits.

### 4. Capture POST-activation report definition

Immediately after saving the manually activated report:

- export/fetch the full report definition again;
- save a normalized non-secret snapshot;
- confirm the custom visual renders with data.

### 5. Produce a semantic before/after diff

Create a machine-readable and human-readable diff that ignores irrelevant noise such as timestamps/order-only changes while preserving meaningful metadata differences.

Classify every difference as one of:

- likely binding-critical;
- potentially binding-related;
- unrelated editor noise;
- unknown.

The diff must inspect beyond the target `visual.json`. Look for changes across the entire report definition.

Potential areas include but are not limited to:

- `query` / `queryState`;
- `prototypeQuery`;
- `projections`;
- `selects` / `Select` entries;
- `dataTransforms`;
- `queryMetadata`;
- `visualContainerObjects`/objects;
- role metadata;
- source aliases;
- field properties;
- format strings;
- custom visual configuration;
- resource references;
- report/page section metadata.

Do not stop after finding the first plausible field.

### 6. Compare with native visual binding structures

Inspect an equivalent native card/chart bound to the same fields and compare its query/binding structures against the custom visual.

Goal:

- identify whether custom visuals require an additional data-reduction/data-transform/query contract;
- identify whether the generated PBIR is missing a structure that native visuals already include.

### 7. Inspect a Desktop-authored custom visual

If available, create the same Premium KPI/custom chart in Power BI Desktop manually, bind the same fields, save/publish/export as PBIP/PBIR or retrieve the deployed report definition.

Compare:

- Desktop-authored bound custom visual;
- API-deployed blank custom visual;
- manually activated web-editor custom visual.

This three-way comparison is mandatory if technically feasible.

### 8. Reverse-engineer the minimal required metadata

From the diffs, identify the smallest programmatically generatable binding payload/state.

Implement a generic helper in the renderer such as conceptually:

```text
build_custom_visual_query_binding(...)
```

or equivalent.

It must derive from:

- custom visual data roles/capabilities;
- bound semantic fields/measures;
- current DashboardSpec visual binding;
- semantic model names/aliases.

No hard-coded retail field names or visual GUID-specific hacks beyond registered custom visual metadata.

### 9. Test candidate fixes incrementally

For each candidate metadata addition:

1. generate a fresh report artifact;
2. deploy to a fresh/new test report or reset artifact;
3. do **not** open in edit mode;
4. load directly headlessly;
5. verify whether the custom visual receives data;
6. capture screenshot/log evidence.

Do not accidentally test against a report that was previously manually activated.

Maintain a candidate matrix recording:

- candidate ID;
- metadata changed;
- deploy result;
- first-load binding result;
- headless screenshot result;
- notes.

### 10. Validate true zero-touch behaviour

A successful candidate must pass this exact test:

- delete/create or otherwise guarantee a fresh report item/state;
- deploy via automation only;
- no Power BI edit-mode interaction;
- no manual field change;
- no browser click that mutates report definition;
- open report in view/embed mode headlessly;
- wait for rendered event;
- verify KPI/chart values are present;
- capture screenshot;
- repeat at least 3 times on fresh deployments.

Acceptance requires 3/3 successful zero-touch runs.

### 11. Verify filter response after auto-binding

Once zero-touch binding works, verify at minimum:

- custom KPI updates when a slicer/filter changes;
- custom chart updates when a slicer/filter changes;
- values match equivalent semantic queries/native visual evidence;
- no stale cached values.

If custom chart selectionManager/cross-filtering is not yet implemented, document that separately; inbound filter response is mandatory.

### 12. Investigate alternative initialization paths only if metadata reproduction fails

If PBIR metadata cannot solve the issue, investigate in this order:

1. report-definition API variants / update sequence;
2. post-deploy API operation that could initialize/refresh visual query state;
3. Desktop-authored PBIP publish path through existing automation;
4. organizational visual registration/order-of-operations timing;
5. custom visual package identity/version mismatch;
6. report rebind APIs or semantic model connection binding;
7. any documented Power BI custom-visual initialization requirement.

Do not introduce UI automation as the product solution unless every programmatic path is exhausted.

### 13. Do not accept a hidden manual workaround

The following do **not** count as success:

- opening report in edit mode programmatically and toggling fields;
- Playwright clicking the editor to activate bindings;
- one manual setup per generated report;
- one manual setup per custom visual instance;
- instructing customers/admins to fix bindings after deployment.

The intended product must remain automated.

### 14. Determine whether one-time template priming is viable

One exception worth testing carefully:

If a pre-authored, correctly bound custom-visual template/report definition can be cloned and have fields/queries replaced programmatically **without triggering the blank-binding issue**, investigate this as a generic architecture.

For example:

```text
pre-initialized custom visual template
→ renderer substitutes semantic field/query metadata
→ deploy cloned report
→ data binds automatically
```

This is acceptable only if:

- no per-report manual action is required;
- field substitution is generic;
- new report items work zero-touch;
- tenant portability remains plausible.

Document whether template priming is a robust solution or merely state leakage from an already-edited artifact.

### 15. Inspect custom visual capabilities/dataViewMappings

Audit the custom visual `capabilities.json` carefully.

Confirm that:

- data roles are correct;
- `dataViewMappings` match the query shape generated by PBIR;
- conditions/min/max cardinality are appropriate;
- categorical/table mappings are valid;
- role names exactly match PBIR bindings;
- chart roles support category + values as intended;
- no API-version mismatch exists.

Add tests to ensure generated PBIR role names match the visual capabilities exactly.

### 16. Inspect the visual update() dataView on blank vs activated state

Instrument the custom visual development build to log non-sensitive diagnostics from `update()` such as:

- whether `options.dataViews` is empty;
- metadata columns count;
- categorical categories/value counts;
- role assignments;
- update type;
- viewport.

Capture diagnostics for:

- fresh blank API deployment;
- manually activated working state;
- each candidate auto-binding fix.

Do not log actual sensitive customer values in future-facing code; for synthetic test data, values may be captured in stage evidence if useful.

### 17. Investigate visual package identity/version behaviour

Confirm whether a custom visual GUID/version/package change causes Power BI to treat it as an uninitialized visual.

Test:

- same GUID + same version;
- same GUID + incremented version;
- organizational store version matching package version;
- report resource package vs org-store resolution.

Record whether binding depends on package registration timing or identity.

### 18. Evidence package

Commit under `docs/stages/07d-a-custom-visual-auto-binding/`:

- PRE report-definition snapshot (normalized/non-secret);
- POST manual-activation snapshot;
- semantic diff JSON;
- human-readable diff summary;
- native-vs-custom binding comparison;
- Desktop-authored comparison if feasible;
- candidate-fix matrix;
- screenshots for blank/activated/final states;
- custom visual update() diagnostics;
- zero-touch run results;
- filter-response results;
- `AUTO_BINDING_MANIFEST.json`;
- `REPORT.md`.

### 19. Automated tests

Add tests covering at minimum:

1. custom visual capability role names match renderer bindings;
2. generated custom visual query state/projections;
3. generated custom visual dataTransforms/queryMetadata if required;
4. deterministic binding payload;
5. KPI single-measure binding;
6. chart category + measure binding;
7. null/empty role handling;
8. package GUID/version mapping;
9. no retail-specific names/IDs;
10. existing full Python suite remains green;
11. custom visual packages still build successfully.

Live Fabric zero-touch tests remain separate from normal unit tests.

## Hard acceptance criteria

### SUCCESS

Stage 07d-a is complete only if all are true:

- the binding activation delta is understood and documented;
- the renderer/deployment pipeline generates the required custom visual binding state automatically;
- a **fresh** API-deployed Premium KPI renders data on first headless view with zero manual interaction;
- a **fresh** API-deployed Premium Chart renders data on first headless view with zero manual interaction;
- zero-touch deployment succeeds **3/3 times** on fresh report state;
- custom visuals respond correctly to inbound slicer/filter changes;
- screenshots prove populated first-render state;
- no edit-mode/browser automation workaround is required;
- solution is generic across fields/metrics, not retail-specific;
- automated tests pass;
- `REPORT.md` and evidence are committed.

### BLOCKED

A blocked outcome is acceptable only if the report demonstrates, with concrete evidence, that no programmatic initialization route is available.

The report must then specify:

- every path tested;
- exact PRE/POST metadata differences;
- why those differences cannot be reproduced;
- whether Desktop-authored artifacts behave differently;
- whether template priming works;
- whether the limitation is REST deployment, PBIR schema, custom visual host behavior, tenant policy, or package registration;
- whether a different automated publishing route remains viable;
- the minimum product compromise that would be required.

Do not call this blocked while unexplained PRE/POST metadata differences remain.

## REPORT.md requirements

Include:

- root-cause summary;
- exact manual activation action;
- PRE/POST report-definition diff findings;
- native vs custom binding comparison;
- Desktop comparison findings;
- custom visual update() diagnostics;
- candidate matrix and results;
- final binding implementation if solved;
- 3-run fresh zero-touch deployment evidence;
- filter-response evidence;
- package identity/registration findings;
- automated test results;
- remaining limitations;
- explicit answer to:

> **Can this project now deploy a freshly generated Power BI report containing premium custom visuals that receive their data automatically on first render, with zero human interaction?**

Do not edit this TASK.md to mark completion. `REPORT.md` is the completion record.
