# Stage 11 — Minimal-Prompt Product Dashboard Challenge

## Instruction

Prepare and deploy a **Product Performance** dashboard matching this reference as closely as practical:

`docs/stages/11-product-dashboard/product-dashboard-reference.svg`

Use **existing registered templates only**. Do **not** create, modify or rebuild any visual template for this stage.

Match the established theme and visual language of the existing Executive, Financial and Customer dashboards.

Build any semantic-model additions required from the available source data, but do not proxy unrelated measures simply to populate the page.

Prioritize, in order:

1. semantic and numerical accuracy;
2. faithful mapping to the supplied reference using the existing template inventory;
3. visual consistency with the established premium dashboard system;
4. speed.

Target **under five minutes end-to-end** from start of execution to first populated headless screenshot.

## Constraints

- Use only capabilities already documented in `docs/TEMPLATE_INVENTORY.md`.
- No new custom visual or new template family.
- No Product-specific renderer branch.
- No manual Power BI Desktop step.
- No manual editor rebinding.
- Use the proven zero-touch private custom-visual packaging path.
- Infer aggressively from the reference and model/source data.
- Do not ask for clarification unless a correct dashboard is impossible without a missing fact.
- The illustrative values/text in the reference are **not ground truth**. Actual visual values, labels and comparisons must come from the available data/model and valid measures.
- If an exact reference element cannot be represented with an existing template, choose the closest analytically valid existing template and record the deviation; do not create a new template to chase pixel fidelity.

## Expected reference mapping

Treat the mockup primarily as a composition/design contract. The available template system should be sufficient for the intended structure:

- headline KPI row;
- ordered/time sales trend hero;
- category composition companion;
- ranked top-products view;
- grouped category-performance comparison;
- product-level detail/performance table;
- established nav, filters, spacing and dark executive theme.

Do not hard-code this mapping if the live source/model makes a different existing-template mapping more semantically correct.

## Semantic model

Use the Stage 10 rapid engine and semantic discovery/model-construction path.

If the required Product model already exists and is valid, reuse it. If source data requires extension or a new table/model element, infer and create the minimum correct structure needed for the dashboard, including where relevant:

- Product/category/brand dimensions;
- sales or transaction facts;
- ordered/date relationship required for the trend;
- sales/revenue measure;
- units/quantity measure;
- gross profit / cost measure where source data supports it;
- gross margin derived correctly from profit and sales;
- prior-period/prior-year comparison only where the date model supports it.

Do not invent unsupported financial fields. If source data cannot support a KPI shown in the mockup, substitute the closest high-value Product KPI supported by real data and document the substitution.

## Timing

Instrument actual wall-clock timings for:

- source/model inspection;
- semantic-model construction/update if required;
- page-spec generation;
- preflight validation;
- PBIR generation;
- deployment/refresh;
- headless render + screenshot;
- total.

The five-minute target is a product-performance objective, but accuracy takes priority. Do not hide errors or skip validation to claim a faster runtime.

## Validation

Before declaring completion, verify at minimum:

- every visual is populated from valid fields/measures;
- every measure displayed means what its label says;
- category/product rankings are correctly sorted where expected;
- trend axis is genuinely ordered/date-capable, not a broken string axis;
- gross margin is mathematically valid if displayed;
- filters bind to the relevant Product data;
- report loads cleanly with zero manual interaction;
- visual layout is within bounds and reasonably faithful to the reference;
- no new visual template/source implementation was added.

## Evidence

Commit under `docs/stages/11-product-dashboard/`:

- final screenshot;
- compact generated page spec or equivalent configuration;
- timing evidence;
- any semantic-model additions/spec used;
- `REPORT.md`.

## REPORT.md

Keep the report concise. Include:

- total elapsed time and timing breakdown;
- source/model used and any semantic-model additions;
- templates used;
- actual KPI/visual bindings;
- deviations from the reference and why;
- zero-touch deployment result;
- accuracy/preflight checks;
- confirmation that no new templates were created or modified;
- screenshot path;
- conclusion: `PASS_UNDER_5_MIN`, `PASS_OVER_5_MIN`, or `FAIL_ACCURACY_OR_RENDER`.

The purpose of this stage is to test whether the system can now deliver a new, polished, accurate dashboard from a **minimal prompt + reference** using the reusable capabilities it already has.