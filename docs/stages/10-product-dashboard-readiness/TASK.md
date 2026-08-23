# Stage 10 — Rapid Product Dashboard Readiness

## Purpose

Prepare the generator for a deliberately minimal-prompt Product dashboard challenge.

**Do not build a Product dashboard in this stage. Do not create a Product mockup. Do not assume the eventual Product dashboard composition.** The next instruction will intentionally provide very little implementation guidance and may provide a visual reference only at execution time.

The purpose of this stage is to make the existing system capable of responding accurately and quickly when that instruction arrives.

## Product goal

Stages 08 and 09 proved that the premium dashboard language and reusable template system can generalise across Financial and Customer domains. The next test changes the optimization target:

> Can the system produce another accurate, visually consistent, reference-led dashboard from a very small prompt, using only the existing template library, in approximately five minutes or less?

The timed challenge should cover the **whole generated BI artifact where needed**, including semantic-model construction, not merely report-page composition.

This is a readiness/performance stage, not another dashboard-design stage.

## Priority order

Optimize in this order:

1. **Accuracy** — correct tables, relationships, measures, dimensions, bindings, labels, formats and visual semantics.
2. **Timeliness** — eliminate unnecessary implementation/deployment steps and target an end-to-end execution time of **<5 minutes** once the next dashboard instruction is received.
3. **Consistency** — preserve the established Executive / Financial / Customer visual language automatically.
4. **Minimal prompting** — infer aggressively from the available source schema/data, existing architecture, semantic model and supplied reference rather than requiring detailed implementation instructions.
5. **Reuse** — the eventual challenge must use the **existing registered visual templates only**. No new visual template should be required to complete it.

Do not trade correctness for speed. A fast dashboard with wrong relationships, measures, bindings or misleading analytical semantics is a failure.

## Strict scope

This stage must NOT:

- build or deploy the Product dashboard;
- create or inspect a Product-specific visual reference;
- add a Product-specific visual template;
- add Product-specific rendering branches;
- pre-design the exact eventual Product page;
- hard-code expected Product metrics or visual positions solely to game the next task;
- pre-create a Product-specific semantic model solely to game the next task;
- ask the user what the Product dashboard should contain.

Prepare **generic capability**, not the answer to the future challenge.

## Read first

Review:

- `KIRO.md`;
- Stage 07d-b custom visual delivery findings;
- Stage 07e / Stage 08 implementation architecture;
- Stage 08 Financial TASK/REPORT;
- Stage 09 Customer TASK/REPORT;
- the current template registry, template builder, design tokens, PBIR renderer, semantic-model inspection/construction utilities, deployment scripts and headless screenshot pipeline.

Extract what made Financial and Customer slow or manual and remove avoidable friction generically.

## 1. Freeze the existing visual vocabulary

Inventory the templates that already exist and make them easy for a future minimal-prompt execution to select without editing their source.

At minimum document/encode for every registered template:

- intended analytical use;
- required and optional data roles;
- compatible field/measure types;
- expected number of series/categories;
- formatting/configuration options;
- suitable page roles (KPI, hero, breakdown, ranking, composition, insight, etc.);
- known limitations.

The next dashboard must be achievable by **composition and configuration of this existing vocabulary**.

Do not add new visual templates during the eventual timed challenge.

## 2. Make template selection fast and deterministic

Create or improve a generic selection layer so a requested/reference visual can be mapped rapidly onto an existing template.

Examples of semantic intent that should map without bespoke code:

- headline metric -> premium KPI;
- trend over ordered/time dimension -> existing trend/area/line-capable template;
- categorical comparison/ranking -> bar/column template;
- composition/share -> donut template;
- narrative observations -> insights template;
- center statistic overlay -> existing overlay template where appropriate.

Selection must be based on analytical/visual intent, not domain words such as `Product`, `Customer` or `Financial`.

If an exact visual in a future mockup is unavailable, choose the closest analytically valid existing template rather than building a new one.

## 3. Semantic-model discovery

Make the eventual dashboard execution capable of discovering relevant fields and measures quickly from an existing semantic model when one is already suitable.

The readiness layer should expose enough metadata to answer rapidly:

- available entities/tables;
- measures and their expressions/formats where accessible;
- dimensions and data types;
- likely date fields;
- likely categorical fields;
- numeric measures;
- existing relationships;
- whether a requested/reference binding is actually supportable.

Prefer existing real measures. If a genuinely required measure is absent, creation should be minimal, deterministic and semantically justified.

Do not silently proxy unrelated measures merely to populate a visual.

## 4. Rapid semantic-model construction

Prepare a **generic model-construction path** for cases where the eventual minimal prompt/reference requires data or metrics that are not already represented by a suitable semantic model.

The generator should be able to move rapidly from available source schema/data into a valid Power BI semantic model without requiring a long modeling prompt.

The path should support, where applicable:

- identifying likely fact and dimension tables;
- selecting business keys and relationship keys;
- inferring one-to-many relationship direction conservatively;
- identifying/creating a canonical Date dimension when time analysis is required;
- converting date-like strings into real date columns rather than leaving them analytically disconnected;
- creating required relationships to Date and other dimensions;
- deriving measures from source columns rather than embedding computed values in visuals;
- assigning appropriate data types, formats and summarization behaviour;
- generating TMDL/model definitions deterministically;
- deploying/refreshing the semantic model through the existing Fabric-compatible path;
- verifying that measures evaluate and visual bindings resolve before report deployment.

This must remain generic. Do not implement Product-specific table names, measures or formulas during readiness.

### 4.1 Fact/dimension inference

Implement or document a fast heuristic/model-assisted approach for classifying source tables/columns, using evidence such as:

- row cardinality;
- repeated vs unique identifiers;
- date columns;
- numeric additive columns;
- categorical attributes;
- foreign-key-like value overlap;
- naming metadata where available.

When confidence is high, infer aggressively. When ambiguity would materially change analytical meaning, fail preflight clearly rather than silently inventing relationships.

### 4.2 Measure inference

Prepare a small generic measure-construction layer capable of creating common analytical measures from source schema and reference intent, for example:

- sums/revenue/value;
- counts/distinct counts;
- averages;
- margins/ratios;
- rates/percentages;
- prior-period comparisons where a valid date relationship exists;
- share-of-total measures;
- rank/top-N support where needed by an existing template.

Measures must be mathematically defensible and based on actual source/model fields.

No unrelated metric proxies.

### 4.3 Model validation

Before report generation, validate at minimum:

- relationship keys exist and are type-compatible;
- expected one-side keys are sufficiently unique;
- no obvious ambiguous relationship loops are introduced;
- required Date relationship exists for time-series/reference visuals;
- measures parse and evaluate;
- formats match semantics;
- requested/reference analytical concepts can actually be supported by the model.

If the supplied source data cannot support an element from the reference, choose the closest accurate representation and report the deviation.

## 5. Rapid page composition

Make page construction configuration-driven enough that a future implementation can be expressed primarily as a compact page specification rather than a bespoke Python deployment script.

Target something conceptually equivalent to:

- page title/subtitle;
- active navigation item;
- filter/slicer configuration;
- visual template IDs;
- positions/sizes;
- bindings;
- titles/labels;
- design-token variants;
- optional content configuration.

The generic renderer should then build the PBIR visual definitions from that compact spec.

Avoid rewriting the same `add_visual()` boilerplate for each new domain.

## 6. Preserve established theme automatically

The future prompt should not need to explain the established theme.

Ensure the default composition automatically inherits the same design system demonstrated by the accepted Executive, Financial and Customer pages:

- dark navy executive canvas;
- left navigation rail;
- established content margins/grid;
- premium surface/panel treatment;
- typography hierarchy;
- accent palette;
- KPI grammar;
- chart chrome;
- spacing/radius conventions;
- filter/header treatment.

A future instruction such as “match the theme of the previous dashboards” should require no manual restyling work.

## 7. Reference-led layout and analytical-intent mapping

Prepare a lightweight process for translating a supplied mockup/reference into both:

1. a compact page specification using only existing templates; and
2. a list of semantic-model requirements needed to support that page accurately.

The process should infer:

- number of major rows/regions;
- approximate grid proportions;
- KPI count;
- hero vs secondary visual hierarchy;
- nearest existing template for each reference visual;
- likely analytical intent of each visual;
- required measures/dimensions/time relationships;
- titles/labels where obvious;
- which details are decorative versus analytically meaningful.

The objective is not pixel-perfect computer vision. It is to let the implementation move from reference + short prompt + available source data to an accurate model and page spec rapidly.

Do not prepare against any Product-specific image in this stage.

## 8. Fast end-to-end deployment path

Profile the full path:

source/schema inspection -> semantic-model plan/construction (if required) -> model deploy/refresh -> page-spec generation -> PBIR generation -> Fabric REST deployment -> first headless render.

Remove avoidable waits and duplicated work without weakening reliability.

Record timings for at least:

- source/schema inspection;
- model inference/validation;
- semantic-model generation/deploy/refresh where required;
- page-spec construction/validation;
- PBIR generation;
- REST create/update;
- first successful headless render;
- screenshot capture.

Use sensible polling rather than fixed sleeps where possible.

Do not optimize by skipping validation that prevents incorrect reports.

## 9. Unified preflight validation

Before deployment, validate both the semantic model and compact page spec.

At minimum check:

### Model
- required entities/columns exist;
- relationship keys/types are valid;
- required Date relationship exists for time analysis;
- measures compile/evaluate;
- measure formats are plausible;
- no obvious ambiguous model structure is introduced.

### Page
- template ID exists;
- all required data roles are bound;
- referenced fields/measures exist;
- data types are compatible with template roles;
- no duplicate/invalid visual IDs;
- visuals stay within canvas bounds;
- obvious overlaps are rejected unless intentional;
- number formats are plausible;
- no domain-specific renderer code was introduced.

A failed preflight should be faster than deploying a broken model/report.

## 10. Generic timed rehearsals — not Products

Run at least one timed rehearsal using an already-known page or neutral synthetic domain configuration.

Do **not** use a Product dashboard for rehearsal.

At least one rehearsal must exercise the **full model + report path**, starting from source-like tabular/schema input rather than relying entirely on an already-perfect semantic model.

The rehearsal should test:

minimal request/reference-like intent -> source/schema inspection -> semantic model inference/construction -> measures/relationships -> existing templates -> validation -> model/report deployment -> headless populated screenshot.

Measure elapsed wall-clock time and identify the remaining bottleneck.

Target **<5 minutes end to end**, including semantic-model creation when required. If the environment itself makes that impossible, report the measured lower bound and exactly why.

A second report-only rehearsal using an existing semantic model may also be used to establish the faster lower-bound path.

## 11. Accuracy regression

Ensure readiness changes do not damage the already accepted dashboards or their models.

At minimum verify:

- Executive still builds;
- Financial still builds;
- Customer still builds;
- their existing semantic bindings remain valid;
- private custom visuals remain zero-touch;
- template registrations are unchanged or backward compatible;
- existing tests remain green.

## Anticipated next instruction

The system should be ready to receive something approximately as terse as:

> Prepare a Product dashboard looking like this mockup, using the existing templates only, matching the theme of the previous dashboards. Build any semantic model required from the available source data. Complete and deploy it in under five minutes.

This sentence is provided only to define the **interface and performance expectation**. It is not permission to build the dashboard now or infer the unseen mockup.

When that instruction arrives, the desired behaviour is:

1. inspect the supplied reference;
2. infer page composition and analytical intent aggressively;
3. inspect available source data/schema and any reusable existing model assets;
4. determine semantic-model requirements;
5. construct/extend the model accurately where required;
6. create required measures and relationships;
7. map reference regions to existing visual templates only;
8. create a compact page spec;
9. run unified preflight validation;
10. deploy/refresh model and report;
11. capture first populated screenshot;
12. report elapsed time and any accuracy/reference compromises;
13. avoid clarification unless a missing fact makes a correct dashboard impossible.

## Acceptance criteria

Stage 10 readiness is complete only when:

- [ ] No Product dashboard has been built or pre-designed.
- [ ] No Product-specific visual template, renderer branch or semantic model has been added.
- [ ] Existing template capabilities/data roles are machine-readable or otherwise rapidly discoverable.
- [ ] A compact configuration-driven page specification can assemble a dashboard without bespoke per-domain visual-building code.
- [ ] Semantic-model discovery supports rapid, accurate reuse of existing models.
- [ ] Generic semantic-model construction can create facts/dimensions/relationships/date handling/measures from source-like input when required.
- [ ] Model validation catches invalid relationships/measures before report deployment.
- [ ] Page preflight catches invalid templates/bindings before deployment.
- [ ] Reference interpretation can produce both a visual page plan and semantic-model requirements.
- [ ] Existing Executive, Financial and Customer pages still build correctly.
- [ ] Zero-touch private custom visual packaging remains intact.
- [ ] At least one non-Product full model+report timed rehearsal reaches <5 minutes end-to-end, or the report provides measured evidence of the irreducible blocker.
- [ ] The system is demonstrably ready to execute the anticipated terse instruction without additional modeling or implementation guidance.

## REPORT.md

Create `docs/stages/10-product-dashboard-readiness/REPORT.md` containing:

- readiness architecture changes;
- existing template inventory/capabilities;
- semantic discovery approach;
- semantic-model construction approach;
- fact/dimension/relationship/date inference rules;
- generic measure inference/construction;
- model validation rules;
- compact page-spec format;
- page validation rules;
- reference-to-model-and-page mapping approach;
- deployment-path optimizations;
- before/after timing breakdown;
- timed non-Product **full semantic-model + report** rehearsal result;
- optional report-only rehearsal result;
- regression results for Executive/Financial/Customer;
- confirmation that no Product-specific implementation or model was created;
- remaining risks to the <5-minute target;
- exact recommended wording for the eventual minimal Product dashboard instruction;
- conclusion: `READY_UNDER_5_MIN`, `READY_WITH_TIMING_RISK`, or `NOT_READY`.

The primary success metric for this stage is **repeatability with minimal prompting across both semantic modeling and premium report generation, while preserving accuracy and the accepted visual language**.
