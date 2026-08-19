---
stage: 05
status: ready
title: Fabric deployment and end-to-end reality test
---

# Stage 05 — Fabric Deployment and End-to-End Verification

## Context

Stages 01–04 have built the complete local generation chain:

```text
Natural-language requirement
    ↓
AI dashboard designer
    ↓
validated DashboardSpec
    ↓
coherent synthetic relational data
    ↓
PBIP/TMDL/PBIR renderer
```

Stage 04 produced a structurally validated PBIP for the live retail fixture: 4 pages, 29 source visuals, 6 semantic tables, 11 measures, 7 relationships, zero visual fallbacks, and 31/31 internal structural checks passing.

However, two critical facts remain unproven:

1. Power BI/Fabric has never actually consumed the generated artifact.
2. Stage 04 semantic-model partitions still contain placeholder M expressions, so the Stage 03 synthetic data is not yet genuinely wired into the deployed semantic model.

This stage is therefore the first uncompromising **end-to-end reality test**.

## Read first

Before changing code:

1. Read `KIRO.md`.
2. Read Stage 01–04 TASK/REPORT files.
3. Inspect `docs/stages/02a-live-designer-test/LIVE_OUTPUT.json`.
4. Inspect Stage 03 data-generation code and live manifest.
5. Inspect Stage 04 renderer, committed `live-project`, and render manifest.
6. Inspect `src/pbi_gen/deploy/fabric.py` in full.
7. Inspect any existing Fabric/workspace configuration and environment-variable handling.
8. Inspect the archived `peter121512/pbi` repository for proven deployment/data-source techniques where useful.
9. Do not expose, print, log, commit or copy credentials/secrets into report artifacts.

## Objective

Prove the following chain with a **real Fabric workspace**:

```text
Stage 02a DashboardSpec
    ↓
Stage 03 generated business data
    ↓
Stage 04 PBIP artifact
    ↓
Fabric deployment
    ↓
semantic model populated with that data
    ↓
refresh succeeds / model becomes queryable
    ↓
report is accepted by Power BI
    ↓
report pages and visuals exist and can render
```

An HTTP success from a deployment API is **not** sufficient.

## Primary live fixture

Use the existing Stage 02a executive UK retail dashboard fixture. Do not substitute a simpler report merely to make deployment easier.

Expected design:

- Executive Overview
- Regional Analysis
- Category Analysis
- Risk Analysis
- 29 source visuals
- 6 tables
- 11 measures
- 7 relationships
- period/region/category filtering
- corporate restrained theme

## Required work

### 1. Inspect real environment first

Before modifying architecture, determine what is actually available through the existing configured Fabric environment:

- authentication method;
- workspace identifier/name;
- Fabric capacity/workspace accessibility;
- existing deployment mechanism (`fabric-cicd` and/or REST APIs);
- whether the workspace supports semantic model/report deployment in the required format;
- practical options for loading generated data.

Reuse existing configuration. Do not ask for credentials if they are already available locally.

If credentials or workspace access are unavailable, record the exact blocker truthfully and stop the live portion rather than fabricating success.

### 2. Replace placeholder data source with a real end-to-end data strategy

This is the most important technical gap from Stage 04.

The deployed semantic model must actually contain/query the Stage 03 generated data.

Choose the simplest robust strategy compatible with Fabric and the existing environment. Investigate before deciding. Viable approaches may include, depending on available Fabric capabilities:

- upload/stage generated CSV/Parquet data into a Fabric-accessible source and generate appropriate Power Query partitions;
- use a Lakehouse/Warehouse if one is already available and straightforward;
- deploy/import semantic-model data through an existing supported route;
- another proven mechanism from the archived implementation.

SQLite itself is an implementation detail of Stage 03. Do not force Fabric to consume SQLite if that creates an artificial architecture problem. A deterministic conversion/export step is acceptable.

Requirements:

- generated rows in Fabric must originate from the Stage 03 dataset;
- relationships/measures must operate over the loaded data;
- no developer-machine absolute path dependency;
- rerunning the pipeline should be deterministic/idempotent enough for development;
- temporary cloud resources should be named clearly and documented;
- no secrets in generated PBIP/TMDL/PBIR files.

### 3. Keep canonical ownership clear

Do not let deployment code re-infer or redesign the dashboard.

- `DashboardSpec` owns analytical/report intent.
- Stage 03 owns generated data.
- Stage 04 renderer owns Power BI artifact construction.
- Stage 05 owns cloud staging/deployment/configuration/verification.

If Stage 04 needs a small data-source abstraction to support real deployment, make the narrowest clean change required and document it.

### 4. Deploy the actual generated PBIP

Deploy the Stage 04 live project through the existing Fabric deployment path where possible.

Verify deployment creates/updates the intended:

- semantic model;
- report;
- workspace items.

Capture non-sensitive IDs/names needed for diagnostics in the Stage 05 report/manifest.

The workflow should be rerunnable without proliferating duplicate items unnecessarily.

### 5. Verify Power BI/Fabric artifact acceptance

This stage must distinguish our own structural validation from **actual platform acceptance**.

Evidence should include as much as the environment permits:

- deployment completed without format/schema rejection;
- semantic model item exists;
- report item exists;
- report references the intended semantic model;
- all expected report pages are present if retrievable;
- refresh/query operations succeed;
- no PBIR/TMDL incompatibility errors are returned by Fabric.

If Fabric rejects generated PBIR/TMDL, diagnose and fix the renderer rather than bypassing it with a hand-built report.

### 6. Populate and refresh the semantic model

Trigger whatever load/refresh operation the chosen data strategy requires.

Verify success explicitly.

Do not treat a submitted refresh request as a successful refresh. Poll/check final state where APIs permit.

Capture:

- refresh/load status;
- elapsed time where practical;
- row-count evidence for core tables where query APIs permit;
- any warnings/errors.

At minimum establish that the `Sales` fact table is populated and the key dimensions are not empty.

### 7. Query-level verification

Where Fabric/Power BI APIs or available tooling permit, execute a small set of semantic queries or equivalent checks against the deployed model.

Verify representative measures/data, preferably including:

- Revenue returns a non-zero value;
- Gross Margin % returns a plausible value;
- YoY Growth % can evaluate;
- Region and Category dimensions return members;
- the generated narrative remains visible in aggregate results where feasible.

If direct DAX querying is unavailable in the environment, document the limitation and use the strongest available alternative evidence.

### 8. Report/page/visual verification

Use the strongest available mechanism to prove the report was actually accepted and is renderable.

Potential evidence, depending on environment/tooling:

- Fabric/Power BI report metadata APIs;
- export/render APIs;
- screenshots from an available browser/Desktop route;
- report page enumeration;
- report visual metadata where accessible.

The ideal outcome is a screenshot or rendered image of each page. If this is technically unavailable, do not fake it; document exactly what was and was not visually verified.

### 9. Visual-quality review if screenshots are obtainable

If rendered screenshots/images can be captured, review them against the original design intent.

Assess:

- executive hierarchy;
- whitespace/density;
- KPI prominence;
- chart appropriateness;
- title/label readability;
- theme application;
- slicer placement;
- obvious overlap/clipping;
- colour consistency;
- whether the dashboard looks premium/boardroom-ready rather than merely functional.

Record concrete visual defects separately from technical deployment defects.

Do not claim visual quality without seeing rendered output.

### 10. Fix Stage 04 compatibility defects discovered by Fabric

A real platform test is expected to expose issues our structural validator could not know about.

Fix narrowly scoped defects such as:

- invalid PBIR property names/shapes;
- TMDL syntax incompatibilities;
- unsupported visual query-state structures;
- theme registration problems;
- dataset-reference errors;
- invalid IDs/metadata;
- partition/data-source definitions;
- Fabric deployment integration issues.

Add regression tests for every meaningful defect discovered.

### 11. Do not hide unsupported visuals

If Power BI accepts the report but one or more visual configurations fail, preserve the Stage 04 fidelity principle.

Every source visual must end as one of:

- rendered successfully;
- rendered through an explicit fallback;
- known failed/unsupported with a diagnostic.

Do not delete troublesome visuals simply to make deployment pass.

### 12. Slicer/layout debt

Stage 04 currently appends generated slicer visuals below main content rather than optimally integrating them into the designer grid.

During real rendering:

- determine whether this causes clipping, off-canvas placement or obviously poor presentation;
- if it causes a functional/rendering defect, fix it in this stage;
- if it is merely a visual-polish issue, document it clearly for the visual-critic/refinement stage.

### 13. Conditional formatting debt

Stage 04 does not yet translate `conditional_formats` into PBIR.

Do not derail the deployment stage to reverse-engineer every conditional-format schema. However, if the Risk page is materially weakened in the real rendered output, document this as a high-priority refinement requirement.

### 14. Typed deployment result

If the current deployment module returns weak/unstructured results, introduce a small typed result model sufficient to distinguish:

- deployment success;
- authentication/workspace failure;
- semantic-model deployment failure;
- report deployment failure;
- data staging failure;
- refresh failure;
- verification failure.

Do not build a large orchestration framework.

### 15. Idempotence and cleanup

Prefer updating/redeploying a clearly named development artifact rather than creating duplicates on each run.

Document any Fabric items created.

Do not delete unrelated workspace items.

### 16. Stage manifest

Commit a non-sensitive machine-readable manifest such as `LIVE_DEPLOYMENT_MANIFEST.json` containing useful evidence, for example:

- timestamp;
- workspace name/id if safe;
- report name/id;
- semantic model name/id;
- data staging mechanism;
- generated table row counts;
- deployment outcome;
- refresh outcome;
- query-verification results;
- expected vs verified pages/visuals where retrievable;
- screenshots/artifact paths if captured;
- warnings/known limitations.

Never include access tokens, client secrets, connection-string passwords or other credentials.

## Acceptance criteria

Stage 05 is complete only when the outcome is reported truthfully and one of the following is established.

### Full success

- the actual Stage 04 live retail PBIP is accepted by Fabric/Power BI;
- semantic model and report are deployed;
- Stage 03 data is genuinely loaded into the deployed model through a Fabric-accessible data path;
- refresh/load reaches a successful final state;
- representative data/measures are verified where APIs permit;
- report existence/page/render evidence is captured using the strongest available mechanism;
- all compatibility defects discovered are fixed with regression tests;
- full automated test suite remains green;
- deployment manifest and `REPORT.md` are committed.

### Honest blocked outcome

If external platform access/permissions/capacity/API constraints prevent completion:

- the deployment was genuinely attempted as far as possible;
- exact blocker and evidence are documented;
- no success is fabricated;
- all local integration work possible without bypassing the blocker is completed;
- the report states precisely what user/environment action is required next.

A blocked report is preferable to a false green result.

## Tests

Add automated tests where code changes warrant them, including at minimum:

1. data staging/export transformation;
2. deployment result/error classification;
3. data-source/partition generation for the chosen cloud strategy;
4. idempotent naming/config behaviour;
5. regression tests for every Fabric incompatibility fixed;
6. no secrets/absolute developer paths in generated artifacts;
7. all existing Stage 01–04 tests remain passing.

Live Fabric tests must be clearly separated from the normal unit/integration suite and should not make routine tests require cloud credentials.

## Non-goals

Do NOT expand this stage into:

- conversational revision;
- autonomous screenshot critic/reviser loops;
- user-facing application UI;
- production-grade tenant provisioning;
- RLS/security architecture;
- every conditional-format property;
- mobile layout;
- arbitrary real customer data ingestion;
- broad Fabric administration.

The purpose is to prove that **our generated dashboard actually works in Power BI**.

## REPORT.md requirements

The completion report must include:

- exact environment/workspace used, omitting secrets;
- authentication mechanism at a non-sensitive level;
- exact deployment path used;
- data staging/loading strategy;
- any Stage 03/04 code changes required;
- semantic model deployment result;
- report deployment result;
- refresh/load final result;
- row-count/query evidence where available;
- report/page/visual acceptance evidence;
- screenshot/render evidence if obtainable;
- visual-quality observations only if output was actually seen;
- compatibility defects discovered and fixes made;
- automated test results;
- live-test result;
- Fabric items created/updated;
- known limitations;
- whether the project has now achieved a genuine prompt-to-working-Power-BI-dashboard path;
- recommended next stage.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
