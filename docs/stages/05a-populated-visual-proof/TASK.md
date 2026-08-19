---
stage: 05a
status: ready
title: Populated dashboard and visual proof
---

# Stage 05a — Populated Dashboard and Visual Proof

## Context

Stage 05 proved that Fabric accepts the generated semantic model and PBIR report. The actual generated report exists in the Fabric workspace with all four intended pages.

However, Stage 05 did **not** prove that we have a working populated dashboard:

- dataset refresh failed because the generated Date dimension contained blank primary-key values;
- the large Sales fact table still used a placeholder M expression rather than real Stage 03 data;
- representative DAX measures were therefore not proven against the deployed model;
- no rendered screenshots were captured, so the 29 visuals have not actually been visually inspected.

Stage 05a closes those gaps. Do not declare the prompt-to-dashboard pipeline complete until the dashboard is populated and visually observed.

## Read first

1. Read `KIRO.md`.
2. Read Stage 03, 04 and 05 TASK/REPORT files.
3. Inspect Stage 03 data generator and its key/FK generation carefully.
4. Inspect Stage 05 inline-M/data-staging implementation.
5. Inspect the deployed Stage 05 semantic model/report IDs and reuse/update the existing development artifacts rather than creating duplicates.
6. Inspect available Power BI/Fabric REST APIs and local browser automation capabilities before choosing screenshot strategy.
7. Never commit credentials, tokens, cookies or embed tokens.

## Objective

Prove this exact chain:

```text
Stage 03 generated data
    ↓
ALL six tables genuinely loaded into Fabric semantic model
    ↓
refresh reaches successful final state
    ↓
representative DAX/data queries return valid values
    ↓
existing four-page report renders with populated visuals
    ↓
screenshots captured and reviewed
```

This is a completion test, not another structural test.

## Hard acceptance rule

Stage 05a is only a full success if **all** of the following are true:

1. no required semantic-model table is backed by placeholder data;
2. refresh/load reaches a successful final state;
3. the Sales fact table is populated with the generated Stage 03 rows;
4. key dimensions are populated and relationship keys are valid;
5. representative measures evaluate successfully;
6. the report renders populated data;
7. screenshots or equivalent rendered visual evidence are captured for all four pages.

If external API/browser limitations prevent visual capture after the populated model is proven, report that separately as a visual-verification blocker. Do not call it full success.

## Required work

### 1. Fix Stage 03 key quality at the source

Diagnose why the Date primary key contains blanks/nulls.

Fix the generator generically, not with a retail-fixture patch.

Add deterministic validation before data generation is considered successful:

- primary/key columns required by relationships contain no null/blank values;
- dimension-side relationship keys are unique where required;
- fact-side foreign keys reference existing dimension keys;
- no relationship-required key column is missing;
- date keys/date columns are valid and parseable.

Add regression tests reproducing the Stage 05 failure.

Regenerate the live retail dataset and verify these invariants locally before touching Fabric.

### 2. Replace the Sales placeholder with real data

The Stage 05 report states that only small dimensions are embedded through inline `Table.FromRows()` while Sales still uses a placeholder because ~10K rows were considered impractical to inline.

That is not an acceptable final data path.

Implement a real Fabric-accessible staging strategy for **all tables**, including Sales.

Investigate available workspace capabilities first. Prefer, in order of practicality for this development environment:

- Fabric Lakehouse/OneLake staging using CSV or Parquet;
- Fabric Warehouse staging;
- another existing Fabric-accessible source already available in the workspace;
- inline M only if actual testing proves the complete Sales table can be deployed/refreshed reliably and within practical payload limits.

Do not invent a complex production ingestion platform. This is mocked dashboard data; choose the simplest robust cloud-accessible path.

SQLite remains a local generation format, not a required cloud format. Export to CSV/Parquet if appropriate.

### 3. Ensure all six tables originate from Stage 03

For the live fixture, verify the deployed semantic model uses the generated contents of:

- Sales
- Date
- Store
- Region
- Product
- Risk

No table may silently fall back to empty/example/placeholder rows.

Record expected local row counts and, where possible, deployed/queryable row counts.

### 4. Redeploy/update existing Fabric artifacts

Update the existing development semantic model/report rather than proliferating duplicates where practical.

After renderer/data-source changes:

- render the project again;
- deploy/update the semantic model;
- deploy/update the report;
- confirm the report still points at the intended semantic model;
- retain all four pages.

### 5. Refresh to final success

Trigger refresh/load and poll to terminal state.

Acceptance requires a **successful final refresh**, not merely request submission.

Capture non-sensitive evidence:

- start/end or elapsed time;
- final status;
- any warnings;
- refresh identifier if useful and non-sensitive.

If refresh fails, diagnose and fix the root cause within Stage 03–05 scope and retry. Add regression tests for code defects discovered.

### 6. Query the populated semantic model

Use the Power BI execute-queries API, XMLA, or strongest available equivalent.

At minimum verify:

- `COUNTROWS(Sales)` is non-zero and plausibly matches the generated fact-row count;
- Revenue evaluates and is non-zero;
- Gross Margin % evaluates and is plausible;
- YoY Growth % evaluates;
- Region returns expected members;
- Category returns expected members.

Where practical compare key aggregates against local Stage 03 verification results to detect ingestion/model discrepancies.

Record actual values in the report/manifest when non-sensitive.

### 7. Obtain rendered report evidence

Capture a rendered image/screenshot of **each of the four report pages**.

Investigate the simplest available route, such as:

- Power BI export/render APIs;
- authenticated browser automation against the Fabric/Power BI report URL using the existing user session;
- embed token + Playwright if necessary and feasible;
- another available official rendering route.

Do not commit authentication state, cookies or tokens.

Commit screenshots under the Stage 05a directory if they contain only synthetic data and no sensitive tenant/user UI details. Crop/redact unrelated account chrome if needed.

If screenshots cannot safely be committed, record their local paths and commit a non-sensitive visual verification manifest instead.

### 8. Verify all four pages visually

Screenshots required:

- Executive Overview
- Regional Analysis
- Category Analysis
- Risk Analysis

For each page verify at minimum:

- page loads;
- visuals display data rather than errors/placeholders;
- no obvious broken visual icons;
- no catastrophic overlap/clipping;
- KPI values appear;
- chart axes/categories/series populate;
- theme appears applied;
- slicers are visible and not functionally broken.

### 9. First visual-quality assessment

Now that actual rendered output exists, assess it against the product bar.

Rate each page and the overall report on:

- executive/C-suite credibility;
- information hierarchy;
- whitespace and density;
- visual-type appropriateness;
- KPI prominence;
- typography/readability;
- colour/theme consistency;
- slicer/filter placement;
- alignment/spacing;
- storytelling/analytical coherence;
- whether it feels genuinely premium and demo-ready.

Be critical. A technically working dashboard is not automatically an impressive dashboard.

Record concrete defects with page + visual references where possible. This assessment becomes the input to the next visual-refinement stage.

### 10. Visual count evidence

Where APIs/DOM/report metadata permit, verify the intended visual population beyond page count.

Expected source visuals: 29, plus renderer-generated slicers as applicable.

If exact visual enumeration is not accessible, use screenshot evidence and clearly state the limitation.

### 11. Data-source architecture cleanup

If Stage 05 introduced temporary inline-M logic that is superseded by the real staging approach, simplify it rather than leaving competing paths without purpose.

Keep a clean abstraction between:

- local generated dataset;
- cloud staging adapter;
- semantic-model partition/source rendering;
- deployment orchestration.

Do not over-engineer for arbitrary production customer data yet.

### 12. Manifest

Commit `LIVE_POPULATED_MANIFEST.json` containing non-sensitive evidence such as:

- local generated row counts by table;
- cloud staging method;
- deployed item IDs/names if safe;
- refresh final status and elapsed time;
- deployed/query row counts where available;
- representative measure results;
- four page names;
- screenshot paths/status;
- visual verification summary;
- known warnings.

No secrets/tokens/cookies.

## Tests

Add tests for code changes, including at minimum:

1. null/blank PK rejection;
2. uniqueness of dimension-side keys;
3. FK referential integrity;
4. valid generated Date keys;
5. export/staging of large fact tables;
6. partition/source generation for the chosen Fabric data strategy;
7. regression tests for every refresh/deployment defect fixed;
8. no secrets/local absolute paths in committed generated artifacts;
9. all existing Stage 01–05 tests remain green.

Live Fabric/browser tests must remain separate from routine automated tests.

## Non-goals

Do NOT expand this stage into:

- conversational revisions;
- autonomous LLM screenshot revision loops;
- general CLI/product UX;
- arbitrary customer data ingestion;
- production multi-tenant infrastructure;
- exhaustive conditional-format implementation;
- mobile layouts.

This stage exists to get the **first genuinely populated generated dashboard on screen**.

## Acceptance criteria

### Full success

- Stage 03 key-quality defect fixed generically with regression tests;
- all six live tables use real Stage 03-generated data in Fabric;
- Sales no longer uses a placeholder source;
- semantic model/report deploy successfully;
- refresh/load finishes successfully;
- Sales row count and representative dimensions are verified;
- Revenue, Gross Margin %, and YoY Growth % evaluate successfully;
- all four report pages render populated data;
- rendered visual evidence exists for all four pages;
- first critical visual-quality assessment is documented;
- complete automated suite passes;
- `LIVE_POPULATED_MANIFEST.json` committed;
- `REPORT.md` committed and pushed.

### Honest blocked outcome

If an external limitation prevents one of these after genuine attempts, document precisely:

- what succeeded;
- what failed;
- exact blocker/evidence;
- whether the blocker is code, data, Fabric capability/permissions, or visual-capture tooling;
- the minimum next action required.

Do not downgrade the acceptance criterion merely to obtain a green report.

## REPORT.md requirements

Include:

- Stage 03 key defect root cause and fix;
- local integrity validation results;
- final data-staging architecture;
- row counts for all six local/staged/deployed tables where available;
- deployment/update result;
- refresh terminal result;
- representative semantic query/DAX results;
- page/render verification;
- screenshot paths/evidence;
- visual-quality assessment by page and overall;
- defects found and fixes made;
- automated test results;
- Fabric items created/updated;
- remaining limitations;
- an explicit answer to: **Do we now have a genuinely populated prompt-generated Power BI dashboard that we have actually seen render?**
- recommended next stage.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
