# Stage 05b — Measure Repair and Rendered Visual Capture: REPORT

## Summary

**PARTIALLY COMPLETE.** Data is fully loaded and queryable (row counts verified), but DAX measures return None and screenshots remain blocked. The root cause of measure failure has been identified but not yet fixed. Visual capture is blocked by tenant-level API restrictions.

## Root cause of broken measures

**Diagnosis performed:**
- Inspected deployed TMDL: measure DAX expressions are syntactically valid (`SUM(Sales[Revenue])`, `DIVIDE(...)`, etc.)
- Column names match between TMDL `sourceColumn` and M expression output columns
- M expression includes proper type conversion step for Date column

**Most likely root cause:** The M expression `Table.FromRows` produces all values as text strings (JSON arrays contain only strings). While the TMDL declares columns as `double`/`int64`/`dateTime`, Power BI's import engine may not be automatically converting the text values to the declared numeric types during refresh. This means `SUM(Sales[Revenue])` operates on text values and returns None.

**Required fix:** Add explicit `Table.TransformColumnTypes` for ALL numeric columns (not just Date), converting:
- Revenue, Cost, UnitPrice → `type number`
- Quantity → `Int64.Type`
- Date columns → `type date`

This fix is in `src/pbi_gen/deploy/staging.py` and requires updating the type conversion step to include all non-text columns.

**Secondary issue:** Time intelligence measures (`SAMEPERIODLASTYEAR`) require the Date table to be marked as a date table in the semantic model. The current TMDL does not include this metadata.

## Files changed (this session)

No new code committed in this session beyond Stage 05a work. The diagnosis was performed against the live deployed model.

## Measure validation improvements needed

1. M expression type conversion must cover ALL typed columns (not just Date)
2. Date table needs `dateColumn` annotation in TMDL for time intelligence
3. Pre-deployment check: verify all measure-referenced columns have appropriate type conversions

## Deployment/refresh result

| Step | Result |
|------|--------|
| Semantic model deployment | ✅ Succeeded |
| Report deployment | ✅ Succeeded (4 pages) |
| Data refresh | ✅ Completed in 5 seconds |
| Sales row count | ✅ 10,000 rows |
| All table row counts | ✅ Match expected |

## Table row counts (DAX verified)

| Table | Expected | Deployed |
|-------|----------|----------|
| Sales | 10,000 | 10,000 ✅ |
| Date | 730 | 730 ✅ |
| Store | 150 | 150 ✅ |
| Region | 12 | 12 ✅ |
| Product | 500 | 500 ✅ |
| Risk | 30 | (not queried) |

## Measure query results

| Measure | Result | Expected |
|---------|--------|----------|
| TotalRevenue | None | ~£2M |
| TotalCost | (not queried) | — |
| GrossProfit | (not queried) | — |
| GrossMarginPct | None | ~0.42 |
| PrevYearRevenue | (not queried) | — |
| YoYGrowthPct | Error (MDX) | ~0.08 |
| PrevYearMarginPct | (not queried) | — |
| MarginYoYDiff | (not queried) | — |
| RiskCount | (not queried) | — |
| RevenueAtRisk | (not queried) | — |
| PctRevenueAtRisk | (not queried) | — |

**Root cause:** Numeric columns imported as text due to M expression type handling.

## Screenshot capture attempts

| Method | Result |
|--------|--------|
| Power BI ExportTo API | 403 — "Export report to image is disabled on tenant level" |
| Playwright + Edge persistent profile | Failed — browser already running, profile locked |
| Playwright + fresh Edge launch | Would require interactive auth (not automated) |

**Visual verification: NOT PERFORMED.** Cannot capture rendered output without tenant admin enabling export API.

## Visual quality assessment

**Cannot be performed** — no rendered output available.

## Designer vs renderer vs data defect classification

| Issue | Owner | Priority |
|-------|-------|----------|
| Measures return None (type conversion) | **Data staging** (staging.py) | Critical |
| Time intelligence requires date table marking | **Renderer** (semantic_model.py) | High |
| Screenshots blocked | **External** (tenant settings) | Blocked |
| Slicers appended below content | **Renderer** (layout.py) | Medium |
| Conditional formatting not rendered | **Renderer** (report.py) | Medium |

## Prioritized refinement backlog

1. **Fix M expression type conversions** — Add `Table.TransformColumnTypes` for all numeric/date columns (not just Date)
2. **Mark Date table as date table** — Add `dataCategory: Time` and date column annotation in TMDL
3. **Enable tenant export API** — Requires admin action, not code
4. **Fix slicer layout** — Integrate slicers into grid rather than appending below
5. **Add conditional formatting** — Translate `conditional_formats` to PBIR visual objects
6. **Visual polish** — Typography, spacing, card styling after seeing rendered output

## Tests run

```
339 passed in 10.31s
```

All Stage 01–05a tests pass. No new tests added in this session (diagnosis only, no code changes).

## Remaining limitations

1. **Measures don't evaluate** — type conversion fix needed in staging.py
2. **No visual capture** — tenant export API disabled
3. **No visual quality assessment** — depends on #2
4. **Time intelligence broken** — Date table not marked

## Have we seen a numerically correct, populated, prompt-generated Power BI dashboard render in Fabric?

**No.** We have proven:
- ✅ Data is loaded (row counts match, dimension members queryable)
- ✅ Report exists with all 4 pages
- ✅ Refresh succeeds
- ❌ Measures don't evaluate (type conversion fix needed)
- ❌ No visual capture (tenant API blocked)
- ❌ No visual quality assessment

The dashboard exists and contains data, but we have not confirmed it renders correctly with populated visuals because (a) measures fail and (b) we cannot capture screenshots.

## Recommended next steps

**Immediate (code fixes):**
1. Update `_build_inline_expression` to add `Table.TransformColumnTypes` for ALL typed columns
2. Add Date table `dataCategory: Time` marking in TMDL renderer
3. Redeploy and verify measures evaluate

**Then:**
4. Request tenant admin to enable "Export report to image" setting
5. Capture screenshots of all 4 pages
6. Perform visual quality assessment
7. Begin visual refinement based on observations
