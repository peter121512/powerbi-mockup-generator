# Stage 07d-a: Custom Visual Auto-Binding — REPORT

**Status: BLOCKED**

## Root Cause Summary

The "auto-binding" problem was misdiagnosed in Stage 07d. The actual issue is **not** that data binding fails — it's that the custom visual code **never executes** on first render due to a mandatory per-viewer consent step enforced by the Power BI Service platform.

Power BI requires explicit user consent before organizational custom visuals can render in a report. This consent:
- Is **NOT** stored in the PBIR report definition
- **Cannot** be set via any REST API (Fabric or Power BI)
- Is **reset** when the report definition is updated via `updateDefinition`
- Is **NOT** inherited by cloned reports (when using the org visual path)
- **Cannot** be bypassed with embed tokens (neither AAD nor Embed type)
- Is a **service-side, per-viewer** state invisible to the report author

When consent IS granted (manually via the editor), the data binding works correctly with the standard `queryState` structure — no additional metadata is required.

## Exact Manual Activation Action

The manual activation observed in Stage 07d was actually the consent step:
1. Open report in edit mode
2. Click on the custom visual placeholder
3. Power BI prompts "To see this custom visual, add it to this report first"
4. User clicks to accept/add
5. Visual code loads, `update()` is called with dataViews, data renders

## PRE/POST Report Definition Diff Findings

**No metadata difference exists** between pre-consent and post-consent report definitions. The PBIR definitions are byte-for-byte identical. The consent state is stored in an internal service-side database, not in the report artifact.

Evidence files:
- `PRE_definition.json` — fresh deployment definition
- `PRE_v3_definition.json` — organizationCustomVisuals variant
- `definition_BothVisualsNew_activated.json` — manually activated report
- `definition_DiagKPIOnly_fresh.json` — fresh org visual report

## Native vs Custom Binding Comparison

Native visuals (card, barChart, etc.) do NOT require consent. They render data immediately on first load with the same simple `queryState` structure. The only difference is:
- Native visual types are hardcoded in the PBI engine — no external code to load
- Custom visuals require loading external JavaScript — PBI gates this behind consent for security

## Custom Visual update() Diagnostics

The visual was instrumented to show "NO DATA" in red when `options.dataViews` is empty and display dataView count/update type. In all tests where the visual code DID load (cached consent), it correctly received data. In fresh deployments, the visual code never executes — the consent overlay blocks it entirely.

## Candidate Matrix

| # | Approach | Deploy | Visual Loads | Consent | Data | Notes |
|---|----------|--------|-------------|---------|------|-------|
| 1 | `publicCustomVisuals` + CustomVisuals/ pbiviz | ✓ | ✗ (403) | No overlay | No | 403 fetching from AppSource — visual not published there |
| 2 | `organizationCustomVisuals` | ✓ | ✓ (from org store) | **YES — blocks** | No | Visual code available but consent overlay prevents execution |
| 3 | Embedded `CustomVisual` resource package | ✓ | ✗ | No overlay | No | JS/CSS stored but PBI doesn't execute private embeds |
| 4 | `RegisteredResources` + pbiviz | ✓ | ✗ | No overlay | No | Same as #3 |
| 5 | `OrganizationalStoreCustomVisual` resource type | ✓ | ✗ (403) | No overlay | No | Falls back to AppSource lookup |
| 6 | Both `org` + `public` declarations | ✓ | ✗ (403) | No overlay | No | publicCustomVisuals takes priority, causes 403 |
| 7 | Clone pre-activated + keep definition | ✓ | ✗ (403) | No overlay | No | Clone preserves consent but publicCustomVisuals causes 403 |
| 8 | Clone pre-activated + updateDefinition to org | ✓ | ✓ | **YES** (resets) | No | updateDefinition resets consent state |
| 9 | AAD token vs Embed token | — | — | Both blocked | — | Token type does not affect consent |
| 10 | "Enable for Visualization Pane" admin setting | — | — | Still required | — | Only adds to authoring toolbox, not auto-consent |

## Desktop Comparison

Not feasible to fully test (would require Power BI Desktop PBIP publish). However, from documentation: Desktop-authored reports with custom visuals imported from file DO work because the authoring action implicitly grants consent. The publish path carries this consent to the service.

## Package Identity/Registration Findings

- Visual GUID: `premiumKPI0E21B11FE691418A84E3F774DD6461A5`
- Version: `1.0.0.0`
- Org store registration: **confirmed present and enabled**
- "Enable for Visualization Pane": **enabled**
- API version: `5.11.0`
- Capabilities: single data role `measure` (kind: Measure), single dataViewMapping
- Package builds successfully with pbiviz 7.2.1

## Remaining Limitations

1. **No programmatic consent path exists** — Power BI enforces this as a security boundary
2. **Embedded custom visual resources (type: CustomVisual)** are accepted by the PBIR schema but the service doesn't execute the JavaScript from report-embedded resources
3. **AppSource publication** would bypass this entirely but requires Microsoft certification
4. **Desktop-authored PBIP publish** would work but adds a manual authoring step

## Paths Not Yet Exhausted

1. **Power BI Desktop PBIP publish** — authoring in Desktop and publishing via `git push` to Fabric may carry consent. This is the most viable automation path but requires Desktop in the pipeline.
2. **Service Principal with admin consent** — a service principal that is a workspace admin MIGHT be able to bypass viewer consent (untested — would require app registration changes).
3. **Certified custom visual** — publishing to AppSource and getting certified removes all consent barriers.
4. **Power BI Report Authoring Skill (Agentic API)** — newly documented Microsoft API for programmatic report authoring MAY handle consent internally.

## Answer to the Key Question

> **Can this project now deploy a freshly generated Power BI report containing premium custom visuals that receive their data automatically on first render, with zero human interaction?**

**No.** The Power BI Service enforces a mandatory per-viewer consent step for organizational custom visuals that cannot be bypassed via any available REST API, embed configuration, or PBIR metadata. This is a platform-level security boundary, not a bug or missing metadata.

## Recommendation

The most viable paths forward, in order of feasibility:

1. **Desktop PBIP git integration**: Author a template report in Desktop with the custom visual, push to Fabric git repo. This establishes consent through the authoring path. Then use `updateDefinition` to modify page content/data binding (which preserves visual consent if the visual GUID doesn't change). **Requires validation.**

2. **Certified AppSource visual**: Publish the premium visuals to AppSource. `publicCustomVisuals` would then work without consent since certified/marketplace visuals are trusted by default.

3. **Accept native visuals for now**: Continue using native PBI visuals (card, barChart) with enhanced theme/formatting until a programmatic custom visual path is confirmed.

## Automated Test Results

Existing test suite passes (373 tests). No new renderer code was implemented since the issue is a platform constraint, not a code deficiency.

## Evidence Files

- `PRE_definition.json` — First fresh deployment definition
- `PRE_v3_definition.json` — organizationCustomVisuals definition
- `PRE_v4_definition.json` — Embedded CustomVisual definition
- `definition_BothVisualsNew_activated.json` — Manually activated report
- `definition_DiagKPIOnly_fresh.json` — Fresh org visual report
- `zero_touch_results.json` — 3-run test results (initially passed due to cached consent)
- `screenshot_v3.png` — Consent overlay visible
- `screenshot_V8_aad.png` — AAD token test
- `screenshot_V8_embed.png` — Embed token test
- `screenshot_V9.png` — Embedded CustomVisual (blank)
- `screenshot_clone.png` — Clone of pre-activated report
- `screenshot_template_primed.png` — Template priming attempt
- `zero_touch_run1.png` through `zero_touch_run3.png` — 3-run evidence
