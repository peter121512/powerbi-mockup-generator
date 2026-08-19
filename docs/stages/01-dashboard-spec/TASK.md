---
stage: 01
status: ready
title: Rich dashboard specification foundation
---

# Stage 01 — Rich Dashboard Specification Foundation

## Context

This project is being rebuilt from the earlier `pbi_gen` prototype. The legacy backend already proved the following execution path:

- natural-language prompt
- dashboard specification
- mocked data generation
- PBIP/TMDL/PBIR generation
- deployment to Fabric / Power BI Service
- dataset refresh
- screenshot capture
- vision-based QA
- conversational refinement and redeployment

The objective of this stage is NOT to rebuild deployment. The objective is to create a much stronger internal dashboard specification that can support enterprise-grade visual design, functionality, iterative amendments, and future quality evaluation.

The product goal for Phase 1 is:

> A natural-language prompt should ultimately result in a genuinely impressive Power BI dashboard deployed to Power BI Service using mocked data. The dashboard should be credible for demonstration to a C-suite audience. Users should then be able to refine the same dashboard through follow-up CLI prompts.

The dominant Phase 1 quality priorities are:

1. visual layout and information hierarchy;
2. appropriateness of visual type for the analytical task;
3. useful filters and report interactions;
4. exceptionally polished enterprise-grade aesthetics;
5. preservation of dashboard identity across revisions.

Data-model optimisation is secondary in Phase 1. The model only needs to be good enough to support the intended visuals and interactions reliably. Deeper semantic-model optimisation belongs to Phase 2.

## Read first

Before changing code:

1. Read `KIRO.md` and follow it as the standing operating instruction.
2. Read `README.md` for project direction.
3. Read `docs/legacy/PBI_BACKEND_BASELINE.md`.
4. Inspect the current `src/pbi_gen/models/schema.py`.
5. Inspect the source repository `peter121512/pbi` if available locally or through GitHub, especially:
   - `src/pbi_gen/models/schema.py`
   - `src/pbi_gen/llm/bedrock.py`
   - `src/pbi_gen/templates/pbip.py`
   - `src/pbi_gen/db/sqlite_gen.py`
   - `src/pbi_gen/core/cli.py`

Do not copy the old schema blindly. Treat it as evidence of what already worked and of what proved too limited.

## Stage objective

Design and implement the new canonical `DashboardSpec` model that will become the contract between future designer, data-generation, rendering, deployment, critique, and revision components.

This stage should remain deliberately focused on the specification layer. Do not build the full designer agent or rewrite the renderer yet.

## Required capabilities

The new specification must support the following concepts explicitly.

### 1. Dashboard-level intent

Represent at minimum:

- dashboard/report title;
- business purpose / analytical objective;
- intended audience;
- inferred business domain;
- assumptions made by the system;
- confidence / uncertainty information sufficient for a later clarification gate;
- design intent / visual tone.

Do not implement a fake arbitrary confidence percentage. Model the underlying confidence dimensions or evidence so a later deterministic confidence score can be derived.

### 2. Multi-page report structure

The old spec effectively treated the report as one flat list of visuals. Replace that with explicit pages.

Each page must be able to describe:

- page ID / stable identity;
- page title;
- page purpose;
- page role, e.g. executive overview, diagnostic, detail, drill-through;
- layout dimensions or grid system;
- ordered visuals;
- page-level filters / slicers;
- navigation where relevant.

Stable identifiers matter because later user amendments must modify the same dashboard rather than regenerate unrelated artifacts.

### 3. Rich visual specification

A visual must represent more than type/title/fields. It should support at minimum:

- stable visual ID;
- visual type;
- title and optional subtitle;
- analytical purpose / question answered;
- field / measure bindings;
- position and size;
- visual priority / hierarchy;
- formatting intent;
- sort intent;
- conditional-formatting intent where relevant;
- tooltip intent;
- interaction behaviour;
- accessibility / alt-description metadata where practical.

Do not hard-code all Power BI JSON formatting details into the spec. The spec should describe design intent and semantics; the renderer should later translate that intent into PBIR/PBI configuration.

### 4. Interaction and filter model

Model report functionality explicitly, including concepts such as:

- slicers;
- page filters;
- report filters;
- cross-filter / cross-highlight behaviour;
- drill-through targets;
- tooltip pages or enhanced tooltip intent;
- page navigation / buttons where applicable.

The schema should be extensible rather than tied only to the handful of visual types supported by the legacy renderer.

### 5. Theme / design system intent

The dashboard should be able to carry structured design intent such as:

- light/dark or other presentation mode;
- enterprise style family;
- colour roles / semantic colour intent;
- typography hierarchy;
- density / whitespace preference;
- card / surface treatment;
- emphasis rules.

Avoid embedding one fixed navy theme into the schema. The whole point is to allow future designer logic to choose an appropriate polished design system while retaining consistency across pages.

### 6. Analytical / data support

Retain enough of the legacy data-model concepts for the existing generator to remain usable later:

- tables;
- columns;
- relationships;
- measures;
- field references;
- mock data requirements.

However, improve typing and structure where useful. The spec should be capable of expressing which data patterns are required to make the intended dashboard story visible, e.g. trend, seasonality, ranking, variance, outlier, target miss, concentration, funnel progression.

The mocked-data specification should be about analytical behaviour/story, not merely arbitrary random-value ranges.

### 7. Revision metadata

Support future conversational iteration by including enough metadata to distinguish:

- dashboard identity;
- specification version;
- parent / prior version where relevant;
- amendment summary or revision reason;
- immutable stable IDs for pages and visuals where unchanged.

Do not build persistence infrastructure in this stage; just make the schema capable of supporting it.

## Implementation guidance

Prefer explicit typed Python models over loosely structured dictionaries. Pydantic is acceptable and likely preferable if justified because later LLM structured output and schema validation will benefit from it. If adopting Pydantic, update project dependencies appropriately and explain the decision in the report.

The schema should be serializable to and from JSON cleanly.

Provide sensible enums / constrained types for concepts that have a bounded vocabulary, while leaving extension points for future Power BI visual types.

Avoid premature abstraction. The goal is a strong canonical domain model, not a generic BI framework.

Compatibility with every old function is NOT required in this stage. However, do not casually break the imported Fabric deployment baseline. Any deliberate incompatibility with the legacy renderer/data generator must be documented clearly for the next stage.

## Tests

Add focused tests covering at minimum:

1. construction of a realistic multi-page executive dashboard spec;
2. JSON serialization and round-trip deserialization;
3. validation failure for clearly invalid specs, e.g. duplicate IDs, invalid dimensions, broken field references where validation can reasonably detect them;
4. revision metadata preserving stable page/visual IDs;
5. confidence / uncertainty representation;
6. interaction/filter structures;
7. mocked-data narrative/pattern requirements.

Tests should demonstrate the model rather than merely chase line coverage.

## Example target scenario

Use a scenario at least as rich as:

> Create an executive retail performance dashboard for a UK retailer. The primary audience is the CEO and CFO. Show revenue, gross margin, YoY growth, regional performance, product/category performance and major underperformance risks. It should feel premium, restrained and boardroom-ready. Include useful filters for period, region and category.

A valid example spec should be able to represent an executive overview plus at least one deeper-analysis page, appropriate visual choices, filters/interactions, design intent and a mocked-data story containing meaningful trends/variance.

The example is illustrative. Do not build the actual AI designer in this stage.

## Non-goals

Do NOT spend this stage on:

- Android UI;
- web UI;
- Fabric authentication redesign;
- full semantic-model optimisation;
- direct PBIR rendering changes;
- full synthetic data rewrite;
- agent framework adoption;
- building multiple autonomous agents;
- screenshot/vision quality improvements.

Those come after the contract is strong enough to support them.

## Learning objective

This stage should make the architecture understandable in terms of agentic AI rather than hiding everything behind framework magic. In the `REPORT.md`, explain briefly:

- why a typed intermediate state is useful between probabilistic LLM reasoning and deterministic tooling;
- which fields should be generated/reasoned about by an LLM versus validated/derived deterministically;
- how this schema will allow later agents/functions to communicate without passing arbitrary prose.

Keep this explanation practical and tied to the code implemented.

## Acceptance criteria

The stage is complete when:

- a materially richer canonical DashboardSpec exists;
- the model supports pages, layout, visuals, filters/interactions, design intent, confidence/assumptions, mocked-data narrative requirements and revision identity;
- it can be serialized/deserialized reliably;
- representative tests pass;
- no secrets or environment-specific config are committed;
- scope has not expanded into renderer/designer implementation;
- the implementation is committed and pushed;
- `docs/stages/01-dashboard-spec/REPORT.md` is created and committed.

## REPORT.md requirements

The report must include:

- implementation summary;
- files added/changed;
- final schema structure and key design decisions;
- dependencies added/changed;
- tests run and results;
- compatibility implications for the salvaged legacy renderer/data generator;
- known limitations;
- recommended next stage;
- the short agentic-learning explanation described above;
- any assumptions or deviations from this task.

Do not edit this TASK.md to mark completion. The REPORT.md is the completion record.
