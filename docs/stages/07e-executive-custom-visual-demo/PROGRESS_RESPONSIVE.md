# Stage 07e Progress Report — Responsive Layout Fix

## Session Summary

Fixed the middle row (Revenue & Profit Trend area chart + Revenue by Region donut) and bottom row to work correctly at different resolutions. Also fixed the donut center KPI overlay positioning and resolved the embed authentication issue for headless screenshots.

## Changes Made

### 1. `custom-visuals/premiumAreaChart/src/visual.ts` — Full responsive rewrite

The area chart previously used fixed pixel values for margins, font sizes, toggle buttons, and legend spacing. It now scales everything proportionally relative to a 640×240 reference viewport.

Key responsive behaviours:
- **`scaleFactor()`** — computes `min(width/640, height/240)` ratio
- **Margins** — scale with clamps: top 28–42px, right 8–16px, bottom 20–32px, left 36–56px
- **Toggle buttons** — shrink from 68→40px width; abbreviate to single letter below 50px; hide entirely below 200px viewport width
- **Font sizes** — axis, legend, tooltip all scale with min 7px floor
- **Legend** — hides when viewport < 120px height or < 250px width; label names truncate based on available spacing
- **Gridlines** — count adapts to chart height (min 3, max 5)
- **X-axis labels** — density computed from `chartWidth / (avgLabelWidth + gap)` 
- **Line stroke**, glow blur, tooltip dot radius, tooltip box dimensions all scale
- **Tooltip** — line height, box width, font sizes all proportional

### 2. `scripts/_deploy_exec_v1.py` — Proportional page layout

Previously hardcoded pixel positions. Now derives all positions from `content_width`:

```python
content_width = 1280 - kpi_start_x - 10  # = 1115px available
hero_width = int(content_width * 0.57)     # = 635px (was fixed 640)
donut_width = content_width - hero_width - mid_gap  # = 470px (was fixed 460)
panel_width = int((content_width - 2 * panel_gap) / 3)  # = 365px each (was fixed 340)
```

### 3. Donut center KPI positioning

The £2.4M / "Total Revenue" overlay is now positioned at:
- **Horizontal**: 40% of donut width (accounts for legend on right)
- **Vertical**: 52% of chart height (accounts for title above)
- Both title and subtitle have `alignment: center`
- KPI label container is 100×44px, centered on the computed ring midpoint

### 4. Embed token fix

Switched from `TokenType.Aad` (which was returning 403 for service principal) to `TokenType.Embed` using the Power BI GenerateToken API. This resolved the headless screenshot authentication failure.

## Commits

- `e93e0c1` — `fix(07e): responsive area chart + proportional layout + centered donut KPI`

## Verification

- Fresh report deployed via Fabric REST API ✓
- Headless Playwright screenshot captured at 1280×720 ✓
- Title shows "RENDERED" (no embed errors) ✓
- Donut KPI visually centered on ring ✓
- Area chart rendering correctly with proportional elements ✓

## Remaining Work for Stage 07e Completion

1. **Custom visuals still needed**: Premium horizontal bar chart, premium donut, premium detail/table (task requires 5 custom visuals; currently using native bar + native donut)
2. **Visual iteration**: Task requires ≥3 meaningful visual iterations with screenshots
3. **Critic evaluation**: 3× multimodal critic runs against the 15-dimension rubric
4. **Hard acceptance gates**: Median ≥7.5/10 overall, ≥80/100 mockup parity, etc.
5. **Automated tests**: 16 test categories specified in TASK.md
6. **Interaction testing**: Cross-filter/selection proof
7. **Full REPORT.md**: Complete evidence package per task contract

## Architecture Notes for GPT

- The deploy script (`scripts/_deploy_exec_v1.py`) is standalone iteration scaffolding — builds entire PBIP definition inline and deploys via Fabric REST
- Custom visuals are packaged via `npx pbiviz package` in each visual's directory
- Private custom visual embedding uses `CustomVisuals/{GUID}/package.json` + `resources/{GUID}.pbiviz.json` structure in PBIP
- Embed tokens are generated via `POST /groups/{workspace_id}/reports/{report_id}/GenerateToken`
- The venv is at `/home/ec2-user/pbi/.venv/` — activate before running scripts
- All 4 custom visuals need `npm ci && npm install powerbi-visuals-tools --save-dev && npx pbiviz package` to build
