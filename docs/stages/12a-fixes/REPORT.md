# Stage 12A — Post-Stage Visual Fixes

Minor, owner-requested presentation fixes applied after Stage 12A was accepted.
No analytical content, measures, chart families or information architecture were
changed. This is visual-system cleanup only.

## Conclusion: `PASS`

---

## Requested fixes

1. **Finance + Product** — restore the visible title on the middle-left
   profit/revenue trend chart.
2. **Product** — ensure the top-right filters (slicers) do not overlap the KPI
   card backgrounds.
3. **Product** — remove the duplicate headers from the top-row KPI cards.
4. **Product** (follow-up) — fix the donut centre KPI text overlap.

---

## 1. Trend chart title restored (finance + product)

### Failure mode
The middle-left trend visual (`premiumAreaChart`) draws its title internally
from `objects.general.title`. The series legend was positioned at the chart's
left margin on the same row as the title, so the legend rendered on top of the
title and made it unreadable.

### Fix
`custom-visuals/premiumAreaChart/src/visual.ts`:
- Store the current title text (`currentTitle`).
- Offset the legend group horizontally so it starts after the title
  (`10 + estimatedTitleWidth + 18px`), falling back to the chart left margin
  when there is no title.

Rebuilt with `pbiviz package`.

### Result
Both "Revenue & Cost Trend" (finance) and "Sales Trend" (product) are now fully
visible, with the legend cleanly to their right.

---

## 2. Product slicer / KPI overlap

### Failure mode
The top-right slicers occupy `y = 6..78`. The product KPI row was at `y = 70`,
so the KPI card backgrounds overlapped the slicers in the `70..78` band.

### Fix
`scripts/_deploy_product_v1.py`: moved the KPI row from `y=70, h=95` to
`y=90, h=75`. The row now clears the slicers (12px gap) and still sits above the
hero row at `y=175`. This matches the accepted Financial dashboard, where the
KPI row is at `y=90`.

---

## 3. Product duplicate KPI headers

### Failure mode
Each top-row KPI (`premium_kpi`) had two labels: a renderer container header
(from `VisualSpec.title` — e.g. "TOTAL SALES") **and** the card's own internal
label (from the measure `displayName`). The container header floated above the
card and collided with the slicers.

### Fix
`scripts/_deploy_product_v1.py`: set `title=""` on the four KPI specs. The card
now shows only its internal label ("Total Revenue", "Gross Profit",
"Gross Margin %", "Active Products"), matching the Financial dashboard's KPI
grammar.

---

## 4. Product donut centre KPI overlap

### Failure mode
`make_donut_composite` emits two visuals in the same donut hole:
- the custom `premiumDonut` (which, since Stage 12A, draws its **own** centre
  total — the sliced revenue total, e.g. "2.4M / TotalRevenue"); and
- a transparent `donut_center_kpi` overlay showing the intended centre metric
  ("128 / Products").

Both rendered in the hole, producing overlapping text ("1282.4M",
"Products / TotalRevenue").

### Fix (generic, at the template level)
Made the donut's internal centre KPI suppressible:
- `custom-visuals/premiumDonut/capabilities.json`: added a
  `general.showCenterValue` boolean property.
- `custom-visuals/premiumDonut/src/visual.ts`: gate the centre total + label
  behind `getShowCenterValue(options)` (defaults to **true** for backward
  compatibility). Rebuilt with `pbiviz package`.
- `src/pbi_gen/renderer/templates/builder.py`: for custom visuals, emit
  `objects.general.showCenterValue` when a binding sets `show_center_value` in
  its config overrides.
- `src/pbi_gen/renderer/templates/rapid_engine.py` (`make_donut_composite`) and
  `src/pbi_gen/renderer/templates/composites.py`
  (`make_donut_composite_bindings`): set `show_center_value=False` on the donut
  so only the overlay metric appears in the hole.

### Result
The product donut centre now shows a clean "128 / Products" with no overlap.

### Backward compatibility
The flag defaults to true. Financial, Customer and Executive donuts use a plain
`premium_donut` (no overlay) and are unaffected — they still render their own
centre total (e.g. Financial "1.0M / GrossProfit"). Verified by the config-build
tests below.

### Follow-up (centre offset)
After the overlap fix, the centre KPI was still ~10px left of the true donut
hole because `compute_donut_center()` used approximate constants
(`legend=120, padding=8`) that did **not** match the donut visual's actual
internal layout (`legendWidth = min(w*0.35, 140), padding=12`,
`chartCenterX = padding + chartArea/2`). Rewrote `compute_donut_center()` to
mirror `premiumDonut/src/visual.ts` exactly, so the overlay lands on the real
ring centre at any size. The Stage 12A donut-centre size-matrix tests were
updated to derive the expected centre from the same geometry and still pass
(≤5px, in practice 0px).

---

## 5. Product trend grouped by year (x-axis)

### Failure mode
The product "Sales Trend" used a single `Date.Month` category, so the x-axis
showed a flat Jan–Dec with no year context — unlike the Financial dashboard,
which groups by Year + Month.

### Fix
`scripts/_deploy_product_v1.py`: the trend `category` binding now uses
`[Date.Year, Date.Month]`. The `premiumAreaChart` visual already handles the
hierarchical (Year + Month) case, so the axis now reads "Apr '21 … Feb '23".

---

## Incidental fix required for deployment

`scripts/_deploy_financial_v1.py` did not package the `premiumDonut` custom
visual, even though the Financial config depends on it (from the Stage 12A donut
work). Deployment failed with
`Cannot read 'CustomVisuals/premiumDonut.../package.json'`. Added the
`DONUT_GUID` archive entry so the Financial report deploys zero-touch.

---

## Files changed

| File | Change |
|---|---|
| `custom-visuals/premiumAreaChart/src/visual.ts` | Offset legend past internal title |
| `custom-visuals/premiumDonut/capabilities.json` | Add `general.showCenterValue` |
| `custom-visuals/premiumDonut/src/visual.ts` | Gate centre KPI behind `showCenterValue` (default true) |
| `src/pbi_gen/renderer/templates/builder.py` | Emit `showCenterValue` for custom visuals |
| `src/pbi_gen/renderer/templates/rapid_engine.py` | `make_donut_composite` suppresses donut centre |
| `src/pbi_gen/renderer/templates/composites.py` | `make_donut_composite_bindings` suppresses donut centre; `compute_donut_center` geometry aligned to visual.ts |
| `scripts/_deploy_product_v1.py` | KPI titles removed; KPI row moved to y=90/h=75; trend grouped by Year+Month |
| `scripts/_deploy_financial_v1.py` | Package `premiumDonut` archive |
| `tests/test_stage12a.py` | +4 assertions for the donut centre-suppression fix |

Screenshots: `docs/stages/12a-fixes/financial_final.png`,
`docs/stages/12a-fixes/product_final.png`.

---

## Tests and verification

- `tests/test_stage12a.py`: **74/74 passed, 0 failed** (was 70; +4 new
  assertions covering composite centre-suppression and the builder flag,
  including the backward-compatible default).
- Financial redeploy: **SUCCESS** (report rendered, title visible).
- Product redeploy: **SUCCESS** (25–28s, preflight passed, 10 visuals).
- Custom visuals rebuilt via `pbiviz package` (premiumAreaChart, premiumDonut).

### Human visual inspection
- Finance trend title visible and clear of the legend? **Yes.**
- Product trend title visible and clear of the legend? **Yes.**
- Product slicers clear of the KPI card backgrounds? **Yes.**
- Product top-row KPIs free of duplicate headers? **Yes.**
- Product donut centre free of overlapping text? **Yes** ("128 / Products").
- Product donut centre KPI actually centred in the ring? **Yes** — geometry now
  matches the donut visual exactly (was ~10px left).
- Product trend x-axis grouped by year like the other dashboards? **Yes**
  ("Apr '21 … Feb '23").
- Financial / Customer donut centres unchanged? **Yes** (backward compatible).

---

## Assumptions and deviations

- The product donut overlay uses a static centre label ("128") from the
  original composite spec rather than the live `ActiveProducts` value (500,
  shown correctly in the top KPI card). This static-vs-live behaviour is
  pre-existing in the `donut_center_kpi` overlay and is outside the scope of the
  requested overlap fix; the top KPI already surfaces the live count. Left
  as-is.

## Known limitations

- Legend-vs-title clearance in `premiumAreaChart` uses an estimated title width
  (character count × font metric). It is generous enough for the current titles;
  a very long title on a narrow panel could still crowd the toggle buttons.

## Recommended future work

- Drive the donut centre overlay from the live measure value instead of a static
  string, or let the donut render an arbitrary secondary measure in its centre
  natively (removing the need for a separate overlay visual entirely).
- Add a `.gitattributes` normalising `*.py` to LF to avoid line-ending churn on
  Windows edits.
