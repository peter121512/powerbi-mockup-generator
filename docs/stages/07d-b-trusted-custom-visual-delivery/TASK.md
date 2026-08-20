---
stage: 07d-b
status: ready
title: Trusted custom visual delivery paths for PBIP
---

# Stage 07d-b — Trusted Custom Visual Delivery Paths for PBIP

## Context

Stage 07d-a established that the apparent custom-visual "binding" problem is actually a Power BI Service trust/consent problem. Organizational custom visuals execute and receive `dataViews` correctly once consent is granted, but fresh REST/API deployments require a per-viewer consent step. Pre/post PBIR definitions are byte-for-byte identical, so there is no missing binding metadata to synthesize.

Do not continue experimenting with more variants of `organizationCustomVisuals` through `updateDefinition`; that path is already well explored and blocked.

However, Microsoft's PBIP model supports additional custom-visual delivery/authorship paths that have not yet been experimentally exhausted. In particular:

- private `.pbiviz` files persisted in PBIP projects;
- Desktop-authored PBIP projects;
- Fabric Git integration as a deployment path rather than REST `updateDefinition`;
- seeded/template PBIP reports containing an already imported custom visual;
- AppSource/public custom visuals, including uncertified publication;
- potentially private Marketplace distribution.

This stage exists to determine whether any of those paths can preserve trusted custom visual execution while still supporting the automated generation architecture.

## Product requirement

The visual goal remains unchanged: custom visuals are being pursued because native Power BI visuals have not reached the premium executive design standard required by this project.

A successful delivery path must therefore support **real custom-visual execution without viewer consent prompts** while remaining compatible with the generated PBIP/PBIR workflow.

The acceptance question is not merely "can a custom visual appear in Power BI?" It is:

> Can this system generate or mutate a PBIP-based report containing premium custom visuals, deliver it into Fabric, and have those visuals execute with data for a fresh viewer without a per-report/per-viewer manual consent step?

## Read first

1. Read `KIRO.md`.
2. Read Stage 07d, 07d-a TASK/REPORT files.
3. Inspect the Premium KPI source/package and any Premium Chart work already present.
4. Inspect the exact 07d-a consent evidence and candidate matrix.
5. Review current Microsoft documentation for PBIP report projects, custom visuals, Git integration, AppSource visual offers and private plans.
6. Preserve all existing working semantic-model/report deployment capability.

## Scope

This is a delivery/trust experiment, not a visual design stage.

Do not spend time improving KPI/chart styling, analytical design, month sorting, mixed axes or the critic loop. Use the existing Premium KPI as the principal probe and a second custom visual only where useful to prove generality.

## Experiment A — Desktop-authored PBIP with private `.pbiviz`

This is the highest-priority path.

Create the smallest possible PBIP report in Power BI Desktop that:

- uses the project's semantic model or a minimal compatible model;
- imports the Premium KPI `.pbiviz` from file/private source;
- binds it to a real measure;
- saves the report as PBIP;
- closes Desktop cleanly.

Then inspect and commit a sanitized structural manifest of the resulting PBIP representation.

Determine exactly:

- where the private `.pbiviz` is persisted;
- the `CustomVisuals/` directory structure;
- any `StaticResources/RegisteredResources/` entries;
- the custom visual identity used in `visual.json`;
- report-level declarations;
- resource-package metadata;
- any differences from the REST-generated organizationCustomVisual report.

Do not assume documentation alone proves runtime behaviour.

### A1. Fresh Fabric Git deployment

Put the Desktop-authored PBIP project into a Fabric-connected Git repository/workspace using the supported Git integration path.

Sync/import it into a **fresh report item**.

Test with a viewer/session that does not rely on cached consent from prior experiments.

Capture headless evidence answering:

- does the private custom visual execute immediately?
- is there a consent/add-this-visual prompt?
- does `update()` receive `dataViews`?
- is data visible on first render?
- does it work with an embed token as well as normal Service viewing where practical?

This single experiment must distinguish "Desktop imported custom visual" trust from "organizational store custom visual" trust.

## Experiment B — Seeded PBIP template mutation

If Experiment A renders without consent, test whether that trust can survive programmatic generation.

Treat the Desktop-authored PBIP as a **seed template** containing the imported custom visual resource and at least one correctly instantiated visual.

Without reopening Desktop, programmatically mutate renderer-owned PBIP/PBIR content to create materially different report output while retaining the same custom visual package/GUID.

At minimum test:

1. change visual position/size;
2. change the measure binding to another compatible measure;
3. duplicate the custom KPI visual into multiple KPI instances if feasible;
4. alter unrelated native visuals/page layout;
5. create a new page containing an instance of the already-imported custom visual if the PBIR representation permits it.

Then deploy/sync via **Fabric Git integration**, not `updateDefinition`, and test a fresh viewer.

### Critical B question

Determine the boundary between safe mutation and trust reset.

Classify each mutation as:

- trust preserved + data renders;
- trust preserved but binding fails;
- consent required again;
- deployment rejected;
- unsupported/unknown.

If simply modifying `visual.json` inside the seeded PBIP is enough to create new trusted instances, that is a potentially viable generation architecture.

If only the exact Desktop-authored instances remain trusted, document that limitation precisely.

## Experiment C — Git integration versus `updateDefinition`

Where Experiment A/B succeeds, compare lifecycle behaviour with REST `updateDefinition`.

Use equivalent changes delivered through:

- Fabric Git sync/update;
- REST `updateDefinition`.

Test whether the same PBIP artifact behaves differently depending on delivery mechanism.

The goal is to identify whether the consent reset discovered in 07d-a is specifically an `updateDefinition` lifecycle side effect.

Do not infer this from documentation; capture actual runtime evidence.

## Experiment D — AppSource/public visual publication feasibility

If A/B cannot provide zero-touch runtime, investigate the AppSource route concretely.

Important distinction: **Marketplace/AppSource publication and Power BI certification are not the same thing. Certification is optional.**

Determine the minimum viable route for publishing the Premium KPI as a Power BI visual offer without certification.

Document:

- Partner Center requirements;
- whether a public Power BI visual offer can be published uncertified;
- package/GUID/version requirements;
- expected lead-time/review gates that are mandatory even without certification;
- whether `publicCustomVisuals` can reference the resulting visual identity;
- whether non-certified AppSource visuals still prompt users on report viewing or only on import/addition;
- export/email/subscription limitations for uncertified visuals;
- implications for enterprise tenants that enforce certified visuals only.

If the existing account/environment permits publishing a test visual without irreversible public exposure, perform the smallest safe test. Otherwise stop at a precise documented feasibility assessment rather than inventing evidence.

## Experiment E — Private Marketplace / private plan

Investigate whether a Power BI visual offer can be distributed through a tenant-restricted/private Marketplace plan while still being resolved by the Power BI Service as a trusted/public visual at runtime.

Answer:

- can the plan be restricted to one or more tenant IDs?
- does the visual still obtain an AppSource/Marketplace identity usable by `publicCustomVisuals`?
- does the viewer avoid the organizational visual consent overlay?
- are private-plan visuals discoverable/usable inside Power BI in the same way as public marketplace visuals?
- what limitations apply to certification and store visibility?

Only implement/test if the environment permits it safely.

## Experiment F — report/resource embedding within PBIP

07d-a tested REST-deployed embedded custom visual resource packages and found the Service would not execute them. Revisit this **only in the context of a genuine Desktop-authored PBIP**, because Desktop may emit additional resource metadata.

Compare the exact private visual resource representation saved by Desktop with the failed handcrafted resource package from 07d-a.

If they differ, test whether reproducing the Desktop-authored private resource structure programmatically inside a PBIP project is sufficient.

This experiment is critical because it could allow the generator to carry `.pbiviz` binaries directly inside PBIP without AppSource or organizational-store registration.

## Experiment G — new Microsoft programmatic authoring capability

Investigate the current Microsoft programmatic/report-authoring capability referred to in 07d-a as the "Power BI Report Authoring Skill / Agentic API" or current equivalent.

Establish:

- the exact product/API name;
- whether it is generally available, preview, tenant-gated, or documentation-only;
- whether it can create custom visual instances;
- whether it can import/attach private or organizational custom visuals;
- whether reports authored through it avoid the viewer-consent state seen with raw `updateDefinition`;
- authentication/service-principal support;
- whether it is suitable for automated generation.

If accessible in the current tenant, perform a minimal test. If not, document precisely why it cannot yet be used.

## Fresh-viewer methodology

Consent caching invalidated earlier tests, so this stage must use a strict fresh-viewer protocol.

For every claimed zero-touch success:

- use a newly created report item where practical;
- avoid reusing a report already manually activated;
- use a browser context/profile without prior custom visual consent state where possible;
- capture the first render before any edit-mode interaction;
- record whether the visual constructor/update executes;
- record whether dataViews are present;
- capture a screenshot.

At least **3 independent first-render tests** are required for any path declared successful.

## No hidden manual step

The following do **not** count as automated success:

- opening Desktop for every generated report;
- clicking "add custom visual" after deployment;
- edit-mode untick/retick;
- a one-time activation per generated report;
- using a browser profile whose consent state was primed manually for that report;
- manually uploading/importing the `.pbiviz` into each report;
- post-deployment Playwright clicking through the consent overlay.

A one-time setup for the **visual product itself** (for example publishing it to AppSource or creating a Desktop-authored seed template) may be acceptable if all subsequently generated reports are zero-touch.

## Viable architecture definitions

Classify each route at the end as one of:

### `VIABLE_ZERO_TOUCH`
Fresh generated reports render trusted custom visuals with data and no viewer/report-specific manual consent.

### `VIABLE_WITH_ONE_TIME_PRODUCT_SETUP`
Requires a one-time action such as AppSource publication, tenant visual installation, or creation of a canonical trusted PBIP template, but generated reports thereafter are zero-touch.

### `NOT_VIABLE_FOR_AUTOMATION`
Requires per-report or per-viewer manual interaction, or cannot be reproduced through the generation/deployment architecture.

## Acceptance criteria

Stage 07d-b is complete when all of the following are true:

- Desktop-authored private PBIP custom visual structure has been inspected empirically;
- Experiment A fresh Git-deployment runtime result is captured;
- if A succeeds, template mutation boundary is tested through Experiment B;
- Git versus `updateDefinition` lifecycle behaviour is experimentally compared where possible;
- the exact Desktop private-resource structure is compared with the failed handcrafted embedding attempt;
- AppSource uncertified publication is assessed accurately and, where safely possible, tested;
- private Marketplace/private plan feasibility is assessed;
- the current Microsoft programmatic authoring API/capability is identified and evaluated;
- fresh-viewer methodology is used to avoid cached-consent false positives;
- each route is classified `VIABLE_ZERO_TOUCH`, `VIABLE_WITH_ONE_TIME_PRODUCT_SETUP`, or `NOT_VIABLE_FOR_AUTOMATION`;
- at least one route is proven with 3/3 zero-touch first renders **or** the report provides strong evidence that all remaining PBIP/custom-visual paths still require manual consent;
- no unsupported claim is presented as fact;
- existing test suite remains green.

## Preferred outcome

The ideal architecture is one of these:

```text
Premium custom visual built once
→ embedded/imported once into canonical PBIP template
→ generator mutates PBIR pages/bindings/layout
→ Fabric Git sync
→ fresh viewers see populated custom visuals immediately
```

or:

```text
Premium custom visual published once to AppSource/Marketplace
→ generator emits publicCustomVisuals references
→ normal API/Git deployment
→ fresh viewers see populated custom visuals immediately
```

Either would justify continuing toward the premium custom-visual library.

## Evidence package

Commit under `docs/stages/07d-b-trusted-custom-visual-delivery/`:

- Desktop PBIP structural manifest/diff;
- screenshots for fresh-viewer Experiment A;
- mutation matrix/evidence for Experiment B;
- Git-vs-updateDefinition comparison;
- private resource structure comparison;
- AppSource/private plan feasibility notes;
- programmatic authoring capability notes;
- `DELIVERY_PATH_MATRIX.json` containing route/status/evidence;
- `REPORT.md`.

Do not commit confidential tenant IDs, access tokens, credentials or private marketplace secrets.

## REPORT.md requirements

Include:

- concise executive summary;
- exact trust/consent question being tested;
- Desktop private PBIP representation findings;
- Experiment A result;
- Experiment B mutation boundary if applicable;
- Fabric Git versus REST lifecycle result;
- private resource embedding conclusion;
- AppSource uncertified publication conclusion;
- private Marketplace/private-plan conclusion;
- current programmatic authoring API conclusion;
- 3-run fresh-viewer evidence for any successful route;
- route classification matrix;
- deployment/tenant/security implications;
- automated test results;
- one explicit recommendation for the product architecture.

The final recommendation must answer:

> **Is there now a PBIP-compatible path that lets the generator deliver premium custom visuals to fresh report viewers with zero report-specific/viewer-specific manual consent?**

If yes, state the exact path and what one-time setup it requires. If no, state which remaining option (most likely AppSource publication/certification) should become the product architecture decision.
