# Stage 05c — Report Runtime Debugging: REPORT

## Summary

**The live Executive Retail Performance Dashboard now opens and renders in the browser without an endless spinner.**

Root cause: `fabric-cicd`'s report deployment creates reports that fail to render at runtime in the Fabric web UI. The fix is a split deployment strategy — semantic model via fabric-cicd, report via direct Fabric REST API with explicit `byConnection` binding.

## Runtime Symptom

Opening any report deployed via `fabric-cicd` in the Fabric web UI resulted in either:
- An endless loading spinner, or
- "Please try again later or contact support" error page

This occurred for ALL reports deployed via fabric-cicd, including a bare-minimum report with zero visuals and a single empty page.

## Scope of the Hang

**All pages and all reports** deployed via fabric-cicd were affected. This was not a visual-specific or page-specific issue — it was a fundamental deployment-method issue.

## Diagnostic Variants Deployed

| Variant | Method | Visuals | Theme | Result |
|---------|--------|---------|-------|--------|
| DiagnosticMinimal | fabric-cicd | 1 card | Yes | ❌ Error |
| BareMinimal | fabric-cicd | None | None | ❌ Error |
| ExactClone | Direct Fabric API | 1 card | None | ✅ Loads ("600 Total") |
| DiagnosticMinimal v2 | Direct Fabric API | 1 card | Yes | ✅ Loads |
| ExecutiveRetailPerformanceDashboard | Direct Fabric API | 29 visuals | Yes | ✅ Loads |

## Isolation Sequence

1. **Deployed minimal 1-card report** via fabric-cicd → spinner/error
2. **Deployed bare page (zero visuals, no theme)** via fabric-cicd → same error
3. **Compared stored definition** (via getDefinition API) of broken reports vs working CRMmetricsng report
4. **Identified `version.json`** discrepancy: broken reports had `"4.0.0"`, working had `"2.0.0"`
5. Fixed version.json, redeployed via fabric-cicd → **still broken**
6. **Created ExactClone** via direct Fabric Create Item API with `byConnection` → **works!**
7. Conclusion: **fabric-cicd report deployment produces reports that cannot render**, regardless of PBIR content

## Root Cause

The `fabric-cicd` library (via `publish_all_items`) deploys reports in a way that produces a broken runtime state in the Fabric web UI. The exact mechanism is unclear (likely an internal API sequencing or metadata issue in fabric-cicd), but the observable difference is:

- Reports deployed via `fabric-cicd` → fail to render
- Reports deployed via direct `POST /v1/workspaces/{id}/items` (Create Item) or `POST .../updateDefinition` → render correctly

Additionally, using `byConnection` with the explicit semantic model ID (rather than relying on fabric-cicd's byPath resolution) ensures a clean binding.

## Secondary Fix: PBIR Schema Alignment

While debugging, we also identified and fixed PBIR metadata mismatches that could cause issues:

| Property | Before | After | Source |
|----------|--------|-------|--------|
| `version.json` version | `"4.0.0"` | `"2.0.0"` | Working CRMmetricsng report |
| `report.json` settings | Missing | Added (`useStylableVisualContainerHeader`, etc.) | Working CRMmetricsng report |
| `report.json` customTheme | Missing | Added in `themeCollection` | Working CRMmetricsng report |
| Visual schema | `1.3.0` | `2.0.0` | Working CRMmetricsng report |

## Code Changes

### `src/pbi_gen/deploy/fabric.py`
- **New function `deploy_report_direct()`**: Deploys reports via Fabric REST API directly, using `byConnection` with explicit semantic model ID
- **New function `_collect_report_parts()`**: Collects all report files as base64-encoded parts for the API
- **Modified `deploy_to_workspace()`**: Now uses a split strategy:
  1. Semantic model deployed via fabric-cicd (which works correctly for models)
  2. Report deployed via direct Fabric API (bypassing fabric-cicd's broken report deployment)

### `src/pbi_gen/renderer/report.py`
- `generate_version_json()`: Changed version from `"4.0.0"` to `"2.0.0"`
- `generate_report_json()`: Added `settings` block, `customTheme` in themeCollection, `layoutOptimization`
- `generate_page_json()`: Schema remains at `1.4.0` (matches working reports)
- `generate_visual_json()`: Schema updated to `2.0.0`
- `generate_filter_visual_json()`: Schema updated to `2.0.0`

## Semantic Query Verification

All measures continue to evaluate correctly (verified via DAX executeQueries API):
- TotalRevenue: £2,443,302
- Sales row count: 10,000
- All 11 measures functional (verified in Stage 05b, data persists)

## Fidelity Impact

No visuals were dropped or replaced with fallbacks. All 29 source visuals across 4 pages are preserved and render with real data.

## Automated Test Result

```
347 passed in 30.57s
```

Full Stage 01–05b test suite passes without modification.

## Final Browser Verification

**User confirmed**: Executive Retail Performance Dashboard loads and renders in the Fabric web browser UI on 2026-08-20.

## Answer: Does the live Executive Overview now load normally without an endless spinner?

**Yes.** The full 4-page report with 29 visuals loads normally after applying the direct Fabric API deployment method.

## Recommended Next Stage

With the end-to-end pipeline fully working (AI spec → data → render → deploy → browser-verified), the next stage could focus on:
- Visual quality/formatting improvements
- Additional visual types and interactions
- CLI interface for the full pipeline
- Automated browser screenshot capture (Playwright with clean profile)
