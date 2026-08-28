# Stage 12B — Persistent Deployment & Working Navigation

## Purpose

Stage 12A stabilised the visual system. Stage 12B now changes the report/runtime architecture so generated reports behave like persistent products rather than disposable artifacts.

The stage has two primary outcomes:

1. **Persistent report identity** — subsequent updates must update the existing report in place wherever possible, preserving report ID and URL instead of delete-and-create.
2. **Real navigation** — the Executive, Financial, Customer and Product dashboards must be linked through a working, polished navigation system that visually matches the established mockups more closely.

This stage should finish with a coherent multi-page report experience rather than four disconnected standalone dashboards.

---

## Read first

Review:

- `KIRO.md`;
- Stage 07d-a, 07d-b reports on custom visual packaging/consent;
- Stage 08–11 report generation architecture;
- Stage 12A task/report and shared design tokens;
- current deployment helpers / REST createReport / updateDefinition paths;
- current page/nav rendering in `PageBuilder`, `rapid_engine`, configs and deploy scripts;
- all four current dashboard configs/screenshots.

Pay particular attention to the previous finding that custom visual execution/consent behaviour can differ across deployment approaches. Do **not** assume `updateDefinition` is safe until experimentally proven with the private PBIP custom-visual packaging path.

---

# Part A — Persistent report deployment

## 1. Introduce create-or-update deployment semantics

Replace the current default "delete old report, create new report" behaviour with a generic deployment strategy:

```text
if target report exists:
    update existing report definition in place
else:
    create report
```

The deployment contract must make report identity explicit, ideally via a stable logical report key/name mapped to Fabric report ID.

The normal update path must preserve:

- report ID;
- report URL;
- report workspace identity;
- semantic model binding where unchanged;
- private custom visual packages;
- page definitions;
- zero-touch render behaviour.

Do not preserve identity by relying on a manually-maintained one-off ID in a script. Make this reusable infrastructure.

## 2. Prove report ID and URL stability

For a test report, capture before update:

- report ID;
- web URL/embed URL or equivalent stable viewer URL;
- page IDs/names;
- current definition hash/version.

Perform a real visible update (e.g. title/subtitle/config change) using the new in-place path.

Then prove:

- same report ID after update;
- same report URL after update;
- changed content visible;
- report still renders headlessly;
- custom visuals execute immediately;
- no manual consent/editor interaction.

Repeat at least **3 consecutive in-place updates** on the same report ID.

## 3. Custom visual regression gate

This is a hard gate because earlier stages found consent/runtime differences with update mechanisms.

For each of the 3 repeated updates verify:

- private custom visuals remain embedded/registered correctly;
- `premium_kpi`, `premium_trend` and any other custom visual used execute on first viewer render;
- data binding is populated on first render;
- no visual error placeholder;
- no manual Power BI edit/save cycle;
- no organizational custom visual consent prompt.

If `updateDefinition` breaks the proven private visual path, do not silently accept it. Investigate whether a different update/publish API, multipart definition structure, clone+swap mechanism, Fabric Git/PBIP route, or another supported approach can preserve stable identity.

A persistent URL that breaks custom visuals is not acceptable.

## 4. Deployment API abstraction

Create a reusable deployment service/module with an explicit result such as:

```text
DeploymentResult
- report_id
- report_url
- action: CREATED | UPDATED
- previous_report_id
- definition_version/hash
- elapsed_time
- render_verified
```

All future report generation should call this rather than implementing delete/create logic in per-dashboard scripts.

Add unit/integration tests for:

- create when absent;
- update when present;
- stable ID preservation;
- safe fallback/error behaviour;
- duplicate-name handling;
- deterministic logical report lookup.

---

# Part B — Consolidate the four dashboards into a coherent report

## 5. Preferred architecture: one report, four pages

Where technically viable, generate a single report containing these four pages:

1. Executive Overview
2. Financial Performance
3. Customer Performance
4. Product Performance

This is strongly preferred over four separate reports because page navigation should be native, fast and coherent.

Each page should retain its existing semantic content and visual quality.

If a single-report architecture is genuinely blocked by semantic-model constraints, document the limitation and implement a robust cross-report navigation alternative while still preserving stable URLs. But do not choose cross-report navigation merely because it is easier.

## 6. Multi-page builder support

Extend the renderer/builder generically so one deployment can contain multiple `PageSpec`/page definitions.

The architecture should support:

```text
ReportSpec
- report_name
- semantic_model binding
- pages[]
- default_page
- navigation definition
- design tokens
```

Do not hard-code the four current pages into the renderer. The report should accept an arbitrary ordered page list.

## 7. Preserve existing dashboard content

Use the accepted/latest versions of:

- Executive;
- Financial;
- Customer;
- Product.

Stage 12B is not a redesign of their analytical content.

Changes should focus on:

- navigation;
- persistent deployment;
- shared shell consistency;
- any small alignment fixes required by the new nav system.

Do not introduce unrelated chart/model rewrites.

---

# Part C — Functional navigation

## 8. Navigation must actually work

The left navigation must no longer be decorative text.

Implement native Power BI page navigation actions where possible.

Each page's nav must allow the viewer to move to all four pages without using the Power BI page tabs.

Acceptance:

- clicking Overview opens Executive Overview;
- clicking Financial opens Financial Performance;
- clicking Customers opens Customer Performance;
- clicking Products opens Product Performance;
- active-state styling updates correctly on each page;
- no broken action targets after in-place update;
- page IDs/actions are generated deterministically.

If page-navigation actions require page object names/IDs, generate them from the report spec rather than hard-coded literal IDs.

## 9. Navigation should survive updates

Prove that after an in-place report update:

- all four navigation actions still target the correct pages;
- active page styling remains correct;
- links do not retain obsolete page IDs;
- no manual reconfiguration is needed.

This must be included in the 3-update persistent-report test.

---

# Part D — Navigation visual redesign

## 10. Improve nav visual quality

The existing nav is functionally/basic. Bring it closer to the premium reference mockups and actual dashboards.

Desired language:

- restrained professional outline icons;
- no emoji-style iconography;
- low-contrast/faded inactive icons and labels;
- clear but subtle active state;
- consistent icon box size;
- consistent icon-to-label spacing;
- precise vertical rhythm;
- strong alignment;
- no oversized filled blocks;
- sophisticated hover/selected treatment where supported;
- compatible with the established dark navy shell.

The target is enterprise-product navigation, not decorative illustration.

## 11. Icon implementation

Use the most robust Power BI/PBIR-compatible route available.

Preferred options, in order:

1. native/simple vector shape/icon primitives;
2. renderer-owned inline SVG/image resources if reliably deployable zero-touch;
3. small text glyphs only if they render consistently and genuinely look professional.

Do **not** use emoji.

Icons should conceptually communicate:

- Overview/dashboard;
- Financial/chart/currency;
- Customers/users;
- Products/package/grid.

Keep them visually consistent as one icon set.

## 12. Central nav tokens/configuration

Add shared navigation tokens/config, e.g.:

```text
nav_width
item_height
item_gap
icon_size
icon_stroke
inactive_opacity
active_background
active_accent
label_font_size
label_color
active_label_color
left/right padding
```

All pages must consume the same nav system.

Changing navigation appearance should not require editing every dashboard config.

---

# Part E — Existing reports migration

## 13. Create the canonical combined report

Deploy a canonical report containing all four dashboards with working nav.

Suggested logical report name:

`ExecutiveAnalyticsDemo`

(or another existing naming convention if the repo already has one).

Capture its report ID and URL.

Then perform at least 3 real updates to the same canonical report during testing and prove identity is stable.

## 14. Existing standalone reports

Do not blindly delete the current four standalone reports.

Document their IDs/URLs and either:

- leave them untouched as historical evidence; or
- update them only if needed to demonstrate deployment compatibility.

The canonical future path should be the combined multi-page persistent report.

---

# Part F — Interaction and regression testing

## 15. Navigation interaction test

Use Playwright/headless browser to verify the nav interactions, not just inspect PBIR JSON.

At minimum automate:

1. load default/Overview page;
2. screenshot;
3. click Financial nav item;
4. assert Financial page title/content visible;
5. click Customers;
6. assert Customer page visible;
7. click Products;
8. assert Product page visible;
9. click Overview;
10. assert Executive page visible.

Capture evidence screenshots or a compact contact sheet.

## 16. Visual regression

For all four pages verify:

- correct active nav item;
- nav design is identical except active state;
- title/header alignment remains correct from 12A;
- donut centre remains visually acceptable where present;
- no overlap introduced by nav changes;
- all custom visuals populate;
- slicers remain functional;
- page content remains within canvas bounds.

## 17. Update regression

After each of the 3 in-place updates, rerun a lightweight interaction/render validation.

At minimum prove:

- same report ID;
- same URL;
- default page renders;
- one custom visual populated;
- page navigation still works.

---

# Tests

Add automated tests covering at least:

1. create-or-update decision logic;
2. stable logical report lookup;
3. update path does not call delete by default;
4. stable report ID across mocked update responses;
5. multi-page `ReportSpec` generation;
6. deterministic page IDs/names;
7. navigation actions target valid pages;
8. each page has exactly one active nav item;
9. no emoji remain in nav config/source;
10. all four current page configs can be assembled into one report;
11. custom visual packages are included once per report as required;
12. Stage 12A shared header/colour/donut systems remain intact;
13. existing test suite remains green.

Keep live Fabric/Playwright tests separate from routine unit tests where appropriate.

---

# Evidence package

Commit under:

`docs/stages/12b-persistent-deployment-and-navigation/`

Include:

- `REPORT.md`;
- canonical report ID/URL evidence;
- before/after update identity evidence for all 3 updates;
- navigation interaction evidence/screenshots;
- final screenshots of all four pages;
- deployment timing evidence;
- any update-path investigation notes;
- navigation design/token summary;
- test results.

Do not commit credentials/tokens.

---

# Hard acceptance criteria

Stage 12B is `PASS` only if all of the following are true:

- [ ] A generated report can be updated in place without changing report ID.
- [ ] Viewer/report URL remains stable across at least 3 consecutive updates.
- [ ] The update path does not rely on delete/create for normal updates.
- [ ] Private custom visuals still execute/populate zero-touch after each update.
- [ ] No custom visual consent/editor touch is required.
- [ ] Executive, Financial, Customer and Product exist in one coherent navigable report unless technically proven impossible.
- [ ] Left nav is genuinely clickable/functional.
- [ ] All four pages can be reached through the nav in headless interaction tests.
- [ ] Nav targets remain valid after in-place updates.
- [ ] Nav appearance uses professional outline-style iconography with no emoji.
- [ ] Nav styling is centrally configurable/reusable.
- [ ] Active state is correct on every page.
- [ ] Existing visual quality and Stage 12A improvements are not regressed.
- [ ] Existing automated tests plus new Stage 12B tests pass.

If stable update-in-place fundamentally conflicts with private custom visual execution, conclude `BLOCKED` and provide exact experimental evidence before proceeding to Stage 13. Do not quietly fall back to delete/create and claim success.

---

# REPORT.md requirements

Report must include:

- previous deployment architecture;
- new create-or-update architecture;
- exact REST/Fabric API path used for updates;
- 3-update report ID/URL stability table;
- custom visual execution result after each update;
- canonical combined report architecture;
- multi-page builder changes;
- page/navigation ID strategy;
- navigation action implementation;
- navigation visual design/token changes;
- screenshots/evidence for all four pages;
- Playwright click-navigation test results;
- automated test results;
- regressions/known limitations;
- canonical report ID and stable URL;
- conclusion: `PASS` or `BLOCKED`.

The key product outcome is:

> **A user receives one stable Power BI report URL whose content can be regenerated/updated repeatedly, while retaining working premium navigation across Executive, Financial, Customer and Product pages.**
