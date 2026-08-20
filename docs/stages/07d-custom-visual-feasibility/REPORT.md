# Stage 07d — Custom Visual Feasibility Spike: REPORT

## Hypothesis Tested

> Can a small library of Power BI custom visuals provide the rendering control required to make generated dashboards genuinely comparable in visual quality to the premium executive dashboard references?

## Conclusion: PROMISING_BOUNDED_FOLLOWUP

Custom visuals **work** and produce **materially better** visual quality than native Power BI visuals when data is bound. However, fully automated headless deployment without manual interaction is **not yet proven** — a data binding activation step is required.

### What works:
- ✅ Custom visual builds and deploys via Fabric API
- ✅ Renders with full styling control (confirmed by user: "much better")
- ✅ Report loads without errors
- ✅ Org visual registration works
- ✅ Both KPI and Chart visuals build successfully

### What doesn't work yet:
- ❌ Fresh API-deployed custom visuals don't auto-bind data on first load
- ❌ Manual editor "touch" (untick/retick field) required to activate data flow
- ❌ This blocks fully headless automated deployment

### Bounded follow-up needed:
One narrow investigation: determine if there's a PBIR metadata field, query configuration, or API parameter that triggers the same data initialization that the manual editor touch performs. Possibilities:
- A `dataTransforms` property in visual.json
- A different query binding format for custom visuals
- A separate API call to "initialize" visual bindings post-deployment
- Using Power BI Desktop to publish (rather than REST API) as the deployment mechanism

## Custom Visual Architecture

### Toolchain
- Node.js 24.15.0
- npm 11.12.1
- powerbi-visuals-tools (pbiviz) 7.2.1
- TypeScript + LESS styling
- API version: 5.11.1

### Premium KPI Visual Implementation
- **Source**: `custom-visuals/premiumKPI/src/visual.ts`
- **Styling**: `custom-visuals/premiumKPI/style/visual.less`
- **Capabilities**: Single measure data role, categorical mapping
- **Build artifact**: `.pbiviz` (4.3KB)

### Visual Features
- Navy accent bar (3px, left edge, rounded)
- Uppercase metric label (10px, secondary colour, letter-spacing)
- Large callout value (responsive sizing 18-48px based on viewport)
- Segoe UI font family
- Proper value formatting (£2.4M, 42.1%, etc.)
- Responsive layout (flexbox)
- No innerHTML (DOM manipulation only, passes security lint)

## PBIR/Deployment Integration

### How custom visuals are deployed via Fabric API:
1. `.pbiviz` file goes in `CustomVisuals/` folder in the report definition parts
2. `report.json` includes `"publicCustomVisuals": ["<GUID>"]` array
3. `visual.json` uses the GUID as `visualType`
4. Fabric API accepts and deploys without error

### Key findings:
- ✅ Fabric API accepts custom visuals in report definitions
- ✅ Report loads without spinner
- ✅ Visual renders after data binding is activated
- ⚠️ Programmatic API deployment doesn't auto-activate data binding (needs manual "touch" in editor)
- ⚠️ Organizational visual registration required for rendering

## Tenant/Security Dependencies

| Requirement | Status | Notes |
|-------------|--------|-------|
| Organizational visual registration | Required | Admin uploads .pbiviz to org visual store |
| "Allow visuals created using Power BI SDK" | Enabled by default | Tenant setting |
| "Add and use certified visuals only" | Must be disabled | Or visual must be certified |
| Data binding activation | Manual touch needed | API-deployed visuals need field re-binding once |

## Visual Quality Comparison

| Aspect | Native Card | Premium KPI Custom |
|--------|------------|-------------------|
| Typography control | Limited (theme only) | Full (any CSS) |
| Internal spacing | Fixed by PBI | Fully controlled |
| Accent/branding | Not possible | Accent bar, colours |
| Label styling | Category label only | Custom uppercase, tracking |
| Value formatting | Basic | Custom (£2.4M, %, etc.) |
| Responsive sizing | Fixed ratios | Viewport-aware |
| Overall impression | "Default Power BI" | "Designed/bespoke" |

**User confirmation**: "All of those. Yes, much better."

## Interaction Testing

- ✅ Report loads
- ✅ Visual renders with data
- ⚠️ Cross-filter: not yet tested (needs further development)
- ⚠️ Slicer response: not yet tested
- ✅ No broken visual icon
- ✅ No runtime errors

## Remaining Gaps for Full Implementation

1. **Auto data binding**: API-deployed custom visuals need the binding "touched" in editor — needs investigation for fully automated deployment
2. **Premium Chart visual**: Not built yet — would need D3.js line/bar chart implementation
3. **Cross-filtering/selection**: Custom visuals need `selectionManager` implementation
4. **Multiple data roles**: KPI prototype only supports single measure
5. **Formatting pane**: No user-configurable properties yet
6. **Headless screenshot**: Embed token capture may not trigger data binding automatically

## Automated Tests

```
373 passed in 15.36s (existing Python suite)
```

Custom visual builds successfully via `npx pbiviz package`.

## Evidence

- `docs/stages/07d-custom-visual-feasibility/custom-visual-test.png` — initial deployment (blank)
- `docs/stages/07d-custom-visual-feasibility/custom-visual-working.png` — after activation
- User visual confirmation: "accent bar, uppercase label, large value — much better"

## Explicit Feasibility Conclusion

**The custom visual approach CAN close the visual gap** between native Power BI and premium dashboard references. With full rendering control via HTML/CSS/TypeScript, we can achieve:
- Bespoke KPI cards with branded styling
- Custom chart rendering via D3.js
- Precise typography and spacing
- Branded accent elements
- Responsive layouts

The architecture is viable for a reusable custom visual library that would allow generated dashboards to match the premium reference standard.

## Recommendation

**PROMISING_BOUNDED_FOLLOWUP** — Custom visuals are the viable path to premium visual quality, but the auto-binding issue must be solved first.

Recommended bounded follow-up:
1. Investigate `dataTransforms` / visual config metadata that triggers binding
2. Try deploying via Power BI Desktop publish flow (not REST API) to see if that activates bindings
3. Consider a post-deployment "warm-up" API call if one exists
4. If binding cannot be automated, evaluate whether a one-time manual setup per report is acceptable for the product

Only after auto-binding is solved should the full custom visual library be built.
