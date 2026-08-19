---
stage: 05b
status: ready
title: Measure repair and rendered visual capture
---

# Stage 05b — Measure Repair and Rendered Visual Capture

## Context

Stage 05a completed the real data path:

- all six Stage 03 tables are loaded into the deployed Fabric semantic model;
- Sales contains the full 10,000 generated fact rows;
- refresh succeeds in ~5 seconds;
- row counts and dimension members are queryable;
- the four-page report remains deployed.

Two blockers remain:

1. key business measures do not evaluate correctly (`TotalRevenue`, `GrossMarginPct`, `YoYGrowthPct`);
2. the report has not yet been visually captured, so the dashboard's actual rendered quality is still unknown.

This stage must close both gaps.

## Objective

Prove that:

```text
real Stage 03 data
    ↓
valid deployed semantic model
    ↓
all critical DAX measures evaluate correctly
    ↓
report visuals render populated values
    ↓
all four pages captured as images
    ↓
first serious visual-quality review completed
```

## Read first

1. Read `KIRO.md`.
2. Read Stage 04, 05 and 05a TASK/REPORT files.
3. Inspect the deployed TMDL for `Sales`, `Date`, and all measure definitions.
4. Inspect the Stage 02a `MeasureSpec` values in `LIVE_OUTPUT.json`.
5. Inspect Stage 05a data-source/M generation and actual deployed column names/types.
6. Reuse the existing Fabric semantic model/report items; do not create duplicates unless unavoidable.
7. Do not commit tokens, browser profiles, cookies, credentials or secrets.

## Part A — Repair semantic measures

### 1. Diagnose the actual measure failures

Do not assume the cause from the Stage 05a report. Verify it.

For each failing measure, inspect:

- generated TMDL expression;
- home table;
- referenced table/column names;
- quoting/escaping;
- deployed metadata if retrievable;
- data types;
- relationship/time-intelligence prerequisites;
- date-table semantics required by functions such as `SAMEPERIODLASTYEAR`.

At minimum diagnose:

- `TotalRevenue`;
- `GrossMarginPct`;
- `YoYGrowthPct`.

Also query every other deployed measure so latent failures are discovered now rather than later.

### 2. Fix the problem generically

Fix the appropriate layer:

- designer/spec generation if DAX itself is invalid;
- renderer/TMDL generation if valid DAX is being serialized incorrectly;
- semantic-model metadata if time intelligence/date semantics are missing;
- data generator if required underlying columns are wrong.

Do not hard-code special cases for the retail fixture unless the fix is genuinely domain-specific and represented explicitly in the spec.

### 3. Measure validation before deployment

Add deterministic pre-deployment checks where feasible.

Potential checks include:

- every measure's referenced columns/tables exist;
- obvious malformed table/column references are rejected;
- date intelligence measures have a viable date field/model relationship;
- measure home tables exist;
- format strings remain valid strings and do not corrupt TMDL syntax.

This does not need to become a full DAX parser.

### 4. Redeploy and refresh

After fixes:

- regenerate/re-render the PBIP;
- update the existing semantic model/report;
- refresh to terminal success;
- confirm all six table row counts remain correct.

### 5. Query all measures

Use Execute Queries / strongest available semantic-query route.

Record results for **all 11 live-fixture measures**.

At minimum these must succeed and return plausible values:

- Total Revenue;
- Gross Margin %;
- YoY Growth %;
- any revenue prior-year/comparison measure;
- risk count / underperformance measure;
- regional/category measures used by visuals.

Compare selected values against local Stage 03 calculations where practical.

Acceptance requires no critical measure used by a visible report visual to remain broken.

## Part B — Capture actual rendered pages

### 6. Reassess screenshot options from scratch

Stage 05a found:

- Power BI ExportTo returned 403 because tenant export-to-image is disabled;
- Playwright could not launch against the active Edge user profile because it was locked.

Do not simply repeat the same failing attempts unchanged.

Investigate alternatives, prioritising paths that work with the current environment and user authentication:

1. attach to an already-running Chromium/Edge instance through remote debugging if available;
2. launch a separate browser profile and authenticate interactively if practical;
3. use Playwright storage state copied/exported safely from an authenticated session without committing it;
4. use an embed token via supported Power BI/Fabric APIs if available with current permissions;
5. use report export to PDF/PPTX and render pages to images if image export alone is disabled but document export is allowed;
6. use Power BI Desktop only if available;
7. another official/robust capture mechanism supported by the environment.

The goal is not specifically PNG via one API. The goal is **reliable rendered visual evidence**.

### 7. Capture all four pages

Required pages:

- Executive Overview;
- Regional Analysis;
- Category Analysis;
- Risk Analysis.

Capture one readable full-page image per page after visuals have loaded.

Synthetic business data is safe to commit, but crop or avoid tenant/account chrome where practical.

Preferred path:

`docs/stages/05b-measures-and-visual-capture/screenshots/<page>.png`

If images cannot safely be committed, retain local evidence and commit a manifest describing capture status and hashes/paths.

### 8. Verify visual population

From the rendered output verify:

- KPI cards show values;
- line/bar/donut/scatter/map/table visuals render data;
- no broken visual/error icons;
- slicers populate with values;
- axes/categories/legends are populated;
- all expected pages are usable;
- no catastrophic visual overlap or off-canvas placement.

Record page-level defects precisely.

## Part C — First serious dashboard-quality assessment

### 9. Assess against the actual product bar

This is the first time the dashboard can be judged as a dashboard rather than as code/configuration.

For each page and overall, assess:

- C-suite credibility;
- information hierarchy;
- KPI prominence;
- visual type appropriateness;
- whitespace and density;
- alignment and spacing;
- typography/readability;
- colour/theme execution;
- slicer placement and usability;
- chart labelling/axis quality;
- storytelling and analytical coherence;
- whether negative/risk states are visually clear;
- whether it looks genuinely premium and boardroom-ready.

Use a strict 1–5 rating per dimension if useful, but accompany ratings with concrete observations.

### 10. Separate designer defects from renderer defects

For every notable visual problem, classify likely ownership:

- **designer/spec issue** — poor visual choice, too many visuals, weak hierarchy, bad page architecture;
- **renderer issue** — styling not applied, sizing/spacing wrong, slicers misplaced, labels/axes bad, visual properties missing;
- **data issue** — values/story not obvious enough;
- **Power BI platform behaviour** — automatic formatting/layout differences.

This distinction is important for the next refinement stage.

### 11. Prioritised visual defect backlog

Create a concise ranked list of the most important changes required to reach the target quality bar.

Prioritise by impact on executive demo quality, not engineering convenience.

Examples may include:

- slicers appended below the composition;
- missing conditional formatting on risk visuals;
- weak KPI treatment;
- poor chart labels;
- excessive visual density;
- inconsistent margins/alignment;
- theme not translating strongly enough;
- default Power BI formatting undermining premium appearance.

Do not fix every cosmetic issue in 05b unless a small fix is required simply to make the output interpretable. The next stage should own systematic visual refinement.

## Part D — Evidence and tests

### 12. Manifest

Commit `LIVE_VISUAL_PROOF_MANIFEST.json` containing non-sensitive evidence:

- semantic model/report IDs;
- refresh final status;
- table row counts;
- all measure query outcomes/values;
- screenshot/capture method;
- screenshot paths/status;
- page names;
- visual population status by page;
- quality ratings/summary;
- prioritized defect categories;
- warnings/limitations.

### 13. Tests

Add tests for all code fixes, including:

1. regression tests for DAX/TMDL issue(s) found;
2. measure reference validation;
3. date/time-intelligence metadata if introduced;
4. all existing Stage 01–05a tests remain green;
5. no secrets/browser auth state included in tracked files.

Live Fabric/browser capture remains outside the routine unit suite.

## Hard acceptance criteria

### Full success

Stage 05b is fully complete only when:

- every critical measure used by visible report visuals evaluates successfully;
- all 11 measures have been queried and results documented;
- refresh remains successful;
- all six real data tables remain populated;
- all four report pages have been captured as rendered visual evidence;
- visuals are visibly populated rather than erroring;
- first critical visual-quality assessment is documented;
- designer-vs-renderer defect ownership is identified;
- prioritized refinement backlog exists;
- complete automated test suite passes;
- manifest + report + intended screenshots/evidence are committed and pushed.

### Honest blocked outcome

If visual capture remains externally blocked after trying materially different approaches, report exactly what was attempted and why it failed. However, measure repair must still be completed if technically possible.

Do not call the stage fully successful without rendered visual evidence.

## Non-goals

Do NOT expand 05b into:

- full conversational revision;
- autonomous LLM visual redesign loop;
- comprehensive redesign of all 29 visuals;
- production UI/CLI;
- arbitrary customer data ingestion;
- tenant administration changes outside what the user explicitly authorizes.

The stage is about **making the report numerically correct and finally seeing it**.

## REPORT.md requirements

Include:

- root cause of each broken measure;
- files/code changed;
- measure-validation improvements;
- deployment/refresh result;
- table row counts;
- actual results for all 11 measures;
- screenshot/capture approaches attempted;
- final capture method;
- screenshot paths/evidence for all four pages;
- visual population findings;
- page-by-page quality assessment;
- overall quality assessment against the C-suite bar;
- designer vs renderer vs data defect classification;
- prioritized refinement backlog;
- tests run/results;
- remaining limitations;
- explicit answer to: **Have we now seen a numerically correct, populated, prompt-generated Power BI dashboard render in Fabric?**
- recommended next stage.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
