# Stage 11 — Minimal-Prompt Product Dashboard Challenge

## Instruction

Prepare and deploy a **Product Performance** dashboard using this reference as the desired composition:

`docs/stages/11-product-dashboard/product-dashboard-reference.svg`

Use **existing registered templates only**. Do **not** create, modify or rebuild any visual template for this stage.

Match the established theme and visual language of the existing Executive, Financial and Customer dashboards.

Build any semantic-model additions required from the available source data, but do not proxy unrelated measures simply to populate the page.

Target **under five minutes end-to-end** from start of execution to first populated headless screenshot.

## What is actually being evaluated

This is **not** a pixel-perfect image reproduction test and the reference must not be treated as if arbitrary HTML/SVG drawing capabilities are available.

The principal visual/accuracy evaluation is:

> **How closely can the generator reproduce the analytical intent, information hierarchy, layout and visual character of the supplied mockup using only the visual templates and capabilities that already exist in `docs/TEMPLATE_INVENTORY.md`?**

Therefore evaluate fidelity **within the feasible envelope of the existing template library**.

A visually different implementation is not automatically a failure when the difference is caused by a documented limitation of an existing template. Conversely, a poor choice or poor configuration of an available template **is** a failure when the inventory already contained a materially closer option.

Do not create new capabilities to improve the score.

## Priority order

1. **Semantic and numerical accuracy** — every metric, category, relationship and measure must mean what its label says.
2. **Best achievable reference fidelity with existing templates** — choose and configure the closest available template for each reference region.
3. **Consistency with the accepted Executive / Financial / Customer dashboard theme.**
4. **Speed** — target <5 minutes for the full run.

Accuracy takes priority over literal mockup values and over speed.

## Reference intent

The reference deliberately stays close to patterns already demonstrated by the current dashboard system:

- established left navigation with Products active and **no left-side filter stack**;
- compact top-right slicers;
- four simple headline KPI cards, with **no delta/up-arrow row required**;
- a large trend hero using the existing trend capability;
- a donut composition visual paired with the existing `donut_center_kpi` overlay;
- three lower-row categorical/ranking visuals using existing bar/column capabilities;
- the same dark navy surfaces, blue/purple accents, typography hierarchy, spacing and chart chrome used by the accepted dashboards.

The intended donut concept is **Product Mix by Category**, with the centre KPI showing **total/active product count**. This is specifically chosen because the existing inventory already supports `premium_donut` + `donut_center_kpi`. If the source/model supports a better semantically valid product-mix measure, use it and document the choice.

The illustrative numbers and names in the reference are not ground truth.

## Constraints

- Use only capabilities already documented in `docs/TEMPLATE_INVENTORY.md`.
- No new custom visual or new template family.
- No edits to existing template source solely to improve this dashboard.
- No Product-specific renderer branch.
- No manual Power BI Desktop step.
- No manual editor rebinding.
- Use the proven zero-touch private custom-visual packaging path.
- Infer aggressively from the reference and model/source data.
- Do not ask for clarification unless a correct dashboard is impossible without a missing fact.
- If an exact reference element cannot be represented with an existing template, choose the closest analytically valid existing template and record the deviation.

## Semantic model

Use the Stage 10 rapid engine and semantic discovery/model-construction path.

If the required Product model already exists and is valid, reuse it. If source data requires extension or a new table/model element, infer and create the minimum correct structure needed for the dashboard, including where relevant Product/category/brand dimensions, sales facts, date relationships and valid measures.

Do not invent unsupported financial fields. If source data cannot support a KPI shown in the mockup, substitute the closest high-value Product KPI supported by real data and document the substitution.

## Timing

Instrument actual wall-clock timings for source/model inspection, semantic-model construction/update, page-spec generation, preflight validation, PBIR generation, deployment/refresh, headless render/screenshot and total elapsed time.

Do not skip validation or hide errors to claim a faster runtime.

## Validation

Before declaring completion verify that every visual is populated from valid fields/measures; every label accurately describes its measure; rankings are correctly sorted; the trend uses a genuinely ordered/date-capable axis; margin is mathematically valid if displayed; slicers bind to relevant Product data; report loads with zero manual interaction; no visual is out of bounds; and no new visual template/source implementation was added.

## Achievable-fidelity evaluation

In `REPORT.md`, score the result in two separate dimensions rather than conflating them:

### A. Semantic accuracy — /100
Judge correctness of model, measures, bindings, labels, filtering and analytical meaning.

### B. Existing-template reference fidelity — /100
Judge the deployed screenshot against the reference **only after accounting for the documented capabilities/limitations of the existing templates**. Score:

- page structure / geometry / hierarchy — 25;
- correct nearest-template selection — 20;
- established theme / surfaces / typography / spacing — 20;
- KPI row fidelity within `premium_kpi` capability — 10;
- hero trend fidelity within `premium_trend` capability — 10;
- donut + centre KPI composition within existing capabilities — 10;
- lower-row ranking/comparison fidelity — 5.

For every material mismatch, classify it as either:

- `IMPLEMENTATION_GAP` — an existing capability could have matched more closely but was not used/configured well; or
- `TEMPLATE_LIMITATION` — the existing inventory genuinely cannot reproduce that aspect without changing/adding a template.

**Do not penalize TEMPLATE_LIMITATION mismatches as though Kiro had arbitrary rendering capability.** The point is to measure how well the existing reusable system performs, not whether it can reproduce an unconstrained design image.

Target **>=90/100 semantic accuracy** and **>=80/100 existing-template reference fidelity**.

## Evidence

Commit under `docs/stages/11-product-dashboard/` the final screenshot, compact generated page spec/configuration, timing evidence, semantic-model additions/spec used, and `REPORT.md`.

## REPORT.md

Keep the report concise. Include total elapsed time and timing breakdown; source/model and semantic additions; templates used; actual KPI/visual bindings; semantic accuracy score; existing-template reference-fidelity score; each mismatch classified as `IMPLEMENTATION_GAP` or `TEMPLATE_LIMITATION`; zero-touch result; confirmation that no templates were created or modified; screenshot path; and conclusion `PASS_UNDER_5_MIN`, `PASS_OVER_5_MIN`, or `FAIL_ACCURACY_OR_RENDER`.

A pass requires semantic correctness and a serious attempt to extract the maximum achievable fidelity from the existing reusable template system. The reference is a target for **composition with existing capabilities**, not permission to create new ones.