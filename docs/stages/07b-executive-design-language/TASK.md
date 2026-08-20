---
stage: 07b
status: ready
title: Executive design language and premium page templates
---

# Stage 07b — Executive Design Language & Premium Page Templates

## Context

Stages 07 and 07a established a competent enterprise baseline and a safe Power BI styling foundation. We now know which styling mechanisms can be trusted in live Fabric rendering, and the current reports are professional, functional, legible, and analytically credible.

That is not the target for this stage.

The target is a **step-change in visual ambition**:

> A generated dashboard should feel intentionally designed, premium, polished and executive-demo ready — visually comparable in standard to high-end dashboard mockups produced by strong image-generation/design systems, while remaining a real native Power BI report.

The desired reaction should move from:

> “This looks professional and shows the data well.”

To:

> “Wow — this looks genuinely premium. I would be comfortable showing this to senior leadership or the whole company.”

This stage is about **composition, art direction and reusable page-template design**, not about fixing one retail report.

## Objective

Create a reusable premium design-language and page-template system that transforms the same analytical dashboard content into a significantly more visually impressive native Power BI experience.

The Stage 02a retail dashboard remains the main proof fixture, but no retail-specific styling, IDs, text, metric names or logic may be embedded into the implementation.

The deliverable is not just a prettier theme. It is a reusable **composition system** that controls page architecture, hierarchy, sections, visual emphasis and decorative structure in addition to typography, colour and formatting.

## Reference standard

Use the visual standard of excellent modern enterprise dashboard mockups as the quality bar: strong hierarchy, restrained visual density, deliberate whitespace, clear page identity, polished KPI treatment, confident typography, subtle depth, disciplined colour and a sense that the page was composed by a skilled designer rather than assembled from default BI tiles.

Do not pixel-copy any single mockup. Extract reusable design principles.

## Core design shift

Current baseline is approximately:

```text
logical grid
  → place visuals
  → format each visual professionally
```

Stage 07b should move toward:

```text
choose page archetype
  → establish page identity and hierarchy
  → allocate designed visual regions
  → reserve structural/whitespace zones
  → place visuals into those regions
  → apply role-aware visual styling
  → add native decorative structure where appropriate
```

The report must read as one composition, not a collection of independently styled visuals.

## Read first

1. Read `KIRO.md`.
2. Read Stage 06, 07 and 07a TASK/REPORT files.
3. Inspect Stage 06 reference image and all Stage 07/07a screenshots.
4. Inspect `EnterpriseDesignSystem`, formatting capability registry and the styling compatibility evidence.
5. Inspect current layout/page-generation architecture.
6. Inspect working PBIR examples for text boxes, shapes, buttons, backgrounds, containers and other native decorative primitives before implementing them.
7. Preserve the Stage 02a analytical content for the principal before/after comparison unless a tiny presentational metadata field is required; do not alter measures, data story or visual semantics to manufacture a higher aesthetic score.

## Required work

### 1. Introduce page archetypes

Create an explicit reusable page-archetype layer that sits between `PageSpec` intent and raw canvas placement.

At minimum implement these generic archetypes:

- `executive_overview`
- `diagnostic_analysis`
- `comparison_analysis`
- `risk_detail`

Exact names are implementation decisions, but the concepts must exist.

Each archetype should define a composition grammar rather than fixed retail-specific coordinates.

Examples of reusable regions:

- page identity/header zone;
- filter/context zone;
- hero KPI zone;
- primary insight zone;
- secondary insight zone;
- supporting detail zone;
- footer/context zone where useful.

Archetype selection should derive from `PageSpec.role`, visual priorities, and visual families.

### 2. Executive Overview composition

The Executive Overview is the primary quality benchmark.

Create a premium executive composition with clear regions such as:

- strong page identity/header area;
- concise contextual subtitle or period context where derivable without inventing business meaning;
- compact integrated filter controls;
- coherent KPI band with strong value emphasis;
- one visually dominant hero analysis area;
- secondary supporting analysis;
- generous whitespace and alignment rhythm.

Do not make every visual equal in size or visual weight.

### 3. Native structural primitives

Explore and safely use native Power BI primitives to improve composition, including where supported:

- text boxes;
- shapes/rectangles;
- lines/dividers;
- section labels;
- buttons only where functionally useful;
- background bands/panels;
- subtle visual containers;
- icons only if native, reliable and semantically justified.

Use them to create visual structure and hierarchy, not decoration for its own sake.

No fake Power BI app chrome.

### 4. Page identity system

Introduce a deliberate page-level identity treatment.

It should support:

- page title;
- optional concise subtitle/context;
- page-role-aware hierarchy;
- restrained accent treatment;
- consistent placement across archetypes;
- visually separated content region below.

This must be generated from existing structured metadata where possible. Do not invent unsupported claims or metrics.

### 5. KPI system v2

Upgrade KPI cards from “styled Power BI cards” into a coherent executive KPI band.

Generic design expectations:

- strong callout values;
- compact, clear metric labels;
- consistent alignment and height;
- intentional surface treatment;
- restrained semantic colour accents;
- appropriate display units;
- balanced whitespace;
- subtle emphasis differences based on priority;
- optional contextual microcopy only when available from existing spec metadata.

Do not fabricate trends, arrows or deltas unless the spec/model provides them.

### 6. Hero visual treatment

Introduce a concept of a hero visual/hero analysis region.

Selection should derive generically from:

- page role;
- visual priority;
- visual family;
- relative analytical importance.

The hero region should receive stronger spatial emphasis and cleaner surrounding composition than supporting visuals.

This is a layout/composition decision, not a change to analytical meaning.

### 7. Section hierarchy

Use section labels/background grouping/dividers where helpful to make complex pages readable at a glance.

Examples of generic section concepts:

- Performance
- Drivers
- Mix
- Risks
- Detail

However, do **not** hard-code these labels unless they can be derived safely from existing page/visual metadata. Generic structural section titles may be generated only from deterministic mappings of page/visual role semantics.

### 8. Whitespace as a first-class design element

Create explicit whitespace rules by archetype.

Requirements:

- stronger outer margins than purely functional minimums where canvas permits;
- generous spacing around page identity and KPI zones;
- consistent inter-section spacing;
- intentional breathing room around the hero visual;
- avoid dense “Power BI wall of tiles” composition;
- allow some unused canvas if it improves hierarchy.

A premium dashboard does not need to maximize occupied pixels.

### 9. Visual density policy

Introduce page-role-aware density rules.

Executive pages should be more restrained than detail pages.

For example:

- executive overview: fewer, larger, more intentional regions;
- diagnostic page: moderate density;
- risk/detail page: can support denser tabular content while preserving hierarchy.

Do not delete source visuals to achieve density. Instead use the archetype to distribute and size them more intelligently. If a page genuinely contains too many visuals for a premium composition, record that as a future spec-level issue rather than silently omitting content.

### 10. Premium surface language

Build on the 07a safe-list to create a coherent surface vocabulary.

Where empirically safe, test and apply:

- light card surfaces;
- subtle border hierarchy;
- restrained radius;
- very subtle depth/shadow if safe;
- section background bands;
- contrast between page background and content surfaces;
- accent edges/lines used sparingly.

Avoid heavy boxes around every chart.

### 11. Typography art direction

Extend the typography hierarchy beyond generic defaults.

Create a deliberate scale for:

- page title;
- page subtitle/context;
- section label;
- visual title;
- KPI label;
- KPI value;
- axis/legend/table text.

The system should feel editorial and intentional, not simply larger/smaller default fonts.

Use only proven Power BI-supported fonts/properties.

### 12. Colour art direction

Use theme colours with stronger restraint and purpose.

Generic principles:

- mostly neutral surfaces and text;
- one dominant accent family;
- semantic positive/negative/warning reserved for meaning;
- avoid rainbow categorical overload;
- use accent colour to guide attention through the page;
- preserve accessible contrast.

For a premium executive report, colour should feel curated rather than merely available.

### 13. Chart-container choreography

Improve how charts sit within the page composition.

Examples:

- align titles and plot areas across related visuals;
- use consistent title placement;
- reduce unnecessary internal chrome;
- create visual continuity between adjacent related charts;
- size supporting visuals relative to their analytical role;
- use consistent baseline heights and aligned edges.

### 14. Navigation and context polish

Where current report semantics support multiple pages, create a restrained, native navigation treatment if it can be done safely.

This may include:

- page navigation buttons;
- subtle current-page indication;
- compact footer/header navigation strip.

Do not let navigation dominate the dashboard.

If native page navigation is not robust enough, defer rather than adding brittle UI.

### 15. Create visual-language variants

Implement at least **three reusable premium visual languages** sharing the same composition engine but varying art direction.

Required variants:

1. **Executive Light** — spacious, premium, restrained, boardroom-oriented.
2. **Executive Dark** — high-impact, sophisticated, suitable for command-centre/executive presentation without gaming-style excess.
3. **Corporate Editorial** — strong typography, publication-like hierarchy, asymmetric but disciplined composition.

Optional fourth:

4. **Dense Analytical** — information-rich while still polished.

The same page/spec should be renderable through different visual languages without analytical changes.

### 16. Default language selection

For the Stage 07b primary proof, use `Executive Light` unless existing theme intent strongly conflicts.

Add a deterministic mapping from `ThemeSpec`/design intent to visual language where reasonable.

Do not ask the user to choose between variants unless future product UX requires it.

### 17. Golden reference generation for development

Generate **at least three high-quality reference mockups** for the same Executive Overview analytical content using the current best available image-generation model.

Purpose:

- extract reusable composition/design ideas;
- compare design languages;
- identify missing native Power BI primitives;
- set a genuinely ambitious visual target.

Do not directly implement impossible fantasy UI.

For each reference, annotate internally which design principles are:

- directly implementable in native Power BI;
- approximable;
- not appropriate/feasible.

Commit only safe synthetic-data references.

### 18. Frozen analytical fixture

For the main before/after comparison:

- use the same Stage 02a DashboardSpec analytical content;
- preserve measures;
- preserve data;
- preserve visual semantics/types;
- preserve page count;
- preserve all source visuals unless Power BI itself forces a documented fallback.

Stage 07b may change **presentation composition and renderer-owned placement**, but not analytical design merely to improve appearance.

### 19. Headless render evidence

After implementing the design language:

1. rerender the unchanged retail fixture;
2. redeploy using the proven direct-report Fabric deployment path;
3. confirm refresh/runtime health;
4. capture all four pages headlessly;
5. capture at target 16:9 executive presentation size;
6. commit screenshots.

### 20. Human-style executive visual review rubric

Create a separate visual-quality assessment rubric focused specifically on **presentation quality**, not analytical correctness.

Score at least:

- first-impression professionalism;
- executive credibility;
- composition/hierarchy;
- typography;
- whitespace;
- KPI treatment;
- colour discipline;
- surface/container quality;
- chart presentation;
- section coherence;
- visual consistency;
- brand/premium feel;
- demo readiness;
- company-wide presentation readiness.

This rubric must intentionally **exclude** known analytical/spec defects such as month sort or mixed axes from the visual-design score, so baseline aesthetics can be judged independently.

### 21. Strong acceptance threshold

This stage should have a genuinely ambitious bar.

For the Executive Overview:

- run at least 3 assessment passes;
- report median and range;
- **median visual-design score must be ≥7.5/10**;
- no individual core presentation dimension (`composition/hierarchy`, `typography`, `whitespace`, `KPI treatment`, `colour discipline`, `surface quality`) may score below 7.0 median;
- `executive credibility` median ≥8.0;
- `demo readiness` median ≥8.0.

Additionally, ask the critic the binary question:

> “Ignoring analytical-choice defects and judging visual presentation only, would you be comfortable presenting this exact dashboard design to the executive committee of a large enterprise?”

Acceptance requires **YES on at least 2 of 3 assessment runs**.

Ask separately:

> “Would this look visually credible if shown company-wide in an internal town hall or leadership presentation?”

Acceptance requires **YES on at least 2 of 3 runs**.

Do not lower these thresholds merely because Power BI is harder to style than an image mockup.

### 22. Relative reference standard

Compare the final Executive screenshot against the three generated Stage 07b reference mockups.

The goal is not pixel fidelity. Assess whether the native Power BI output achieves the same **level of intentional design quality** across:

- hierarchy;
- spacing;
- polish;
- visual confidence;
- premium feel;
- coherence.

The report must explicitly state where native Power BI remains visibly behind the references and why.

### 23. All-four-page consistency

The other three pages must also feel like part of the same product, not like neglected secondary pages.

Capture and assess:

- Regional Analysis;
- Category Analysis;
- Risk Analysis.

Requirements:

- consistent page identity;
- consistent typography and surfaces;
- archetype-appropriate density;
- coherent filters/navigation;
- no visual regression;
- no obvious default-Power-BI-looking page left behind.

### 24. Cross-domain proof

Use the Stage 07 finance and SaaS/operations fixtures to prove the template system is generic.

At minimum generate structural screenshots or rendered previews for:

- one finance-style executive overview;
- one SaaS/operations executive overview.

They should visibly inherit the same premium design language without retail assumptions.

### 25. No fixture hacks

Automated/static checks should fail if implementation logic references:

- retail page names;
- retail metric names;
- Stage 02a visual IDs;
- specific retail field names;
- fixed UK-specific labels;
- hard-coded retail colours.

All behaviour must derive from generic semantic roles/archetypes/design tokens.

### 26. Runtime and analytical safety

Premium styling must not regress functionality.

Verify:

- report opens without spinner;
- all four pages render;
- all 29 source visuals preserved;
- generated slicers remain usable and in-bounds;
- all 11 measures still evaluate;
- semantic model refresh succeeds;
- no broken visual icons;
- no clipping caused by decorative structure;
- no important content obscured by overlays.

### 27. Evidence package

Commit a clear evidence package under:

`docs/stages/07b-executive-design-language/`

Include at minimum:

- 3 generated executive reference mockups;
- final screenshots for all four retail pages;
- finance/SaaS visual evidence;
- `EXECUTIVE_DESIGN_ASSESSMENT.json` with the 3-run scores and binary judgments;
- `DESIGN_LANGUAGE_MANIFEST.json` describing selected archetypes/language/tokens used;
- any compatibility notes for newly used structural primitives.

### 28. Iteration within the stage

Unlike Stage 07/07a, Stage 07b is allowed to iterate repeatedly on **generic composition/template rules** until the acceptance threshold is met or a hard native-Power-BI limitation is demonstrated.

Use the image references and visual-only critic as development feedback.

Do **not** mutate the DashboardSpec to fix analytical issues during this stage.

### 29. Failure handling

If the ≥7.5 visual-design threshold is not reached:

- do not declare success merely because screenshots look somewhat better;
- identify the specific remaining visual deficits;
- distinguish renderer/template limitations from Power BI platform limitations;
- continue iterating on generic templates where technically feasible;
- if a Power BI limitation is genuinely blocking the target, provide concrete screenshot evidence and explain the closest achievable native result.

### 30. Design-system documentation

Document the reusable design language as an executable product contract, including:

- archetypes;
- region grammar;
- spacing rhythm;
- typography hierarchy;
- surface treatment;
- KPI treatment;
- hero visual rules;
- colour policy;
- navigation policy;
- density by page role;
- design-language variants;
- mapping from ThemeSpec/design intent to visual language;
- native Power BI limitations.

## Suggested architecture

Conceptually:

```text
renderer/
  design_language/
    archetypes.py
    regions.py
    variants.py
    composition.py
    primitives.py

  design_system.py
  layout.py
  formatting/
```

The exact structure is flexible. The important separation is:

- `DashboardSpec` owns analytical intent;
- page archetypes own composition grammar;
- design-language variants own art direction;
- design-system tokens own styling values;
- renderer/PBIR layer owns safe native Power BI realization.

## Tests

Add meaningful automated tests covering at minimum:

1. page-archetype selection;
2. archetype region generation;
3. executive hierarchy from visual priorities;
4. whitespace/gutter rules;
5. hero visual selection;
6. KPI-band composition;
7. page identity primitive generation;
8. variant token generation for Executive Light/Dark/Corporate Editorial;
9. deterministic render;
10. all decorative primitives remain within canvas bounds;
11. all source visuals preserved;
12. no retail-specific identifiers/constants;
13. finance fixture rendering;
14. SaaS/operations fixture rendering;
15. runtime-safe PBIR structure for newly used shapes/textboxes/buttons;
16. full existing suite remains green.

Live visual-quality assessment remains separate from routine unit tests.

## Non-goals

Do NOT expand Stage 07b into:

- changing visual types to solve mixed-scale analytical issues;
- adding MonthNumber or other semantic-model fixes;
- autonomous critic-driven spec mutation;
- conversational dashboard revision;
- custom Power BI visuals;
- production UX for choosing templates;
- fake image-only dashboard delivery;
- pixel-perfect reproduction of image-model mockups;
- external CSS/browser overlays that are not part of the actual Power BI report.

Everything visible in the accepted screenshots must come from the deployed native Power BI artifact.

## Acceptance criteria

Stage 07b is complete only when all of the following are true:

### Architecture
- reusable page archetypes exist;
- at least 3 premium design-language variants exist;
- Executive Overview uses an archetype-based composition rather than raw grid placement;
- decorative structural primitives are reusable and generic;
- no retail-specific hacks are present.

### Native Power BI fidelity
- final output is a real deployed native Power BI report;
- report loads normally in Fabric;
- all 4 pages render headlessly;
- all 29 source visuals remain present;
- slicers remain visible/usable;
- all 11 measures remain functional;
- semantic refresh succeeds.

### Visual quality
- 3 visual-only assessment runs completed;
- median Executive visual-design score ≥7.5/10;
- median executive credibility ≥8.0;
- median demo readiness ≥8.0;
- no core presentation dimension below 7.0 median;
- at least 2/3 runs answer YES to executive-committee presentation suitability;
- at least 2/3 runs answer YES to company-wide presentation suitability;
- all four pages show coherent premium design language;
- finance and SaaS/operations examples visibly inherit the same standard.

### Evidence
- 3 reference mockups committed;
- all four final retail screenshots committed;
- cross-domain visual evidence committed;
- assessment JSON committed;
- design-language manifest committed;
- report documents native Power BI gaps versus reference quality honestly.

### Engineering
- full automated test suite passes;
- no runtime regression;
- no analytical correctness regression;
- all new composition primitives have regression coverage.

If these visual-quality thresholds are not met, `REPORT.md` must state the stage is **not yet complete** unless a hard documented native Power BI limitation makes the target unattainable and the closest achievable result is demonstrated with evidence.

## REPORT.md requirements

Include:

- implementation summary;
- architecture of page archetypes/design-language variants;
- three reference mockups and the reusable design principles extracted from them;
- which reference ideas were directly implementable, approximated, or rejected;
- exact native Power BI structural primitives added;
- Executive composition before/after explanation;
- KPI system improvements;
- whitespace/density changes;
- typography hierarchy;
- colour/surface strategy;
- page identity/navigation treatment;
- all four final screenshots;
- finance and SaaS evidence;
- three-run visual-only scores with median/range;
- binary executive/company-wide judgments per run;
- evidence that DashboardSpec analytical content remained frozen;
- runtime/measure/refresh verification;
- automated test result;
- Power BI-specific limitations preventing closer reference parity;
- explicit answer to:

> **Does the default generated dashboard now look visually strong enough that we would confidently demo it to senior executives or a company-wide audience without first apologising for the design?**

- recommendation on whether the project is finally ready to proceed from baseline design work into critic-driven/spec-level optimisation.

Do not edit this `TASK.md` to mark completion. `REPORT.md` is the completion record.
