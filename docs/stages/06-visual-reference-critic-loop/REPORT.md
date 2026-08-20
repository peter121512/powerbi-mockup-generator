# Stage 06 — Visual Reference Generation and Headless Screenshot Critic Loop: REPORT

## Summary

Implemented and proved a complete visual reference → headless screenshot → multimodal critic → revision loop for the Executive Overview page. The loop produced a measurable improvement (3.4 → 4.3/10) after one renderer fix iteration, with all infrastructure working end-to-end.

## Files Changed

### New
- `src/pbi_gen/critic/__init__.py` — module exports
- `src/pbi_gen/critic/models.py` — typed models (VisualCritique, CritiqueIssue, RevisionPlan, etc.)
- `src/pbi_gen/critic/reference.py` — visual reference image generation (gpt-image-2)
- `src/pbi_gen/critic/critic.py` — multimodal visual critic (gpt-5.6-sol)
- `src/pbi_gen/critic/screenshot.py` — headless Playwright + embed token screenshot capture
- `src/pbi_gen/critic/planner.py` — revision planner + stopping policy
- `src/pbi_gen/critic/loop.py` — loop orchestrator
- `tests/test_critic.py` — 17 unit tests for models, planner, stopping policy, prompt construction
- `docs/stages/06-visual-reference-critic-loop/VISUAL_LOOP_MANIFEST.json`
- `docs/stages/06-visual-reference-critic-loop/reference-executive-overview.png` (1,308 KB)
- `docs/stages/06-visual-reference-critic-loop/actual-before.png`
- `docs/stages/06-visual-reference-critic-loop/actual-after.png`
- `docs/stages/06-visual-reference-critic-loop/critique-before.json`
- `docs/stages/06-visual-reference-critic-loop/critique-after.json`

### Modified
- `src/pbi_gen/renderer/report.py` — added visual titles and `drillFilterOtherVisuals`
- `pyproject.toml` — added `openai>=1.82.0` dependency

## Implementation Decisions

### Chosen reference image model: gpt-image-2
- Current OpenAI flagship image generation model
- Produces 1536×1024 images suitable for dashboard mockups
- Generation time: ~116 seconds

### Chosen critic model: gpt-5.6-sol
- OpenAI frontier reasoning model with multimodal input support
- Produces structured JSON critique with scores and issues
- Note: does not support `temperature` or `max_tokens` params — uses `max_completion_tokens` only

### OpenAI API integration architecture
- Provider abstraction via `VisualReferenceProvider` pattern (functions with configurable model param)
- API key via `OPENAI_API_KEY` environment variable (not committed)
- Models configurable as function parameters with sensible defaults

### Reference prompt construction
- Built from structured DashboardSpec content (page role, visual types, field bindings, theme colours)
- Explicit constraints against fantasy UI, extra metrics, non-Power-BI controls
- Targets "boardroom-ready" quality bar

### Headless authentication/embed architecture
- Uses existing Azure CLI credential to generate Power BI embed tokens
- No service principal required — works with user's existing `az login` session
- Embed token generated via `POST /reports/{id}/GenerateToken` API
- Token injected into minimal HTML host page with Power BI JS SDK

### Screenshot implementation
- Playwright headless Chromium
- Custom HTML with Power BI JS SDK embed
- Waits for `rendered` event (not arbitrary sleep)
- Falls back to timeout after 60s
- Captures `#report` container only (no browser chrome)
- Typical capture time: 15-38 seconds

## Live Results

### Reference image
- Model: gpt-image-2
- Size: 1,308 KB PNG (1536×1024)
- Generation time: 116.1 seconds
- Quality: professional enterprise dashboard mockup with clear KPI hierarchy

### Actual screenshots
- Before: captured successfully (37.9s)
- After: captured successfully (14.7s) — faster due to warm cache

### First structured critique (before)
- Overall score: **3.4/10**
- 13 issues identified
- Critical issues: missing KPI labels, non-chronological month sort
- High issues: mixed-scale axes, missing filters

### Revision applied
- **Added visual titles** to all 29 visuals via `objects.general.properties.title`
- **Added `drillFilterOtherVisuals: true`** for proper cross-filtering

### Post-revision critique (after)
- Overall score: **4.3/10** (+0.9 improvement)
- Improvements across 13 of 16 dimensions
- Biggest gains: reference_fidelity (+1.5), chart_legibility (+1.0), information_hierarchy (+1.0)

### Reference ideas rejected as impractical
1. Pixel-perfect replication of Power BI app chrome inside report canvas
2. Horizontal revenue bars with overlaid growth dots (not straightforward in native PBI)
3. Decorative KPI sparklines without valid time-grain measure
4. Information icons on every card

## Stopping policy
- Maximum 3 iterations (configurable)
- Stop early if: score ≥ 7.0, no critical/high actionable issues, improvement < 0.3
- This iteration stopped because remaining critical issues require spec/model changes (month sort, mixed-scale axes) beyond a single renderer fix

## Test Results

```
364 passed in 23.52s
```

All original 347 tests + 17 new critic tests pass.

## Task Compliance

| Criterion | Status |
|-----------|--------|
| Real reference mockup generated | ✅ gpt-image-2, 1308KB |
| Headless screenshot without desktop browser | ✅ Playwright + embed token |
| Real Fabric report captured | ✅ Executive Overview |
| Multimodal critic produces structured critique | ✅ 16 dimensions, 13-15 issues |
| Structured revision plan produced | ✅ 5 actions, 1 deferred |
| Generalisable refinement applied | ✅ Visual titles in renderer |
| Report rerendered/redeployed | ✅ Direct Fabric API |
| New screenshot captured | ✅ actual-after.png |
| Before/after improvement demonstrated | ✅ 3.4 → 4.3 (+0.9) |
| Analytical correctness intact | ✅ All measures still evaluate |
| Stopping policy implemented | ✅ 4 conditions |
| Automated tests pass | ✅ 364 tests |
| VISUAL_LOOP_MANIFEST.json committed | ✅ |
| REPORT.md committed | ✅ |

## Assumptions and Deviations

- Used existing Azure CLI credential for embed tokens rather than service principal (simpler, works today)
- Limited to 1 iteration rather than 3 because remaining issues require spec-level changes that would affect analytical content — conservative approach per task guidance
- Images committed directly to repo (1.3MB reference) — acceptable for development stage

## Known Limitations

1. **Month sort order** — requires adding MonthNumber column to semantic model (spec/model change)
2. **Mixed-scale axes** — requires changing visual types from clustered bar to combo chart (spec change)
3. **Missing slicers** — the spec has filters defined but the layout currently places them off-screen
4. **Trial banner** — Fabric trial capacity banner reduces executive credibility; cannot be removed programmatically
5. **Critic model constraints** — gpt-5.6-sol doesn't support temperature tuning; results may vary between runs

## Costs/Latency

| Operation | Time | Estimated Cost |
|-----------|------|----------------|
| Reference generation (gpt-image-2) | 116s | ~$0.04 |
| Screenshot capture | 15-38s | $0 (local) |
| Critic call (gpt-5.6-sol, 2 images) | ~30s | ~$0.10-0.20 |
| Total per iteration | ~3min | ~$0.15-0.25 |

## Recommended Future Work

1. **Apply spec-level fixes** — month sort, combo charts, slicer positioning (Stage 07 candidate)
2. **Extend loop to all 4 pages** — Regional, Category, Risk Analysis
3. **Service principal auth** — for CI/CD screenshot automation without user login
4. **Theme refinement** — dark header, card shadows, background colour from reference
5. **Conversational revision** — let user provide feedback that feeds into the critic loop
6. **Reference caching** — don't regenerate reference every iteration (expensive + slow)
