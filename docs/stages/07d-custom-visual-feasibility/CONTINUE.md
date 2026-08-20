# Stage 07d — Continue Feasibility Spike

The current Stage 07d REPORT is **not accepted as complete**. Continue the same stage. Do not create a new stage yet.

## Why this continues

The Premium KPI custom visual is promising and demonstrates materially greater rendering control than native Power BI cards. However, the original Stage 07d acceptance work is incomplete:

- Premium Chart was not built;
- three-run final visual assessment was not completed;
- reference-relative scoring against the same three premium reference standards was not completed;
- cross-filtering/selection was not tested;
- slicer/filter response was not tested;
- fully headless rendering without manual intervention was not proven;
- API deployment currently appears to require a manual editor “touch” to activate data binding.

Therefore the correct current conclusion is **PROMISING_BOUNDED_FOLLOWUP**, not STRONG_POSITIVE.

## Product goal remains unchanged

The visual target remains the same high-end premium executive standard established by the three reference examples used in Stage 07b/07c.

The result must ultimately feel comparable in design quality to those references, not merely “better than native Power BI”.

## Mandatory execution order

### 1. Solve or conclusively diagnose automatic data binding FIRST

Before investing heavily in more custom visuals, determine whether a programmatically deployed custom visual can be fully bound and rendered **without any manual Power BI editor interaction**.

Investigate:

- PBIR custom visual query/dataTransform/schema requirements;
- custom visual identity/GUID references;
- capabilities/dataRoles mapping;
- semantic query binding structure;
- whether visualContainer/config/query fields differ from native visuals;
- whether an export from a manually working custom visual can be diffed against the generated PBIR;
- whether the manual “touch” simply causes Power BI to emit missing metadata that can be generated directly;
- whether organizational visual registration changes binding behaviour;
- whether direct Fabric REST deployment preserves all required metadata.

Preferred debugging method:

1. create a manually working Premium KPI instance;
2. export/download/inspect the resulting PBIP/PBIR if possible;
3. diff its visual definition against the programmatically generated one;
4. identify the minimal missing metadata;
5. update the renderer to emit that metadata;
6. deploy a fresh report and prove the KPI renders with data on first load.

Acceptance for this item:

> A freshly deployed report loads the Premium KPI with the correct bound value in headless Fabric rendering **without any manual editor touch**.

If this is genuinely impossible, document exact evidence before proceeding to a negative feasibility conclusion.

### 2. Build the missing Premium Chart

Implement one reusable chart custom visual suitable for a major Executive Overview visual.

Prefer a line or bar/column family already present in the frozen Stage 02a dashboard.

The chart must demonstrate real custom rendering control over:

- plot area geometry;
- typography;
- axis styling;
- gridlines;
- series styling;
- colour palette;
- legend placement;
- data labels/tooltips where appropriate;
- internal spacing;
- title/context treatment if component-owned;
- hover/selection states;
- responsive sizing.

Use SVG/Canvas/D3 or equivalent appropriate custom-visual rendering techniques.

Do not build a static decorative mock. It must bind to real semantic-model data.

### 3. Implement minimum interaction support

For the custom chart, implement and test at minimum:

- selection identity;
- `selectionManager` or appropriate Power BI interaction API;
- response to slicer/filter context;
- cross-filter/highlight behaviour where supported;
- tooltip behaviour if present.

For the KPI, prove it updates in response to at least one slicer/filter context even if it does not itself initiate cross-filtering.

Record any interaction limitations clearly.

### 4. Integrate KPI + Chart into the real Executive Overview

Create a fresh deployed Executive Overview variant using:

- the Premium KPI across the KPI band where feasible;
- the Premium Chart for at least one hero/major analytical visual;
- the strongest existing generic page composition/design language for surrounding content;
- unchanged analytical bindings and frozen Stage 02a semantics.

No manual editing after deployment is permitted for final evidence.

### 5. Fully headless proof

The final integration must be proven through the automated path:

```text
render
→ deploy via API
→ headless embed-token browser load
→ wait for rendered state
→ screenshot
```

No manual Power BI Desktop/Fabric editor intervention between deployment and screenshot.

Capture evidence showing the custom KPI and chart are both populated on first headless load.

### 6. Visual quality iteration

Once fully automatic rendering works, tune the custom KPI and chart visually against the same three premium references.

Focus on the dimensions that native visuals could not control:

- refined typography;
- internal whitespace;
- bespoke KPI composition;
- chart plot proportions;
- custom axes/gridlines;
- legend/chrome restraint;
- surfaces and accents;
- hover/interaction polish;
- responsive balance.

The goal is a **step-change**, not incremental improvement.

### 7. Mandatory three-run visual-only assessment

For the final fully automated Executive screenshot, run the same visual-only assessment at least 3 times with the same model/configuration where practical.

The rubric must explicitly ignore frozen analytical-choice defects and score visual presentation only:

- first-impression professionalism;
- executive credibility;
- composition/hierarchy;
- typography;
- whitespace/rhythm;
- KPI treatment;
- colour discipline;
- surface/container quality;
- chart presentation;
- visual consistency;
- premium/brand feel;
- demo readiness;
- company-wide presentation readiness.

Record all runs, medians and ranges. No cherry-picking.

### 8. Mandatory binary judgments

On each of the 3 runs ask:

1. “Ignoring analytical-choice defects and judging visual presentation only, would you be comfortable presenting this exact dashboard design to the executive committee of a large enterprise?”
2. “If shown full-screen at a company-wide town hall or leadership presentation, would its visual quality make the product/team look highly professional?”
3. “Does this visually feel materially closer to a premium bespoke executive dashboard than to a well-formatted default Power BI report?”

Report YES/NO for all three runs.

### 9. Reference-relative scoring

Compare the final custom-visual Executive screenshot against the same three feasible premium references on a 0–100 design-quality scale, where 100 means equal overall design quality rather than pixel identity.

Report:

- score against each reference;
- median score;
- best-feasible-reference score;
- remaining gaps;
- which gaps are solvable by expanding the custom visual library;
- which gaps remain constrained by Power BI host/report-canvas behaviour.

### 10. Final decision gates

Use these exact categories.

#### STRONG_POSITIVE

Only if all of the following are true:

- fully automatic API deployment + first-load data binding works;
- Premium KPI and Premium Chart both render populated headlessly;
- slicer/filter response works;
- chart selection/cross-filter behaviour is demonstrated at a credible minimum level;
- median overall visual score ≥ **7.0/10**;
- KPI treatment ≥ **7.5/10**;
- chart presentation ≥ **7.0/10**;
- premium/brand feel ≥ **7.0/10**;
- executive credibility ≥ **7.5/10**;
- demo readiness ≥ **7.5/10**;
- at least 2/3 YES for executive presentation;
- at least 2/3 YES for bespoke-vs-default-Power-BI;
- best-feasible reference-relative score ≥ **70/100**;
- remaining gaps have a credible route via a reusable custom visual library.

#### PROMISING_BOUNDED_FOLLOWUP

Only if:

- automatic deployment is proven or has one very narrow, well-understood missing metadata issue;
- custom visuals materially outperform native/composite output;
- median overall score is approximately **5.5–6.9**;
- reference parity approximately **55–69/100**;
- remaining gaps are bounded and technically credible.

If this category is used, recommend **one** tightly scoped next experiment only.

#### NEGATIVE

Use if:

- automatic binding cannot be achieved without manual intervention;
- or custom chart rendering/interaction is operationally unsuitable;
- or median visual score remains < **5.5**;
- or reference parity remains < **55/100**;
- or executive/bespoke judgments remain predominantly NO.

If NEGATIVE, recommend reconsidering the Power BI-native delivery constraint rather than continuing visual engineering indefinitely.

## Ultimate product bar remains higher

Even a STRONG_POSITIVE 07d result does **not** mean the product is visually complete.

It only proves the route.

A subsequent custom-visual-library stage must still hit the original premium standard:

- overall visual score ≥ **7.5/10**;
- executive credibility/demo readiness/company-wide readiness ≥ **8.0**;
- no core visual dimension below **7.0**;
- reference-relative quality ≥ **80/100**;
- dashboard genuinely comparable in standard to the three premium reference examples.

## Evidence required

Update `docs/stages/07d-custom-visual-feasibility/REPORT.md` and commit:

- automatic binding investigation/diff evidence;
- fully automatic fresh-deployment screenshot;
- Premium Chart source/build notes;
- KPI + Chart integrated Executive screenshot;
- interaction test evidence;
- three complete final critic runs;
- medians/ranges;
- binary judgments;
- 0–100 comparison against each premium reference;
- native/composite/custom comparison;
- tenant/security/organizational visual implications;
- automated test/build results;
- final category: `STRONG_POSITIVE`, `PROMISING_BOUNDED_FOLLOWUP`, or `NEGATIVE`.

Do not reuse or infer user approval. Only record user confirmation if the user actually provided it.
