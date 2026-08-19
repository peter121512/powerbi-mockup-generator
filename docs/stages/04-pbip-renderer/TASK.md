---
stage: 04
status: ready
title: Rich DashboardSpec to deployable PBIP/PBIR renderer
---

# Stage 04 — PBIP/PBIR Generation

## Context

Stages 01–03 now provide the new intelligent front half of the product:

```text
Natural-language requirement
    ↓
AI dashboard designer
    ↓
validated rich DashboardSpec
    ↓
coherent narrative-driven synthetic relational data
```

The missing link is now the actual Power BI artifact.

The repository retains a proven legacy baseline for PBIP/TMDL/PBIR generation and Fabric deployment. This stage must reconnect that capability to the new rich `DashboardSpec` rather than rebuilding Power BI file formats from first principles unnecessarily.

The product goal is not merely to emit syntactically plausible project files. A user prompt must ultimately become a Power BI report that faithfully reflects the designer's analytical structure, visual choices, layout and enterprise design intent.

## Read first

Before changing code:

1. Read `KIRO.md`.
2. Read the Stage 01–03 TASK/REPORT files.
3. Inspect `docs/stages/02a-live-designer-test/LIVE_OUTPUT.json` in full. This is the primary integration fixture.
4. Inspect the current repository's legacy renderer/deployment/template code.
5. Inspect the archived `peter121512/pbi` repository where useful for proven PBIP/PBIR/TMDL structures and prior deployment behaviour.
6. Prefer salvaging known-good Power BI structures over inventing undocumented JSON shapes.
7. Preserve the current Fabric deployment path unless a narrowly scoped compatibility fix is required.

## Objective

Implement a production-shaped renderer that accepts:

- a validated rich `DashboardSpec`; and
- the SQLite dataset generated for that spec;

and produces a complete **Power BI Project (PBIP)** containing a semantic model and report definition suitable for opening/deployment through the existing Power BI/Fabric workflow.

The live Stage 02a retail spec must be rendered as the main end-to-end integration fixture.

Conceptually:

```python
render_powerbi_project(
    spec: DashboardSpec,
    data_path: Path,
    output_dir: Path,
) -> RenderResult
```

Exact naming is an implementation decision.

## Critical acceptance philosophy

**“Files were generated” is not sufficient.**

The renderer must preserve the decisions already made by the designer. The rendered artifact should demonstrably contain:

- all intended pages;
- the intended visuals on those pages;
- correct visual types;
- correct field/measure bindings;
- meaningful layout hierarchy;
- report/page filters and slicers;
- semantic-model relationships;
- DAX measures;
- report theme/design intent;
- navigation/drill-through where supported;
- coherent connection to the generated mock data.

Where Power BI format limitations prevent an exact mapping, use a deliberate documented fallback rather than silently dropping the intent.

## Required capabilities

### 1. Explicit renderer boundary

Create a clear public renderer service/API returning a typed result.

The caller must be able to distinguish:

- success;
- invalid input/spec;
- unsupported visual or feature mapping;
- semantic-model render failure;
- report render failure;
- output validation failure.

Do not require callers to infer outcome from arbitrary exceptions or console text.

### 2. PBIP project structure

Generate a valid project directory with the required `.pbip`, report, and semantic-model structure expected by Power BI Project format.

Reuse known-good project metadata/version declarations from the proven baseline where appropriate.

Do not add generated transient/cache files to Git.

### 3. Semantic model generation

Generate the semantic model from `spec.semantic_model` and the Stage 03 SQLite data.

At minimum render:

- every required table;
- every required column with sensible data type;
- hidden/key metadata where appropriate;
- relationships from `RelationshipSpec`;
- measures from `MeasureSpec` using the supplied DAX expressions;
- measure format strings;
- table/column metadata needed for visual field resolution;
- a working data-source/partition strategy compatible with the project's deployment path.

Prefer TMDL if that matches the proven baseline and current project format.

The renderer must not re-infer the semantic model independently. `DashboardSpec` is canonical.

### 4. Data-source integration

The generated project must have a practical path to consume the Stage 03 data.

Inspect the legacy deployment architecture and choose the simplest robust mechanism compatible with Power BI/Fabric deployment. If direct SQLite ingestion is not supported by the existing deployment path, introduce a narrowly scoped conversion/staging step rather than compromising the semantic contract.

Document exactly how generated data reaches the semantic model.

The eventual deployed mockup must not depend on a developer-machine-only absolute path that Fabric cannot access.

### 5. Page generation

Create every `PageSpec` from the canonical spec.

Preserve:

- page title/name;
- page role where representable as metadata;
- canvas width/height;
- page order;
- visual membership;
- drill-through target semantics where supported;
- tooltip-page semantics where supported.

For the live retail fixture this means all four pages must render: Executive Overview, Regional Analysis, Category Analysis and Risk Analysis.

### 6. Layout translation

Translate the designer's logical grid positions into Power BI canvas coordinates deterministically.

Requirements:

- respect each page's declared canvas dimensions;
- support varying `grid_columns` / `grid_rows` rather than assuming one hard-coded grid;
- preserve relative hierarchy and grouping;
- avoid overlaps for valid source specs;
- make priority-1 visuals visually prominent where the source layout intends that;
- use stable deterministic coordinates across repeated renders.

Do not redesign the page randomly during rendering. Rendering should faithfully execute the design spec.

### 7. Visual mapping layer

Implement an explicit mapping from canonical `VisualType` values to Power BI visual configurations.

Prioritise the visual types used by the live fixture and common executive dashboards, including at minimum:

- card/KPI-style visual;
- line chart;
- clustered bar/column chart;
- table/matrix as applicable;
- slicer;
- map if the proven PBIR structure is available and robust;
- scatter chart;
- donut chart;
- navigation/button where specified.

If a canonical visual is unsupported, the renderer must either:

1. apply a documented analytically sensible fallback; or
2. return a typed unsupported-feature diagnostic.

Never silently omit a requested visual.

### 8. Field bindings

Translate every `FieldRef` into valid Power BI query/projection bindings.

Support:

- columns;
- measures;
- category fields;
- value fields;
- series/legend fields;
- aggregations where applicable;
- sort definitions;
- tooltip fields where supported.

Add deterministic validation that rendered visual references correspond to generated semantic-model objects.

### 9. Filters and slicers

Render report/page/visual filters and slicers represented by the spec where supported.

For the live fixture, period, region and category filtering must not disappear during rendering.

Where the source spec expresses a filter concept that requires a different Power BI representation, document the mapping.

### 10. Interactions, navigation and drill-through

Implement the highest-value interaction semantics supported by the known-good PBIR format:

- cross-filter/highlight defaults;
- drill-through page targets;
- page navigation buttons;
- tooltip page references where present.

Do not spend the entire stage reverse-engineering obscure interaction metadata. Prioritise correctness of the primary report experience and document unsupported interaction details explicitly.

### 11. Theme generation

Translate `ThemeSpec` / design-system intent into a Power BI report theme or equivalent report-level formatting configuration.

At minimum preserve:

- primary/accent/positive/negative/neutral colour roles;
- heading/body typography where supported;
- restrained corporate visual defaults;
- backgrounds and card styling where supported;
- consistency across pages.

The live fixture's `corporate_restrained`, premium boardroom-ready intent should be visible in the generated report configuration, not merely stored in unused metadata.

Do not hard-code the retail fixture's colours as global renderer defaults. Theme comes from the spec.

### 12. Enterprise visual formatting

Apply sensible formatting defaults consistent with the spec and the product quality bar:

- readable titles;
- restrained borders/backgrounds;
- consistent spacing;
- sensible data-label use;
- appropriate number formats;
- uncluttered legends/axes;
- accessible contrast;
- no gratuitous visual chrome.

Formatting should be systematic and driven by visual type + design intent rather than dozens of fixture-specific hacks.

### 13. Live fixture integration render

Render `docs/stages/02a-live-designer-test/LIVE_OUTPUT.json` using a dataset generated by Stage 03.

Commit a lightweight render manifest under the Stage 04 directory containing at minimum:

- project name/path;
- pages rendered;
- visual count by page/type;
- measures rendered;
- relationships rendered;
- theme mapping summary;
- warnings/fallbacks;
- structural validation results.

Do not commit large generated database/cache/transient artifacts unless there is a strong reason.

If generated PBIP text files are reasonably sized and useful as a regression fixture, committing the live rendered project under `docs/stages/04-pbip-renderer/live-project/` is encouraged. Avoid committing machine-specific paths or secrets.

### 14. Structural output validation

Implement deterministic post-render validation.

At minimum verify:

- required PBIP/report/model files exist;
- generated JSON files parse;
- TMDL/model files contain expected tables/measures/relationships;
- page count matches the spec;
- no source visual has silently disappeared;
- every rendered visual has a supported type/fallback recorded;
- expected visual field references resolve;
- visual positions are within canvas bounds;
- theme artifact/config is present;
- no absolute local credential/path leakage exists.

Where practical, use official/local Power BI tooling to validate project structure. If unavailable, document that limitation rather than claiming Power BI acceptance without evidence.

### 15. Fidelity manifest

Produce a machine-readable mapping/fidelity report for each render.

For every page and visual record whether it was:

- rendered exactly;
- rendered with fallback;
- unsupported/failed.

Include important feature mappings such as filters, drill-through and navigation.

This is essential for later critic/revision stages: we need to know whether a visual-quality problem came from the designer or from renderer lossiness.

### 16. Determinism

Given the same spec, dataset and renderer version, generated project text/configuration should be deterministic apart from unavoidable generated identifiers/timestamps.

Prefer stable IDs derived from canonical page/visual IDs where Power BI permits it.

## Live retail quality bar

The generated project for the live fixture should structurally represent:

### Executive Overview
- four headline KPI cards;
- revenue trend with appropriate time axis;
- regional/category comparisons;
- period, region and category filtering;
- clear executive hierarchy.

### Regional Analysis
- regional KPIs;
- geographic/comparison view;
- trend/breakdown analysis.

### Category Analysis
- category KPIs;
- contribution/mix view;
- category trend and comparison analysis.

### Risk Analysis
- risk KPIs;
- risk matrix/scatter where supported;
- detailed risk tables;
- strong negative/underperformance emphasis.

The renderer should preserve the analytical story rather than flattening all pages into generic charts.

## Tests

Add meaningful automated tests covering at minimum:

1. PBIP project skeleton creation;
2. semantic table rendering;
3. column type mapping;
4. measure/DAX rendering;
5. relationship rendering;
6. page generation and ordering;
7. grid-to-canvas layout translation;
8. visual mapping for each priority visual type;
9. column and measure field bindings;
10. filters/slicer mapping;
11. theme generation;
12. unsupported visual behaviour/fallback diagnostics;
13. no silent visual loss;
14. output structural validation;
15. deterministic repeated render;
16. full Stage 02a `LIVE_OUTPUT.json` integration render;
17. all existing Stage 01–03 tests remaining green.

Tests must not require Fabric credentials or a live Power BI tenant.

## Practical Power BI validation

If Power BI Desktop, PBIP validation tooling, Fabric APIs, or another existing local validation route is available in the development environment, perform the strongest practical validation possible without turning this stage into deployment work.

If the artifact can be opened/parsed/imported locally, do so.

If that is impossible in the current environment, explicitly distinguish:

- structurally validated by our renderer; from
- actually accepted/rendered by Power BI.

Do not claim the latter without evidence.

## Non-goals

Do NOT expand this stage into:

- conversational amendment/revision;
- screenshot/vision critique;
- full Fabric deployment orchestration rewrite;
- every Power BI custom visual;
- pixel-perfect reproduction of every Power BI formatting property;
- mobile layouts;
- RLS/security modelling;
- production-scale data ingestion;
- external user UI.

The goal is the first faithful, deployable Power BI artifact from the new intelligent pipeline.

## Architecture expectation

Prefer explicit layers conceptually similar to:

```text
PowerBIRenderer
    ├── project writer
    ├── semantic-model/TMDL renderer
    ├── data-source adapter
    ├── report/PBIR renderer
    │      ├── page renderer
    │      ├── layout translator
    │      ├── visual registry/mappers
    │      ├── field-binding builder
    │      ├── filter/interaction mapper
    │      └── formatting/theme mapper
    ├── structural validator
    └── fidelity manifest
```

Keep Power BI format-specific mechanics out of the canonical domain models.

## Salvage principle

This project already proved that Power BI artifacts could be generated and published. Use that evidence.

Before implementing any PBIR/TMDL structure from scratch:

1. search the current repo;
2. inspect the archived `peter121512/pbi` repo;
3. identify known-good templates/examples;
4. adapt them behind the new renderer boundary.

The rebuild should improve the intelligence and maintainability of the system, not discard working Power BI format knowledge.

## Acceptance criteria

Stage 04 is complete when:

- a public rich-spec-to-PBIP renderer exists;
- the Stage 02a live retail spec renders end-to-end with Stage 03 data;
- the generated project contains all four pages and all source visuals or explicit documented fallbacks;
- semantic tables, relationships and DAX measures are generated from the canonical spec;
- visual types and field bindings are mapped deterministically;
- logical grid layout becomes valid Power BI canvas layout;
- filters/slicers survive rendering;
- design/theme intent materially affects report formatting;
- deterministic post-render validation passes;
- a machine-readable fidelity manifest is generated;
- no secrets or developer-machine-only paths leak into committed artifacts;
- all existing tests remain green;
- new Stage 04 tests pass;
- a live integration render has been performed and documented;
- all intended changes are committed and pushed;
- `docs/stages/04-pbip-renderer/REPORT.md` is created and committed.

## REPORT.md requirements

Include:

- implementation summary;
- files added/changed;
- renderer architecture;
- legacy/archived components salvaged and how they were adapted;
- PBIP project structure generated;
- semantic-model/TMDL strategy;
- data-source strategy;
- visual mapping table (canonical → Power BI → fallback if any);
- field-binding approach;
- layout translation approach;
- filter/interaction support;
- theme/formatting mapping;
- structural validation performed;
- live retail integration result with exact page/visual counts;
- fidelity/fallback summary;
- automated test results;
- any actual Power BI acceptance/open/deployment validation performed, clearly separated from internal structural validation;
- defects/fixes discovered during integration;
- known limitations;
- recommended next stage.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
