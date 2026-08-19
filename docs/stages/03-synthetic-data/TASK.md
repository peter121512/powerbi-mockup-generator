---
stage: 03
status: ready
title: Narrative-driven synthetic data generation
---

# Stage 03 — Narrative-Driven Synthetic Data Generation

## Context

Stage 01 established the canonical rich `DashboardSpec`. Stage 02 implemented the AI dashboard designer and deterministic clarification/validation boundaries. Stage 02a proved the live designer against Amazon Bedrock and committed a realistic 4-page retail executive specification at:

`docs/stages/02a-live-designer-test/LIVE_OUTPUT.json`

The project now has a real, validated dashboard design containing:

- analytical intent;
- tables, columns, relationships and DAX measures;
- page architecture and visual bindings;
- filters and interactions;
- enterprise design-system intent;
- a `MockDataNarrative` describing the business story the generated data should exhibit.

The next objective is to make that specification **demonstrable** by creating synthetic relational data whose analytical behaviour supports the intended dashboard story.

The product quality bar is not “populate tables with random values”. The generated data should make the intended trends, comparisons, risks and executive insights visibly true when the eventual Power BI report is rendered.

## Read first

Before changing code:

1. Read `KIRO.md`.
2. Read `README.md`.
3. Read the Stage 01 task/report and `src/pbi_gen/models/dashboard_spec.py`.
4. Read the Stage 02 task/report and designer implementation.
5. Read the Stage 02a task/report and inspect `LIVE_OUTPUT.json` in full.
6. Inspect any useful synthetic-data/database-generation code in the legacy `peter121512/pbi` repository or archived project history if available, but treat it as evidence rather than an architecture to copy.
7. Preserve the existing deployment/rendering baseline; this stage should create a clean data-generation boundary rather than entangle data generation with Fabric deployment.

## Stage objective

Implement a deterministic synthetic-data engine that accepts a validated canonical `DashboardSpec` and produces a coherent relational mock dataset suitable for later Power BI artefact generation.

The engine must use the spec's semantic model and `MockDataNarrative` as the source of truth.

Conceptually:

```python
generate_synthetic_data(spec: DashboardSpec, ...) -> DataGenerationResult
```

The exact public API is an implementation decision.

The output should be reproducible, inspectable, structurally valid, and rich enough for the intended measures/visuals to show meaningful results.

## Core design principle

Synthetic data generation should proceed approximately as:

```text
Validated DashboardSpec
    ↓
Semantic-model inspection
    ↓
Dimension/member planning
    ↓
Date/calendar generation
    ↓
Fact-grain determination
    ↓
Narrative pattern interpretation
    ↓
Deterministic base-value generation
    ↓
Pattern application / business-story shaping
    ↓
Relational integrity validation
    ↓
Analytical verification
    ↓
SQLite dataset + generation diagnostics
```

Do not generate each column independently with random values. Relationships and business behaviour must be generated together.

## Required capabilities

### 1. Public data-generation boundary

Create an explicit service/function that consumes the canonical `DashboardSpec` and returns a typed result.

The result should distinguish at minimum:

- success;
- invalid/unsupported specification;
- generation failure;
- analytical verification failure.

On success, expose enough metadata for downstream code to know where the generated dataset is and what was generated.

Prefer a typed result/error contract rather than callers inferring state from exceptions or strings.

### 2. SQLite as the Stage 03 storage target

Use SQLite as the generated-data target unless repository evidence shows a materially better already-working local format.

Requirements:

- create one table per relevant `TableSpec`;
- preserve column names expected by `FieldRef` and relationships;
- use SQLite-compatible types derived from the canonical column types;
- create primary/unique keys where the schema clearly identifies them;
- preserve referential integrity across generated tables;
- create the database in a caller-specified/output directory rather than a machine-specific hard-coded path;
- replace/overwrite safely and intentionally when requested;
- do not commit generated `.db` files unless a test fixture is deliberately small and justified.

### 3. Deterministic generation and reproducibility

Generation must accept a seed and produce reproducible output for the same spec + seed.

Randomness may be used internally, but all random behaviour must flow from a controlled seeded generator.

Record the effective seed in diagnostics.

Tests should assert reproducibility for representative datasets.

### 4. Semantic-model-driven table generation

Use `DashboardSpec.tables`, columns and relationships to construct the relational dataset.

The engine should infer practical generation roles such as:

- date/calendar dimensions;
- categorical dimensions;
- entity dimensions (store, customer, product, region, etc.);
- fact/event tables;
- risk/target/helper tables where specified.

Avoid hard-coding retail-specific table names into the engine. Retail-specific behaviour belongs in the input spec/narrative or reusable pattern logic.

A limited amount of deterministic inference from table structure is acceptable and should be explicit/testable.

### 5. Date/calendar generation

Generate realistic date dimensions when the spec contains date-related tables/columns.

At minimum support common fields where present, such as:

- date;
- year;
- quarter;
- month number;
- month name;
- year-month;
- fiscal period/year where reasonably inferable.

Use the `MockDataNarrative.time_period` when it can be parsed reliably. Where it cannot, apply a documented deterministic fallback rather than silently producing nonsense.

The generated calendar must be adequate for YoY/trend measures in the live Stage 02a spec.

### 6. Dimension/member generation

Generate credible categorical members using schema descriptions/sample values where available.

Priority of evidence should broadly be:

1. explicit sample values in `ColumnSpec`;
2. narrative/domain clues;
3. deterministic generic fallbacks.

Examples:

- region fields should receive coherent region values;
- category fields should receive plausible category members;
- status/risk fields should use a bounded meaningful vocabulary;
- IDs/keys must be unique and stable within a generation run.

Do not make a live LLM call just to invent dimension members in this stage.

### 7. Fact-grain and relationship coherence

Determine a practical fact grain from the spec and generate enough rows for all intended visualisations to behave credibly.

The generator must ensure:

- fact foreign keys resolve to generated dimensions;
- many-to-one relationships are honoured;
- required combinations exist across time and dimensions;
- data volume is sufficient to create smooth trends and meaningful category/region comparisons;
- row counts remain modest enough for fast local testing and Power BI mock-up refreshes.

Use `row_count_hint` as evidence, not an absolute instruction when a richer fact grain is required to make the dashboard story work.

### 8. Narrative pattern engine

Implement reusable deterministic support for the `DataPatternType` values required by the live Stage 02a scenario and representative Stage 01 tests.

At minimum support meaningfully:

- `TREND_UP`;
- `TREND_DOWN`;
- `SEASONAL`;
- `VARIANCE_HIGH` / `VARIANCE_LOW` where relevant;
- `OUTLIER_POSITIVE` / `OUTLIER_NEGATIVE`;
- `TARGET_MISS` / `TARGET_HIT`;
- `CONCENTRATION`;
- `RANKING_CLEAR`;
- `YOY_GROWTH`;
- `YOY_DECLINE`;
- `PARETO`;
- `FLAT`.

If other enum values are straightforward to support cleanly, they may be added, but do not chase enum completeness at the cost of quality.

Pattern application must use the narrative's `applies_to`, `parameters`, descriptions and key insights where practical.

Patterns should alter underlying generated facts in a way that downstream measures can discover, rather than storing precomputed “insight labels”.

### 9. Coherent metric construction

When a dashboard requests financially related columns/metrics, generate underlying values that reconcile sensibly.

Examples of desirable behaviour where relevant:

- revenue = quantity × unit price or another internally coherent construction;
- gross profit/margin derives consistently from revenue and cost;
- percentage measures remain in plausible ranges;
- target/actual relationships reconcile;
- aggregate totals match the underlying rows;
- negative revenue/cost values should not appear unless the schema/story clearly permits them.

Do not parse and execute arbitrary DAX in Stage 03. The generator should generate the base columns needed for measures to evaluate correctly later.

### 10. Analytical verification

After generation, perform deterministic checks that the dataset actually exhibits important requested narrative behaviours.

At minimum, for supported patterns, verify representative properties such as:

- positive/negative trend direction;
- YoY growth or decline sign/magnitude within tolerance;
- intended ranking/concentration;
- presence and location of configured outliers;
- target hit/miss behaviour;
- basic reconciliation constraints.

Return structured verification diagnostics rather than a single boolean.

If a required high-impact narrative pattern is not present after generation, treat that as a generation/verification failure rather than silently accepting random data.

### 11. Constraints

Interpret `MockDataNarrative.constraints` conservatively.

Implement deterministic validation for common constraints that can be expressed safely without general natural-language execution, e.g.:

- values non-negative;
- margins within plausible bounds;
- totals reconcile;
- dates fall inside requested period;
- foreign keys resolve.

Do not build a general natural-language constraint interpreter. Unsupported constraints should be recorded in diagnostics as unverified rather than pretended to be enforced.

### 12. Measures awareness without DAX execution

The generator should inspect `MeasureSpec` names/descriptions/expressions only enough to understand which underlying columns/time structure must exist.

Do not build a DAX engine.

Where a measure depends on a missing base column or impossible semantic-model requirement, fail clearly or return an unsupported-spec result.

### 13. Diagnostics / manifest

On successful generation, produce a small structured manifest/diagnostics object containing useful information such as:

- seed;
- output path;
- tables generated;
- row counts;
- generation period;
- patterns applied;
- pattern verification results;
- unsupported/unverified constraints;
- warnings;
- elapsed time if convenient.

Optionally persist a JSON manifest beside the database if that simplifies downstream stages.

### 14. Stage 02a live-spec integration test

Use `docs/stages/02a-live-designer-test/LIVE_OUTPUT.json` as the primary integration fixture.

Generate a real SQLite dataset from that spec.

The integration verification should demonstrate, at minimum, that:

- all six specified tables are generated as appropriate;
- all required relationship keys reconcile;
- date coverage supports YoY analysis;
- revenue/gross-margin data is coherent;
- the intended overall YoY growth is visible;
- regional/category differences are visible;
- the described underperformance/risk story appears in the data;
- the generated dataset is structurally suitable for the next PBIP/PBIR stage.

Persist a lightweight **manifest / verification report**, not necessarily the full SQLite binary, under the Stage 03 docs directory so the result is reviewable from Git.

## Representative Stage 02a business story

The live designer report describes a scenario broadly including:

- overall UK retail growth;
- regional variation, including stronger and weaker regions;
- category winners/laggards;
- margin compression caused by promotional activity;
- underperformance outliers/risk areas;
- seasonal/trend behaviour;
- Pareto/concentration behaviour.

Use the actual `MockDataNarrative` in `LIVE_OUTPUT.json` as the source of truth rather than copying these bullets blindly.

## Tests

Add meaningful automated tests covering at minimum:

1. deterministic/reproducible generation with a fixed seed;
2. SQLite schema/table creation from `TableSpec`;
3. key uniqueness and foreign-key coherence;
4. date dimension generation;
5. dimension member generation from sample values;
6. fact-table generation at useful grain;
7. upward and downward trend patterns;
8. YoY growth/decline patterns;
9. seasonality;
10. concentration/Pareto/ranking;
11. positive/negative outliers;
12. target hit/miss where supported;
13. reconciliation of related financial values;
14. structured analytical verification;
15. clear failure for structurally impossible specs;
16. unsupported constraints recorded honestly;
17. generation from the committed Stage 02a live spec;
18. full existing Stage 01/02 tests remain passing.

No automated test should require AWS credentials or network access.

Prefer invariant/behaviour tests over asserting exact large generated datasets.

## Integration artefacts

Under `docs/stages/03-synthetic-data/`, commit:

- `TASK.md`;
- `REPORT.md` on completion;
- a concise JSON manifest/verification artefact from generating the Stage 02a live spec, e.g. `LIVE_DATA_MANIFEST.json`.

Do not commit secrets or machine-specific paths. Prefer repository-relative/normalised paths in committed diagnostics.

Do not commit a large SQLite database unless it is genuinely small and useful as a fixture; the report should state where it was generated locally.

## Non-goals

Do NOT expand this stage into:

- PBIP/TMDL/PBIR generation;
- Fabric deployment;
- Power BI refresh;
- screenshot capture;
- visual QA/critic agent;
- conversational revision;
- execution of arbitrary DAX;
- a generic synthetic-data platform;
- LLM-based row-by-row generation;
- exhaustive natural-language constraint parsing;
- production-scale data volumes.

The output of Stage 03 is a **credible, coherent mock relational dataset** ready for the future Power BI renderer/deployer.

## Engineering expectations

Prefer a small, explicit architecture conceptually similar to:

```text
SyntheticDataGenerator
    ├── semantic model planner
    ├── date/dimension generators
    ├── fact generator
    ├── narrative pattern applicators
    ├── SQLite writer
    └── analytical verifier
```

Exact modules/classes are implementation decisions.

Keep the pattern engine deterministic and testable. Avoid giant conditional functions if small composable pattern handlers are clearer.

## Acceptance criteria

Stage 03 is complete when:

- a public synthetic-data generation entry point exists;
- it consumes the canonical `DashboardSpec` directly;
- generation is reproducible via seed;
- it generates relational SQLite data with valid keys/relationships;
- supported narrative patterns materially shape the underlying data;
- important narrative behaviours are verified deterministically after generation;
- basic financial/reconciliation logic is coherent where required;
- unsupported constraints/requirements are surfaced honestly;
- typed success/failure diagnostics exist;
- the committed Stage 02a live spec can be generated successfully;
- a reviewable `LIVE_DATA_MANIFEST.json` (or equivalent) is committed;
- no credentials or machine-specific secrets are committed;
- the full automated test suite passes;
- implementation, tests, manifest and `REPORT.md` are committed and pushed.

## REPORT.md requirements

The report must include:

- implementation summary;
- files added/changed;
- generator architecture;
- public API/result model;
- seed/reproducibility approach;
- semantic-model planning approach;
- pattern types implemented and how they affect data;
- constraint handling;
- analytical verification approach;
- SQLite structure/output handling;
- Stage 02a live-spec generation result;
- row counts for generated live-spec tables;
- concrete evidence that the requested retail story is visible in generated data;
- tests run and results;
- assumptions/deviations;
- known limitations;
- recommended next stage.

The recommended next stage should explicitly assess readiness to reconnect the generated spec + data to the salvaged PBIP/TMDL/PBIR/Fabric deployment baseline.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
