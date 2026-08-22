---
stage: 09
status: ready
title: Customer Performance dashboard from reusable premium templates
---

# Stage 09 — Customer Performance Dashboard

## Context

Stage 08 successfully extracted the Executive visual language into a reusable template system and used it to generate a Financial dashboard with 0% finance-specific visual source code. The next proof is **Customers**.

Read first:
- `KIRO.md`
- Stage 07d-b REPORT
- Stage 07e working implementation/progress
- Stage 08 TASK and REPORT
- `src/pbi_gen/renderer/templates/`

Canonical visual contract for this stage:

`docs/stages/09-customer-dashboard/customer-dashboard-reference.svg`

This is the approved target for **design quality, composition, hierarchy, spacing, density, typography, surfaces, colour discipline and executive impact**. Do not treat it as loose inspiration. Preserve real Power BI semantics/interactivity and adapt details where necessary, but the finished page should feel substantially like this reference and like the same product as Executive Overview and Financials.

## Primary objective

Build a **Customer Performance** page using the reusable premium template architecture, proving that the system can generate a third genuinely different executive dashboard with minimal page-specific engineering.

The page should answer, at a glance:
- Are we growing the customer base?
- Are we retaining customers?
- Which segments are most valuable?
- Where are customers being acquired?
- Which cohorts/segments need attention?

## Visual composition target

Match the reference's overall grammar:

1. shared left navigation with `Customers` active;
2. strong page title/subtitle and compact filter context;
3. five headline KPI cards;
4. dominant customer growth/retention hero chart;
5. customer segment breakdown;
6. acquisition-channel ranking;
7. customer-value segment table;
8. retention cohort treatment;
9. concise customer insights panel.

Do not create a wall of equal-weight rectangles. The hero trend must dominate; KPI row must read as one coherent executive band; bottom panels should be clearly supporting detail.

## Data/model requirements

Create or extend a coherent synthetic customer model sufficient to support the page. Prefer generic semantic-model extensions over visual-level hardcoding.

At minimum support concepts equivalent to:
- Customer ID;
- acquisition/join date;
- active/inactive/churn state;
- customer segment;
- acquisition channel;
- region;
- business unit where meaningful;
- revenue/customer value contribution;
- cohort period;
- retention/churn calculations.

Required measures should include, where modelled coherently:
- Active Customers;
- New Customers;
- Retention Rate;
- Churn Rate;
- Customer Lifetime Value or a clearly defined value proxy;
- customers by segment;
- customers acquired by channel;
- segment retention/value;
- cohort retention.

Do not invent independent KPI values in custom visual source. Derive them from the semantic model.

Retention and churn definitions must be documented and mathematically consistent. Do not automatically assume `Retention = 1 - Churn` unless the chosen cohort/time definition makes that true.

## KPI row

Target five headline KPIs matching the reference intent:
- Active Customers;
- New Customers;
- Retention Rate;
- Customer LTV / value;
- Churn Rate.

Use the reusable Premium KPI template. Extend it only through **generic reusable improvements** if required.

Where data supports it, include comparison vs prior year/period and compact trend treatment. Semantic direction matters: lower churn is positive.

## Customer Growth & Retention hero

Use/reuse the premium trend visual as the dominant chart.

Show customer growth over time and a meaningful retention series or comparison. If combining absolute customers and percentage retention in one visual would create a misleading mixed-scale presentation, preserve the reference's visual hierarchy but implement a more analytically valid treatment, such as aligned mini-series, secondary scale with explicit labelling, or customer growth plus prior-period customer series.

Requirements:
- correct chronological ordering;
- premium axis/gridline treatment;
- deliberate current/comparison hierarchy;
- useful tooltip;
- responsive to filters;
- no clipping;
- visually dominant on the page.

## Customer Segments

Use the premium breakdown/donut treatment or improve it generically if needed.

Show a coherent whole such as share of active customers by segment. Center label should show total active customers; legend should show segment and share/value where space allows.

## Acquisition by Channel

Use the reusable premium horizontal-bar treatment.

Rank channels by new customers/acquisitions. Sort descending, use restrained colour, direct labels and minimal chart chrome. Cross-filtering/selection should work where supported.

## Customer Value by Segment

Use the reusable premium table/ratio treatment.

Target columns equivalent to:
- Segment;
- Customers;
- Customer LTV/value;
- Retention Rate.

Keep density presentation-grade and use semantic emphasis sparingly. This should feel designed, not like a default Power BI table.

## Retention Cohorts

This is the main likely new visual family for Stage 09.

Create a **generic reusable cohort/heatmap template** if the current registry cannot express the reference adequately.

It must not be customer-specific in source code. Its generic contract should support concepts like:
- cohort category/period;
- elapsed period;
- measure/value;
- value format;
- semantic colour scale;
- optional labels/tooltips.

Register it in the template registry and prove it can theoretically bind to another cohort-style domain (e.g. employee cohort retention, subscription cohort usage) through a fixture/test.

If native Power BI can achieve the same premium result cleanly, native is acceptable, but do not accept a visibly default matrix simply to avoid creating the generic template.

## Customer Insights

The reference contains a concise insights panel. Do **not** hard-code business conclusions into the custom visual.

Use one of these approaches, in priority order:
1. refactor/reuse `premiumInsights` so insight rows are data/config driven;
2. generate insight statements upstream from deterministic metric rules and pass them as data/config;
3. if neither is robust in this stage, use a premium data-driven exception/ranking panel instead.

No fixed retail/customer prose inside TypeScript.

## Navigation and report continuity

This should be a page in the same product/report shell, not a disconnected report aesthetic.

Navigation should show at least:
- Overview;
- Financials;
- Customers;
- Products.

`Customers` must be active. Preserve the same design tokens and navigation grammar as Stage 08.

If practical, move closer to a true multi-page report with functional page navigation rather than separate demo reports. Do not let this derail the primary visual/template proof if Fabric/PBIR navigation mechanics require disproportionate work; document the boundary.

## Reuse discipline

Classify every page component/change as:
- `template_reuse_only`;
- `generic_template_improvement`;
- `customer_specific_visual_code`.

Hard target: **0% customer-specific visual source code**.

Hard maximum: no more than **20%** of page visual components may require customer-specific source changes; exceeding this means the reusable template system has failed the stage.

Any new cohort visual or insight improvement must be generic and reusable.

## Screenshot-driven implementation loop

Use the reference as a visual contract:

`reference → build → zero-touch deploy → headless screenshot → compare → identify largest visual gaps → generic refinement → redeploy`

Allow at most **three material visual refinement cycles after the first complete render**. Track them in the report.

Do not claim success merely because the first render works technically. Stage 08's critic was blocked; Stage 09 must restore strict visual-quality validation if an OpenAI-capable multimodal critic is available in the execution environment.

## Zero-touch deployment

Use the proven private custom visual PBIP structure from 07d-b:

`CustomVisuals/{GUID}/package.json`
`CustomVisuals/{GUID}/resources/{GUID}.pbiviz.json`
`report.json → resourcePackages[type=CustomVisual]`

Acceptance requires fresh deployment with:
- no organizational consent;
- no manual editor touch;
- no manual binding;
- no Desktop action per generated report;
- first headless render populated with data.

## Functional acceptance

Verify:
- KPI values derive from model and are correct;
- chronological ordering is correct;
- filters/slicers affect all relevant visuals;
- region/segment/date filtering works;
- chart selection/cross-filter works where exposed;
- cohort values reconcile with the documented retention definition;
- insights are data/config driven;
- no broken visuals;
- no clipping/overflow;
- deterministic rendering;
- Executive and Financial template reuse is not regressed.

## Visual-quality rubric

Run at least three comparable multimodal critic assessments on the final Customer screenshot if critic access is available. If unavailable, mark the scoring gate BLOCKED rather than inventing scores.

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

Also score relative visual-quality parity against `customer-dashboard-reference.svg` on 0–100, where 100 means equal overall design quality rather than pixel identity.

## Hard visual gates

Target/acceptance bar remains the original premium product requirement:
- median overall visual quality ≥ **7.5/10**;
- executive credibility ≥ **8.0/10**;
- demo readiness ≥ **8.0/10**;
- company-wide presentation readiness ≥ **8.0/10**;
- premium/brand feel ≥ **7.5/10**;
- no core visual dimension below **7.0/10** median;
- median relative parity with the Customer reference ≥ **80/100**.

At least 2/3 runs must answer YES to:

> Would you comfortably present this exact Customer dashboard design to the executive committee of a large enterprise?

and:

> Does this look materially closer to a premium bespoke analytics product than to a default Power BI report?

If critic access is unavailable, do not mark these gates as passed. Report them as blocked and provide screenshot evidence for external review.

## Template-system gates

Stage 09 must also prove:
- Customer page is assembled predominantly from Stage 08 templates;
- any new cohort/insight capability is generic and registered;
- 0% target / ≤20% hard maximum customer-specific visual source changes;
- design tokens remain centralized;
- private custom visual embedding remains automatic;
- at least two new automated cross-domain reuse tests are added;
- page reaches final form within ≤3 material refinement cycles;
- Executive and Financial regression builds still succeed.

## Evidence package

Commit under `docs/stages/09-customer-dashboard/`:
- `customer-dashboard-reference.svg`;
- first full Customer screenshot;
- iteration screenshots/contact sheet;
- final Customer screenshot;
- `CUSTOMER_VISUAL_ASSESSMENT.json` if critic is available;
- `CUSTOMER_TEMPLATE_REUSE_MANIFEST.json`;
- customer metric/model definitions and reconciliation evidence;
- zero-touch deployment evidence;
- Executive/Financial regression evidence;
- `REPORT.md`.

## REPORT.md requirements

Include:
- Stage 08 baseline/template system used;
- Customer data/model architecture;
- precise retention/churn/LTV definitions;
- visual composition and bindings;
- reused templates;
- generic template improvements/new templates;
- first screenshot;
- each material refinement cycle;
- final screenshot;
- reuse classification and customer-specific-code percentage;
- cohort implementation and genericity proof;
- insight implementation and proof it is data/config driven;
- critic runs/medians/ranges or explicit BLOCKED status;
- reference-parity score or BLOCKED status;
- zero-touch deployment result;
- filter/interaction tests;
- Executive/Financial regression result;
- automated test results;
- remaining limitations;
- explicit answers:

> **Can the same premium template system now generate a Customer Performance dashboard at the same executive visual standard with minimal bespoke engineering?**

> **Did the Customer page reach the approved reference standard while remaining generic, interactive and zero-touch deployable?**

Do not answer yes without the corresponding evidence.