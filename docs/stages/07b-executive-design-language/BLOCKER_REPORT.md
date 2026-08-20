# Stage 07b — Blocker Report & Options

## Current State

The architecture is complete and functional:
- Page archetypes with composition regions ✅
- 3 design language variants (Light, Dark, Editorial) ✅
- Structural primitives (header bands, section backgrounds) ✅
- Composition engine replacing raw grid placement ✅
- Report deploys with 105 parts, all 4 pages render ✅
- 373 tests pass ✅
- 3 premium reference mockups generated ✅

## The Blocker

**Visual-only critic scores plateau at 2.3–3.2/10 regardless of PBIR formatting applied.** Target is ≥7.5.

The critic compares our deployed Power BI report against generated reference mockups and consistently identifies the output as "default Power BI with formatting" rather than "premium bespoke dashboard."

### What we CAN control (and have maximised):

| Capability | Status | Mechanism |
|-----------|--------|-----------|
| Page background colour | ✅ Applied | Page objects |
| Visual background (white surfaces) | ✅ Applied | PBIR general.background |
| Visual titles | ✅ Applied | PBIR general.title |
| KPI callout font size | ✅ Applied | theme.json textClasses.callout |
| Data palette colours | ✅ Applied | theme.json dataColors |
| Chart axis title suppression | ✅ Applied | PBIR showAxisTitle=false |
| Chart gridlines | ✅ Applied | PBIR gridlineShow |
| Category labels on cards | ✅ Applied | PBIR categoryLabels.show |
| Slicer placement (visible, top) | ✅ Applied | Composition engine |
| Visual hierarchy (hero/supporting) | ✅ Applied | Archetype regions |
| Section gap/whitespace | ✅ Applied | Region proportions |

### What we CANNOT control (the gap):

| Limitation | Impact | Why |
|-----------|--------|-----|
| Card internal padding/layout | Cards look "default" | Fixed by Power BI rendering engine |
| Chart plot area proportions | Charts look "standard" | Fixed internal visual rendering |
| Border rendering style | Can't achieve subtle design borders | Only on/off, no radius in practice |
| Shadow/depth | No modern card elevation | Not supported in PBIR |
| Internal spacing within visuals | Cramped/default feel | Power BI visual owns this |
| Custom fonts beyond Segoe UI | Limited typographic range | Power BI font support |
| Legend/axis text micro-positioning | Can't fine-tune chart chrome | Power BI renders these |
| Container grouping with styling | No visual groups with shared background | Not a native concept |

## Options to Proceed

### Option A: Accept Native Power BI Ceiling (~4-5/10 visual-only)

**What:** Declare that native Power BI reports via PBIR have a visual ceiling around 4-5/10 when compared against high-end design mockups. Accept this as the product constraint and move on to spec-level improvements (month sort, combo charts) which would lift the *analytical* critic score to 6-7/10.

**Pros:**
- Honest about platform constraints
- Unblocks spec-level work that provides real analytical value
- The report IS functional and professional — just not "bespoke"

**Cons:**
- Won't achieve the "wow" factor
- Visual-only score stays below 7.5

### Option B: Custom Power BI Visuals

**What:** Develop or integrate custom Power BI visuals (using the Power BI Visuals SDK) for KPI cards, styled containers, and premium chart treatments. These would give full control over rendering via D3.js/SVG.

**Pros:**
- Full pixel control over visual rendering
- Could achieve 7.5+ visual quality
- Industry standard for premium PBI dashboards

**Cons:**
- Significant development effort (separate JS/TypeScript project)
- Custom visuals need certification for org-wide deployment
- Adds complexity to the deployment pipeline
- Out of scope per current TASK.md

### Option C: Power BI Paginated Reports / SSRS

**What:** Use Power BI Paginated Reports (RDL format) instead of interactive reports for the visual layer. Paginated reports offer pixel-level layout control.

**Pros:**
- Precise layout control
- Better for fixed executive presentations

**Cons:**
- Completely different technology (RDL vs PBIR)
- Loses interactivity (slicers, drill-through)
- Major architectural pivot
- Not what the project was designed for

### Option D: Enhanced Theme + Figma/Design Tokens Approach

**What:** Push the theme.json to its absolute limits with `visualStyles` overrides for every visual type. Power BI themes support deep `visualStyles` sections that can override per-property defaults for every visual family.

**Pros:**
- No custom visuals needed
- Theme is a single file applied globally
- `visualStyles` can control much more than basic textClasses

**Cons:**
- Theme `visualStyles` is poorly documented
- May not affect all properties we need
- Needs extensive trial-and-error testing
- May only achieve incremental improvement (4→5 rather than 4→7.5)

### Option E: Lower the Target

**What:** Redefine "premium" to mean "the best achievable native Power BI report" rather than "matching a bespoke design mockup." Set the target at ≥5.5 visual-only with the understanding that native Power BI has inherent visual constraints.

**Pros:**
- Achievable with current architecture + spec fixes
- Honest about platform constraints
- Can proceed to deliver real value

**Cons:**
- Doesn't meet the stated 7.5 target

## Recommendation

**Option A (accept ceiling) + Option D (theme visualStyles exploration)** is the most pragmatic path:

1. Accept that native PBIR formatting caps visual-only scores around 4-5/10
2. Explore theme `visualStyles` as an untested avenue that might yield another 1-2 points
3. Move to spec-level fixes (month sort, combo charts) to lift analytical credibility
4. The combined result (better rendering + fixed analytics) would produce a dashboard scoring 6-7/10 on the full rubric — professional, credible, and demo-worthy for most enterprise contexts

The 7.5 visual-only target against a gpt-image-2 mockup is unreachable with native Power BI visuals alone.
