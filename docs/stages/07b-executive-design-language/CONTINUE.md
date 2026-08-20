# Stage 07b — Completion Pass

The existing Stage 07b REPORT is **PARTIAL and not accepted as completion**. Continue Stage 07b. Do not create Stage 08.

## Why this is reopened

The current rendered result remains below the product requirement:

- overall visual score ~4.4/10;
- `polish_premium` ~2.8;
- typography ~5.1;
- whitespace ~4.1;
- required premium reference mockups were not generated;
- required three-run assessment was not completed.

Architecture completion is not acceptance. Month sorting and mixed-scale axes may affect analytical credibility, but they do not explain weak premium polish, typography or whitespace. Do not fix or use those analytical defects as a reason to stop this stage.

## Frozen scope

Do **not** change month sorting, mixed axes, visual types, DAX, semantic-model analytical design, Stage 02a analytical content or the business story. Improve only generic renderer-owned visual presentation: composition, page templates, typography, whitespace, KPI treatment, surfaces, colour, structural primitives, chart chrome and visual hierarchy. No retail-specific hacks.

## Mandatory sequence

### 1. Generate references first

Generate and commit at least three premium Executive Overview mockups representing the same broad analytical content:

1. premium Executive Light / boardroom;
2. Corporate Editorial / publication-inspired;
3. sophisticated modern enterprise / high-design BI.

Use the strongest available image-generation capability. Keep them plausibly approximable with native Power BI rather than sci-fi UI.

For each reference extract reusable principles for page identity, composition, KPI band, hero treatment, sections, whitespace, typography, colour, surfaces, chart chrome, filters, navigation and density. Classify each principle as `native_powerbi_direct`, `native_powerbi_approximation`, or `not_suitable`.

### 2. Diagnose the current screenshot visually

Ignoring analytical defects, document why the current 07b screenshot still looks ordinary. Explicitly assess first impression, hierarchy, page identity, region proportions, whitespace, KPI proportions, typography, surfaces, colour, focal point, wall-of-tiles residue and hero/supporting balance.

### 3. Iterate materially on generic design rules

Use repeated:

`reference principles → generic template change → deploy → headless screenshot → visual-only assessment → inspect → refine`

Do not stop after one iteration. Region percentages are provisional. Explore materially different generic compositions until there is an obvious one-second focal hierarchy, a genuinely dominant hero area, a coherent premium KPI system, subordinate supporting content, deliberate breathing room and no wall-of-tiles effect.

Structural primitives must earn their pixels. Refine/remove weak header bands, KPI backgrounds, dividers or labels. Use proven-safe native shapes/text/background bands/accent rules only where they improve hierarchy.

### 4. Typography must become a design feature

The current ~5.1 typography score is not acceptable. Create an editorial hierarchy for page title, context/subtitle, section labels, KPI values/labels, chart titles and muted axis/legend/table text. Do not merely enlarge fonts; tune weight, contrast, alignment, available box height and spacing.

### 5. KPI band must look bespoke

Iterate card proportions, internal spacing, label/value relationship, surfaces, restrained accents, baseline alignment, display units and generic priority emphasis. It must read as one designed system, not independent default cards. Do not invent trends/deltas/icons unsupported by the spec.

### 6. Whitespace is a hard requirement

Current ~4.1 whitespace score is a direct failure. Tune outer margins, header/filter/KPI spacing, card gaps, hero isolation, section gaps, chart gutters and title-to-plot spacing. Avoid both cramped layouts and purposeless voids.

### 7. Premium polish is the primary failure signal

Current `polish_premium` ~2.8 must materially change. Push proven-safe styling toward coherent canvas/surface contrast, subtle grouping, disciplined borders/radius/depth where safe, neutral-first palettes, intentional accent use, curated series colours and semantic colours reserved for meaning. The dashboard should look designed before the viewer reads the data.

### 8. Polish chart presentation without changing chart types

Improve plot proportions, title alignment, axes/gridline restraint, legend positioning, backgrounds/containers, colour discipline, internal padding and alignment across related charts. Charts should feel native to one composition.

## Visual-only acceptance rubric

The critic must explicitly ignore month ordering, mixed units/axes, alternative chart choices, data-story choices and semantic-model issues. Score visual presentation only:

- first-impression professionalism;
- executive credibility;
- composition/hierarchy;
- typography;
- whitespace/rhythm;
- KPI treatment;
- colour discipline;
- surface/container quality;
- chart presentation;
- section coherence;
- visual consistency;
- premium/brand feel;
- demo readiness;
- company-wide presentation readiness.

Compare against generated references for **level of design quality**, not pixel similarity.

## Mandatory three-run final assessment

For the final Executive screenshot run the same visual-only assessment at least three times with the same model/configuration where practical. Record every run, median and range. No cherry-picking.

## Hard Executive gates

Stage 07b is not complete unless:

- median overall visual-design score ≥ **7.5/10**;
- executive credibility ≥ **8.0**;
- demo readiness ≥ **8.0**;
- company-wide presentation readiness ≥ **8.0**;
- premium/brand feel ≥ **7.5**;
- composition/hierarchy ≥ **7.5**;
- typography ≥ **7.0**;
- whitespace/rhythm ≥ **7.0**;
- KPI treatment ≥ **7.5**;
- colour discipline ≥ **7.0**;
- surface/container quality ≥ **7.0**;
- no core visual dimension median below **7.0**.

Do not average away a weak fundamental dimension.

On each run ask:

1. “Ignoring analytical-choice defects and judging visual presentation only, would you be comfortable presenting this exact dashboard design to the executive committee of a large enterprise?” — require YES ≥2/3.
2. “If shown full-screen at a company-wide town hall or leadership presentation, would its visual quality make the product/team look highly professional?” — require YES ≥2/3.
3. “Does this visually feel materially closer to a premium bespoke executive dashboard than to a well-formatted default Power BI report?” — require YES ≥2/3.

## Reference-relative gate

Score the final native result 0–100 against each feasible generated reference for overall design quality, excluding genuinely infeasible fantasy elements. Require median relative quality against the best/most feasible reference ≥ **75/100**, and no conclusion that the output still primarily resembles “default Power BI with formatting.”

## Human-inspection gate

REPORT must explicitly answer:

- Is focal hierarchy obvious within one second?
- Does the page have distinctive visual identity?
- Do KPIs read as a coherent premium system?
- Is whitespace deliberate?
- Does typography create authority?
- Are surfaces/colours restrained and sophisticated?
- Do charts feel integrated into one composition?
- Is removable default-Power-BI residue still visible?
- Would it look credible full-screen in an executive meeting?
- What remains behind the references?

A “no” to any of the first seven means continue iterating unless a concrete native Power BI limitation is demonstrated.

## All pages and cross-domain proof

After Executive passes, apply the mature language to Regional, Category and Risk pages. Each secondary retail page must score ≥ **7.0/10** visual-only and cannot look like a default fallback.

Render actual visual evidence for finance and SaaS/operations executive fixtures using the same generic Executive Light language. Each should score ≥ **7.0/10** or have a documented rendering-only limitation. Structural tests alone are insufficient.

## Functionality gates

Every iteration must preserve report loading, four retail pages, all 29 source visuals, visible/usable slicers, all 11 measures, successful semantic refresh, valid bindings, no broken visual icons, no overlays obscuring data, no typography clipping and deterministic output.

## No fixture hacks

No branches/constants based on retail page names, metrics, fields, IDs, displayed values, UK labels or fixture-specific coordinates. Behaviour must derive from page archetype, visual priority/family, count/density, theme tokens and composition regions.

## Blocked outcome

If the gates cannot be reached, do **not** call architecture completion success. A blocked result requires concrete evidence for each claimed native Power BI limitation: desired effect, attempted mechanisms, rendered evidence, why generic renderer work cannot close the gap and closest achievable native treatment. If composition, typography, whitespace, surfaces or colour can still improve, Stage 07b remains in progress.

## Evidence required

Commit:

- ≥3 premium reference mockups;
- reference-principles analysis;
- pre-completion screenshot;
- iteration screenshots/contact sheet;
- final four retail screenshots;
- finance and SaaS screenshots/previews;
- `EXECUTIVE_DESIGN_ASSESSMENT.json` with all final runs, medians/ranges and binary judgments;
- `DESIGN_LANGUAGE_MANIFEST.json`;
- reproducible visual-only critic rubric;
- newly discovered compatibility evidence if applicable.

Update the existing `REPORT.md` with the completion-pass results. Explicitly answer:

> **Does the default generated dashboard now meet the visual standard of a premium executive dashboard that we would proudly demo to senior leadership or show company-wide?**

Do not answer yes unless the hard gates are met.
