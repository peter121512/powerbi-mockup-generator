---
stage: 08
status: ready
title: Reusable premium templates + Financial Performance dashboard
---

# Stage 08 — Reusable Premium Templates & Financial Performance Dashboard

## Context

Stage 07e is still in progress. There is no final `REPORT.md` yet; the current stage directory contains `PROGRESS_RESPONSIVE.md` plus working screenshots. Do not discard that work. Stage 08 is the next product milestone once the Executive Overview is stable enough to extract reusable visual primitives.

The product goal now changes from **one beautiful executive page** to **repeatable premium dashboard generation**.

We need to prove that the visual language developed for Executive Overview can be captured as reusable templates/components and then applied to a genuinely different business page with:

- new metrics;
- new data;
- different chart mix;
- the same visual standard;
- minimal design iteration.

The first reuse target is the Financial dashboard from the left navigation.

Canonical visual reference for this stage:

`docs/stages/08-financial-dashboard/financial-dashboard-reference.svg`

This reference is a design contract for quality, hierarchy, spacing, density, composition and premium finish. It is not a requirement to reproduce every decorative pixel literally.

## Primary outcomes

Stage 08 has **two equally important deliverables**:

1. extract the winning 07e visual system into **reusable templates/components** that can be used for future dashboard pages without re-designing from scratch;
2. build a **Financial Performance** dashboard using those templates, new finance data and new metrics while preserving the same executive-grade visual quality.

If the Financial page only looks good because it contains one-off hard-coded styling, Stage 08 has failed.

---

# Part A — Reusable premium template system

## 1. Freeze the reusable visual primitives

Identify the strongest successful Stage 07e implementations and convert them into reusable custom visual templates/components.

At minimum capture reusable definitions for:

- Premium KPI Card;
- Premium Line / Area Trend;
- Premium Horizontal Bar;
- Premium Donut / Breakdown;
- Premium Table / Ratio List;
- Premium Waterfall / Bridge;
- Premium Region / Geo Summary treatment if feasible;
- shared title / subtitle / header treatment;
- shared filter / slicer treatment;
- shared page navigation shell;
- shared panel/container treatment.

Do not simply copy files and rename them. Extract reusable design tokens, data roles, sizing rules and interaction behaviour.

## 2. Template API / configuration contract

Each reusable visual template must have an explicit configuration/data contract.

For example, a KPI template should accept concepts such as:

```text
label
primary_measure
comparison_measure or variance_measure (optional)
format
semantic_direction
accent_role
sparkline/category series (optional)
priority
```

A line/area template should accept concepts such as:

```text
category/date axis
primary measure
comparison measure (optional)
series labels
number format
accent role
legend policy
reference/tooltip behaviour
```

Exact schemas are implementation decisions, but the system must make it possible to instantiate the same visual template with entirely different metrics without rewriting TypeScript/LESS for each page.

## 3. Shared design tokens

Centralize the visual design language so future visuals/pages inherit the same system automatically.

At minimum centralize:

- canvas/background colours;
- panel/surface colours;
- border/radius policy;
- primary/secondary text colours;
- accent palette;
- positive/negative/warning semantic colours;
- typography scale;
- spacing scale;
- KPI label/value hierarchy;
- chart axis/gridline policy;
- table density;
- header/filter treatment.

No page-specific hard-coded copies of the same token set.

## 4. Responsive sizing rules

The current 07e work is explicitly dealing with responsive layout. Preserve that learning.

Reusable visual templates must behave correctly across the set of sizes expected in page layouts:

- KPI compact/wide;
- hero chart;
- half-width supporting chart;
- bottom/detail panel;
- table/ratio panel.

No clipping, unreadable fonts or excessive empty space when reused at intended dimensions.

## 5. Interaction contract

Reusable custom visual templates must preserve Power BI behaviour where relevant:

- receive slicer/filter updates;
- respond to report/page filters;
- support cross-filter or selection where the visual type requires it;
- expose useful tooltips;
- preserve data identity/selection state;
- render deterministic empty/null states.

A reusable visual cannot be purely decorative.

## 6. Template registry

Introduce a registry or equivalent reusable mapping so the renderer can request a visual family by semantic role rather than page-specific implementation name.

Conceptually:

```text
premium_kpi
premium_trend
premium_bar
premium_breakdown
premium_table
premium_waterfall
premium_region_summary
```

The registry should associate each template with:

- custom visual GUID/package;
- supported data roles;
- required/optional fields;
- default dimensions;
- formatting tokens;
- interaction capabilities.

Future page generation should consume this registry rather than hard-coded 07e references.

## 7. Private custom visual packaging

Reuse the proven 07d-b zero-touch PBIP packaging path:

```text
CustomVisuals/{GUID}/package.json
CustomVisuals/{GUID}/resources/{GUID}.pbiviz.json
report.json → resourcePackages / CustomVisualMetadata
```

The renderer should automatically embed every custom visual package actually used by a generated report.

No org-store consent path. No AppSource requirement. No per-viewer/manual setup.

## 8. Reuse tests before Financial page

Before building the Financial page, create at least lightweight automated fixtures proving that the same template can bind to two different metric sets.

Examples:

- KPI template: Revenue vs Headcount;
- Trend template: Revenue over time vs Customers over time;
- Bar template: Expenses by category vs Sales by product;
- Table template: Financial ratios vs product performance.

The objective is to prove reuse before the page itself becomes evidence.

---

# Part B — Financial Performance page

## 9. Reference mockup

Use:

`docs/stages/08-financial-dashboard/financial-dashboard-reference.svg`

as the page-specific visual-quality target.

The dashboard should feel like the same product as Executive Overview:

- same navigation shell;
- same dark premium design language;
- same typography family/hierarchy;
- same panel grammar;
- same filter/header language;
- same density discipline;
- same executive presentation standard.

But it should contain **finance-specific information**, not copied executive-page metrics.

## 10. Generate new coherent financial data

Create a realistic synthetic finance model for FY2024 with sufficient granularity to support the Financial page.

At minimum support monthly analysis and meaningful slicing by the existing dimensions such as region and business unit.

Recommended financial facts/dimensions include, where appropriate:

### Profit & loss
- Revenue;
- Cost of Goods Sold;
- Gross Profit;
- Operating Expenses;
- EBITDA;
- Depreciation / Amortization if required;
- Operating Profit;
- Tax / Interest if needed;
- Net Profit.

### Expense categories
- COGS;
- Sales & Marketing;
- R&D;
- General & Admin;
- Other operating expenses.

### Cash flow
- Opening cash;
- Operating cash flow;
- Investing cash flow;
- Financing cash flow;
- Closing cash.

### Ratios
Support measures such as:

- Gross Margin;
- Operating Margin;
- Net Margin;
- ROE;
- ROIC;
- Current Ratio;
- Debt-to-Equity.

Do not create arbitrary independent numbers. Values must reconcile mathematically where possible.

Examples:

```text
Gross Profit = Revenue - COGS
Gross Margin = Gross Profit / Revenue
Operating Profit = Gross Profit - Operating Expenses
Net Margin = Net Profit / Revenue
Closing Cash = Opening Cash + Operating CF + Investing CF + Financing CF
```

Where metrics cannot be derived from the existing semantic model, extend it generically rather than embedding values in the visuals.

## 11. Financial KPI row

Target five headline KPIs, matching the reference composition:

- Total Revenue;
- Gross Profit;
- EBITDA;
- Net Profit;
- Gross Margin.

Each should use the **same reusable Premium KPI template** from Part A with new bindings.

Where possible show:

- current value;
- vs prior-year percentage or percentage-point change;
- a compact 12-month sparkline.

Do not invent comparison numbers independently; derive them from the model.

## 12. Revenue Over Time

Use the reusable premium trend template.

Show monthly Revenue and prior-year/comparison series where available.

Requirements:

- January–December correctly ordered;
- current-year series visually dominant;
- comparison series deliberately subdued;
- readable axis/tooltip formatting;
- consistent chart surface/title treatment;
- response to page slicers.

## 13. Profitability Overview

Use the reusable breakdown/donut template.

Represent a meaningful finance breakdown such as profit/revenue contribution by revenue stream or business model.

The center value should show the main aggregate and the legend should include both value and percentage where space permits.

Do not use a donut merely because the reference has one if the underlying categories cannot form a coherent whole. If necessary choose a mathematically valid finance breakdown while preserving the same visual treatment.

## 14. Expenses by Category

Use the reusable horizontal bar template.

Rank expense categories by value with restrained semantic colours and professional number formatting.

Requirements:

- sorted descending;
- direct value labels;
- no unnecessary axes/gridlines;
- compact but readable category labels;
- filters/cross-highlighting functional.

## 15. Key Financial Ratios

Use the reusable premium table/ratio template.

Show at least 5 useful financial ratios with:

- metric name;
- current value;
- change vs prior period/year;
- compact trend/spark indicator if feasible.

Semantic colouring must be metric-aware. For example, higher debt-to-equity is not automatically positive simply because the numeric change is positive.

## 16. Cash Flow Summary

Build or reuse a premium waterfall/bridge template.

At minimum communicate:

```text
Opening Cash
+ Operating CF
+ Investing CF
+ Financing CF
= Closing Cash
```

Use positive/negative semantic colours and clear value labels.

If a true waterfall custom visual is required, make it reusable and register it in the template system rather than coding it as a finance-only visual.

## 17. Revenue by Region

Use the strongest feasible reusable regional-summary treatment.

The reference uses map-like regional emphasis plus a ranked table. The actual implementation may use:

- native map combined with a premium side table;
- a custom region summary visual;
- or another robust Power BI-native/custom hybrid.

The result should show regional revenue and growth with the same premium design quality.

Do not compromise zero-touch deployment or cross-filter behaviour for decorative geography.

## 18. Navigation continuity

The Financial page should appear as the next page within the same report/product shell.

The navigation must show Financials as the active item and support navigation between at least:

- Executive Overview;
- Financials.

Do not create a disconnected standalone report page with a different shell.

---

# Part C — Minimal-iteration success criterion

## 19. Track page-specific work

A major Stage 08 objective is proving that new dashboards can be produced with **minimal visual engineering iteration**.

Track implementation effort explicitly.

Classify every change required to build Financial as one of:

- `template_reuse_only` — new data/config/binding, no visual source code change;
- `generic_template_improvement` — reusable improvement that benefits all future pages;
- `financial_specific_visual_code` — finance-only custom implementation.

The target is that the overwhelming majority of Financial is `template_reuse_only` or a generic reusable improvement.

## 20. Hard reuse gate

Stage 08 should not be considered a successful reuse proof if more than **20% of the Financial page's visual components require finance-specific visual source-code changes**.

Ideally the page should be assembled almost entirely from existing templates plus configuration and bindings.

Any new visual family required by finance, such as waterfall, must be created as a generic template suitable for future pages.

## 21. Iteration limit

After the first end-to-end Financial render, allow a maximum of **three material visual refinement cycles** before final scoring.

A refinement cycle means a real screenshot-driven design change, not trivial typo/data correction.

If the page requires more than three major visual iterations to reach the bar, document why the template system failed to generalize.

This is a key product metric.

---

# Part D — Acceptance testing

## 22. Headless zero-touch deployment

The final Financial page must be generated/deployed through the fully automated PBIP path.

Acceptance requires:

- custom visuals embedded with the 07d-b private resource structure;
- no organizational visual consent;
- no manual editor touch;
- no manual data rebinding;
- no Desktop requirement per generated report;
- first headless render populated with data.

## 23. Functional validation

Verify:

- all Financial visuals display correct values;
- financial equations reconcile;
- filters work;
- region/business-unit slicers affect the page;
- date filtering works;
- cross-filter/selection works for visuals that expose selection behaviour;
- tooltips work where implemented;
- navigation works;
- no broken visual icons;
- no clipping or overflow;
- report still loads cleanly.

## 24. Visual-quality assessment

Use the same strict visual-only evaluation philosophy as 07e.

Ignore analytical disagreements that are outside the renderer's visual responsibility when scoring visual design.

Score:

- first-impression professionalism;
- executive credibility;
- hierarchy/composition;
- typography;
- whitespace/rhythm;
- KPI treatment;
- chart presentation;
- colour discipline;
- surface/container quality;
- visual consistency;
- premium/brand feel;
- demo readiness;
- company-wide presentation readiness.

Run the final Financial page through at least 3 comparable critic assessments and report median/range.

## 25. Financial visual hard gates

The Financial page is accepted only if:

- median overall visual quality ≥ **7.5/10**;
- executive credibility ≥ **8.0/10**;
- demo readiness ≥ **8.0/10**;
- company-wide presentation readiness ≥ **8.0/10**;
- premium/brand feel ≥ **7.5/10**;
- no core visual dimension below **7.0/10** median;
- median relative design-quality parity with `financial-dashboard-reference.svg` ≥ **80/100**.

At least 2/3 critic runs must answer YES to:

> Would you comfortably present this exact Financial dashboard design to the executive committee of a large enterprise?

and:

> Does this look materially closer to a premium bespoke analytics product than to a default Power BI report?

## 26. Reuse-quality hard gates

The template system itself is accepted only if:

- at least 5 major reusable visual templates are registered and documented;
- the Financial page uses those templates with new metrics/data;
- ≤20% of Financial visual components require finance-specific visual source changes;
- zero-touch custom visual packaging remains automatic;
- configuration/data roles can be changed without editing visual styling code;
- at least two automated cross-domain fixtures prove template reuse;
- Financial reaches the visual bar within ≤3 material post-first-render refinement cycles.

## 27. Preserve Executive Overview

Stage 08 must not regress the Executive Overview.

Run a regression screenshot/check after template extraction.

Executive Overview must retain:

- working data;
- working custom visuals;
- zero-touch deployment;
- expected design quality;
- existing navigation;
- no clipping/regressions caused by shared token/template changes.

---

# Evidence package

Commit under `docs/stages/08-financial-dashboard/`:

- `financial-dashboard-reference.svg`;
- first full Financial render screenshot;
- iteration screenshots/contact sheet;
- final Financial screenshot;
- `FINANCIAL_VISUAL_ASSESSMENT.json` with all critic runs;
- `TEMPLATE_REUSE_MANIFEST.json`;
- template registry summary;
- data/model reconciliation evidence;
- zero-touch deployment evidence;
- Executive regression screenshot;
- `REPORT.md`.

Also document reusable template code under the appropriate source/custom-visual directories, not under `docs`.

# REPORT.md requirements

Include:

- current Stage 07e baseline used for extraction;
- reusable template architecture;
- list of visual templates and GUIDs/data roles;
- shared design-token architecture;
- private PBIP package integration;
- generated finance model/data architecture;
- financial measure definitions and reconciliation checks;
- Financial page composition;
- first-render screenshot;
- number and nature of refinement cycles;
- classification of page work into `template_reuse_only`, `generic_template_improvement`, `financial_specific_visual_code`;
- percentage of Financial components requiring page-specific source changes;
- final screenshot;
- all visual critic runs and medians/ranges;
- relative-to-reference score;
- zero-touch deployment result;
- filter/interaction/navigation tests;
- Executive Overview regression result;
- automated test results;
- explicit answer to both questions:

> **Can the same premium visual templates now generate a genuinely different dashboard with new data and metrics at the same executive visual standard?**

> **Did Financial reach that standard with minimal iteration and without bespoke visual re-engineering?**

Do not mark success unless both answers are yes and the hard gates are met.
