# Stage 10 — Rapid Product Dashboard Readiness

## Purpose

Prepare the generator for a deliberately minimal-prompt Product dashboard challenge.

**Do not build a Product dashboard in this stage. Do not create a Product mockup. Do not assume the eventual Product dashboard composition.** The next instruction will intentionally provide very little implementation guidance and may provide a visual reference only at execution time.

The purpose of this stage is to make the existing system capable of responding accurately and quickly when that instruction arrives.

## Product goal

Stages 08 and 09 proved that the premium dashboard language and reusable template system can generalise across Financial and Customer domains. The next test changes the optimization target:

> Can the system produce another accurate, visually consistent, reference-led dashboard from a very small prompt, using only the existing template library, in approximately five minutes or less?

This is a readiness/performance stage, not another dashboard-design stage.

## Priority order

Optimize in this order:

1. **Accuracy** — correct measures, dimensions, bindings, labels, formats and visual semantics.
2. **Timeliness** — eliminate unnecessary implementation/deployment steps and target an end-to-end execution time of **<5 minutes** once the next dashboard instruction is received.
3. **Consistency** — preserve the established Executive / Financial / Customer visual language automatically.
4. **Minimal prompting** — infer aggressively from the existing architecture, semantic model and supplied reference rather than requiring detailed implementation instructions.
5. **Reuse** — the eventual challenge must use the **existing registered templates only**. No new visual template should be required to complete it.

Do not trade correctness for speed. A fast dashboard with wrong bindings or misleading analytical semantics is a failure.

## Strict scope

This stage must NOT:

- build or deploy the Product dashboard;
- create or inspect a Product-specific visual reference;
- add a Product-specific template;
- add Product-specific rendering branches;
- pre-design the exact eventual Product page;
- hard-code expected Product metrics or visual positions solely to game the next task;
- ask the user what the Product dashboard should contain.

Prepare **generic capability**, not the answer to the future challenge.

## Read first

Review:

- `KIRO.md`;
- Stage 07d-b custom visual delivery findings;
- Stage 07e / Stage 08 implementation architecture;
- Stage 08 Financial TASK/REPORT;
- Stage 09 Customer TASK/REPORT;
- the current template registry, template builder, design tokens, PBIR renderer, semantic-model inspection utilities, deployment scripts and headless screenshot pipeline.

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

Make the eventual dashboard execution capable of discovering relevant fields and measures quickly from the current semantic model.

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

## 4. Rapid page composition

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

## 5. Preserve established theme automatically

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

## 6. Reference-led layout mapping

Prepare a lightweight process for translating a supplied mockup/reference into the compact page specification using only existing templates.

The process should infer:

- number of major rows/regions;
- approximate grid proportions;
- KPI count;
- hero vs secondary visual hierarchy;
- nearest existing template for each reference visual;
- titles/labels where obvious;
- which details are decorative versus analytically meaningful.

The objective is not pixel-perfect computer vision. It is to let the implementation move from reference + short prompt to an accurate page spec rapidly.

Do not prepare against any Product-specific image in this stage.

## 7. Fast deployment path

Profile the current build -> PBIR generation -> Fabric REST deployment -> first headless render path.

Remove avoidable waits and duplicated work without weakening reliability.

Record timings for at least:

- semantic inspection;
- page-spec construction/validation;
- PBIR generation;
- REST create/update;
- first successful headless render;
- screenshot capture.

Use sensible polling rather than fixed sleeps where possible.

Do not optimize by skipping validation that prevents incorrect reports.

## 8. Preflight validation

Before deployment, a compact page spec should be validated automatically for at least:

- template ID exists;
- all required data roles are bound;
- referenced fields/measures exist;
- data types are compatible with template roles;
- no duplicate/invalid visual IDs;
- visuals stay within canvas bounds;
- obvious overlaps are rejected unless intentional;
- number formats are plausible;
- no domain-specific renderer code was introduced.

A failed preflight should be faster than deploying a broken report.

## 9. One generic rehearsal — not Products

Run at least one timed rehearsal using an already-known page or a neutral synthetic page configuration.

Do **not** use a Product dashboard for the rehearsal.

The rehearsal should test the mechanics of:

compact request/spec -> existing templates -> validation -> PBIR -> Fabric deployment -> headless populated screenshot.

Measure elapsed wall-clock time and identify the remaining bottleneck.

Target **<5 minutes** end to end on the existing environment. If the environment itself makes that impossible, report the measured lower bound and exactly why.

## 10. Accuracy regression

Ensure readiness changes do not damage the already accepted dashboards.

At minimum verify:

- Executive still builds;
- Financial still builds;
- Customer still builds;
- private custom visuals remain zero-touch;
- template registrations are unchanged or backward compatible;
- existing tests remain green.

## Anticipated next instruction

The system should be ready to receive something approximately as terse as:

> Prepare a Product dashboard looking like this mockup, using the existing templates only, matching the theme of the previous dashboards. Complete and deploy it in under five minutes.

This sentence is provided only to define the **interface and performance expectation**. It is not permission to build the dashboard now or infer the unseen mockup.

When that instruction arrives, the desired behaviour is:

1. inspect the supplied reference;
2. infer the page composition aggressively;
3. inspect available semantic-model fields/measures;
4. map reference regions to existing templates;
5. create a compact page spec;
6. validate it;
7. generate/deploy;
8. capture first populated screenshot;
9. report elapsed time and any accuracy compromises;
10. avoid clarification unless a missing fact makes a correct dashboard impossible.

## Acceptance criteria

Stage 10 readiness is complete only when:

- [ ] No Product dashboard has been built or pre-designed.
- [ ] No Product-specific template or renderer branch has been added.
- [ ] Existing template capabilities/data roles are machine-readable or otherwise rapidly discoverable.
- [ ] A compact configuration-driven page specification can assemble a dashboard without bespoke per-domain visual-building code.
- [ ] Semantic-model discovery supports rapid, accurate binding decisions.
- [ ] Preflight catches invalid templates/bindings before deployment.
- [ ] Existing Executive, Financial and Customer pages still build correctly.
- [ ] Zero-touch private custom visual packaging remains intact.
- [ ] A non-Product timed rehearsal reaches <5 minutes end-to-end, or the report provides measured evidence of the irreducible blocker.
- [ ] The system is demonstrably ready to execute the anticipated terse instruction without additional implementation guidance.

## REPORT.md

Create `docs/stages/10-product-dashboard-readiness/REPORT.md` containing:

- readiness architecture changes;
- existing template inventory/capabilities;
- semantic discovery approach;
- compact page-spec format;
- validation rules;
- deployment-path optimizations;
- before/after timing breakdown;
- timed non-Product rehearsal result;
- regression results for Executive/Financial/Customer;
- confirmation that no Product-specific implementation was created;
- remaining risks to the <5-minute target;
- exact recommended wording for the eventual minimal Product dashboard instruction;
- conclusion: `READY_UNDER_5_MIN`, `READY_WITH_TIMING_RISK`, or `NOT_READY`.

The primary success metric for this stage is **repeatability with minimal prompting while preserving accuracy and the accepted premium visual language**.
