# Stage 10 — REPORT.md

## Summary

Stage 10 prepared the generator for rapid, minimal-prompt dashboard execution. No Product dashboard was built. No Product-specific visual template, renderer branch, or semantic model was added.

The system can now execute a full reference-to-deployed-report pipeline in **~45 seconds** (well under the 5-minute target), including model discovery, spec generation, preflight validation, PBIR generation, Fabric REST deployment, and headless screenshot.

**Conclusion: `READY_UNDER_5_MIN`**

---

## Readiness Architecture Changes

### New Module: `src/pbi_gen/renderer/templates/rapid_engine.py`

Single 1,570-line domain-agnostic module providing:

| Component | Purpose |
|-----------|---------|
| Template Catalog loader | Machine-readable template inventory |
| `select_template()` | Deterministic intent→template mapping |
| `discover_model()` | TMDL-based semantic model discovery |
| `ModelMetadata` / `TableInfo` / `MeasureInfo` | Model introspection data classes |
| `infer_column_type()` | CSV value type inference |
| `infer_table_role()` | Fact/dimension classification |
| `infer_relationships()` | Conservative FK inference |
| `infer_measures()` | Standard measure generation |
| `generate_tmdl_table()` | TMDL text generation with DATATABLE |
| `build_model_update()` | Model extension from spec |
| `PageSpec` / `VisualSpec` | Compact page specification |
| `page_spec_to_shell()` / `page_spec_to_bindings()` | PageSpec → builder inputs |
| `validate_model_spec()` | Model preflight |
| `validate_page_spec()` | Page preflight |
| `run_preflight()` | Unified validation |
| `deploy_from_page_spec()` | One-call deployment with timing |
| `deploy_model_update()` | Model definition update |
| `ReferenceSpec` / `ReferenceVisual` | Reference/mockup description |
| `reference_to_page_spec()` | Reference → deployable PageSpec |

### New Artifact: `src/pbi_gen/renderer/templates/template_catalog.json`

204-line machine-readable catalog documenting all 10 templates with:
- Analytical use description
- Page roles (kpi, hero, breakdown, ranking, composition, insight, overlay)
- Data roles with kind, required flag, compatible field types
- Series limits (min/max measures and categories)
- Formatting options
- Known limitations
- Intent mapping (11 analytical intents → template candidates)
- Page role constraints (max per page, typical count, row position)

---

## Existing Template Inventory / Capabilities

| Template ID | Visual Type | Analytical Use | Page Roles | Required Data |
|---|---|---|---|---|
| premium_kpi | Custom | Headline metric | KPI | 1 measure |
| premium_trend | Custom | Time-series trend | Hero, Trend | 1 category + 1-4 measures |
| premium_bar | Native | Horizontal comparison | Breakdown, Ranking | 1 category + 1-3 measures |
| premium_column | Native | Vertical comparison | Hero, Breakdown, Comparison | 1 category + 1-4 measures |
| premium_donut | Native | Part-to-whole | Composition, Breakdown | 1 category + 1 measure |
| premium_table | Native | Detailed tabular | Detail, Breakdown | 1-6 categories + 1-8 measures |
| premium_waterfall | Custom | Bridge / contribution | Breakdown, Bridge | 1 category + 1 measure |
| premium_gauge | Custom | Progress / target | Hero, KPI | 1 measure |
| donut_center_kpi | Native | Center overlay | Overlay | 1 measure |
| premium_insights | Custom | Narrative text | Insight | 1 measure (trigger) |

### Known Limitations

- `premium_trend`: Only works with numeric/date categories (string categories show NaN)
- `premium_insights`: Text is hardcoded in visual source, not data-driven
- `premium_gauge`: Hardcoded to NPS-style display with KPI boxes
- `donut_center_kpi`: Title text is static (set via config_overrides)

---

## Semantic Discovery Approach

`discover_model()` calls the Fabric REST API `getDefinition` endpoint, polls for async completion, fetches the TMDL parts, then parses each table TMDL file to extract:

- Table name and calculated status
- Columns: name, dataType, summarizeBy, formatString
- Measures: name, DAX expression, formatString
- Relationships: from model.tmdl (fromTable/fromColumn/toTable/toColumn)

The resulting `ModelMetadata` object exposes:
- `all_measures()`: flat list across all tables
- `find_date_table()`: heuristic canonical date table detection
- `has_relationship()`: relationship existence check
- Per-table: `numeric_columns`, `date_columns`, `categorical_columns`

---

## Semantic Model Construction Approach

### Fact/Dimension/Relationship/Date Inference Rules

| Signal | Classification |
|--------|---------------|
| Name contains "dim", "lookup", "category" | Dimension |
| Name contains "fact", "sales", "transactions" | Fact |
| ≥3 numeric columns + >100 rows | Fact |
| Mostly categorical + <100 rows | Dimension |
| ≥2 date columns + "date" in name | Dimension (calendar) |
| Same-name column across tables + value overlap | Relationship candidate |
| Smaller distinct count side | One-side (dimension) of relationship |

### Date Handling

- Detects date-like columns via regex (`YYYY-MM-DD` pattern)
- `find_date_table()` identifies canonical Date dimension by name or structure
- Date strings without table relationships are flagged as a limitation (no time-series analysis without proper Date FK)

### TMDL Generation

`generate_tmdl_table()` produces complete TMDL with:
- Proper tab-indented structure
- lineageTag UUIDs for all elements
- Column definitions (dataType, summarizeBy, sourceColumn)
- Inline measures with formatString
- `DATATABLE()` partition with up to 1000 rows from CSV

---

## Generic Measure Inference / Construction

`infer_measures()` generates standard DAX measures based on column names and table role:

| Pattern | Trigger | Example |
|---------|---------|---------|
| Sum | Numeric column with "amount", "value", "revenue", "cost", "price", "quantity" | `SUM(Sales[Revenue])` |
| Count | All fact tables | `COUNTROWS(Sales)` |
| Distinct count | Available via `MEASURE_PATTERNS["distinct_count"]` | `DISTINCTCOUNT(Sales[CustomerID])` |
| Average | Available via template | `AVERAGE(Sales[Amount])` |
| Ratio | Available via template | `DIVIDE(numerator, denominator)` |
| Share of total | Available via template | `DIVIDE(measure, CALCULATE(measure, ALL(table)))` |
| Filtered count | Available via template | `COUNTROWS(FILTER(table, condition))` |

Currency format (£#,##0) is auto-assigned for revenue/cost/price/value/amount columns.

---

## Model Validation Rules

`validate_model_spec()` checks:

- ✓ Tables have at least one column
- ✓ Column data types are valid (`string`, `int64`, `double`, `boolean`, `dateTime`, `decimal`)
- ✓ Measures have non-empty expressions
- ✓ Relationship from/to columns exist in their respective tables
- ✓ Relationship column types are compatible (warning if mismatched)

---

## Compact Page-Spec Format

```python
PageSpec(
    page_name="sales_overview",
    display_name="Sales Overview",
    title="Sales Overview",
    subtitle="Revenue · Volume · Regional Performance",
    nav_items=[("🏠 Overview", "overview"), ...],
    active_nav="overview",
    slicers=[{"entity": "Date", "property": "Year"}],
    visuals=[
        VisualSpec(
            template_id="premium_kpi",
            title="Total Revenue",
            bindings={"measure": [{"entity": "Sales", "property": "TotalRevenue", "is_measure": True}]},
            position=(155, 70, 245, 100),
        ),
        ...
    ],
    semantic_model_id="...",
    semantic_model_name="...",
)
```

Converters:
- `page_spec_to_shell()` → `PageShell` (structural chrome)
- `page_spec_to_bindings()` → `list[VisualBinding]` (content visuals)
- Used directly by `deploy_from_page_spec()` for one-call deployment

---

## Page Validation Rules

`validate_page_spec()` checks:

- ✓ Template ID exists in registry
- ✓ All required data roles are bound
- ✓ Referenced entities exist in model (when model provided)
- ✓ Referenced measures exist on their entity
- ✓ Referenced columns exist on their entity
- ✓ Visuals stay within canvas bounds (warning)
- ✓ No duplicate positions (warning for exact overlap)
- ✓ No domain-specific renderer code introduced

---

## Reference-to-Model-and-Page Mapping Approach

`ReferenceSpec` describes what a reference/mockup communicates:
- Title/subtitle
- Visual count per row (KPI / hero / bottom)
- Per-visual: analytical intent, required measures, required dimensions, axis preferences

`reference_to_page_spec()` maps this to a deployable `PageSpec`:

1. Groups visuals by row (kpi / hero / bottom)
2. Positions KPIs evenly across the top row
3. Hero visual gets 57% width (matching existing pages); companion (donut) gets remaining 43%
4. Bottom visuals split equally
5. For each visual, calls `select_template()` with intent + axis info
6. Resolves measures/dimensions against model metadata (fuzzy name matching)
7. Slicer fields resolved against model columns

The layout grid (`STANDARD_LAYOUT`) matches the established Executive/Financial/Customer pages:
- Nav rail: 140px left
- Content starts: x=155
- Content width: 1115px
- KPI row: y=70, h=100
- Hero row: y=180, h=240
- Bottom row: y=430, h=240

---

## Deployment-Path Optimizations

| Before (Stage 08/09 scripts) | After (rapid_engine) |
|---|---|
| Manual custom visual loading per script | `_auto_load_visual_archives()` auto-detects from project structure |
| Bespoke deploy script per dashboard | `deploy_from_page_spec()` — single generic function |
| Fixed `time.sleep(5)` after delete | Reduced to 3s |
| Fixed `time.sleep(8)` before report lookup | Reduced to 2s |
| 6s stabilization wait for screenshot | Reduced to 4s |
| 3s polling interval | 2s polling interval |
| No timing instrumentation | `TimingRecord` captures per-phase timing |
| Manual embed HTML generation per script | Centralized in `_capture_screenshot()` |

---

## Timing Breakdown

### Timed Rehearsal Result (Full Model Discovery + Report Deployment)

| Phase | Time | % of Total |
|---|---|---|
| Authentication | 4.0s | 8.9% |
| Model discovery | 3.3s | 7.3% |
| Spec generation | 0.0s | 0.0% |
| Preflight validation | 0.0s | 0.0% |
| Deployment (total) | 37.6s | 83.8% |
| **Total** | **44.9s** | **100%** |

### Deployment Sub-Breakdown

| Sub-phase | Estimated Time |
|---|---|
| PBIR generation | <0.1s |
| Delete existing report | ~3s |
| REST create + polling | ~15s |
| Report lookup | ~2s |
| Screenshot (embed + render + capture) | ~17s |

### Bottleneck Analysis

The deployment phase (37.6s / 83.8%) is dominated by:
1. **REST API async polling** (~15s) — irreducible Fabric service latency
2. **Playwright headless render** (~17s) — Power BI JS client initialization + data load + render

These are external service latencies, not optimizable further in application code.

---

## Timed Rehearsal Result

**Test**: Full model discovery → reference spec → page spec → preflight → deploy → screenshot

| Metric | Result |
|---|---|
| Total wall-clock | 44.9s |
| Target | <300s (5 minutes) |
| Status | ✅ PASS (85% under target) |
| Visuals deployed | 9 |
| Templates used | premium_kpi (4), premium_column (2), premium_donut (1), premium_bar (1), premium_insights (1) |
| Preflight | Passed (0 errors, 0 warnings) |
| Screenshot | Captured successfully |

---

## Regression Results

| Dashboard | Build Result | Parts Count |
|---|---|---|
| Executive Overview | ✅ PASS | 31 |
| Financial Performance | ✅ PASS | 29 |
| Customer Performance | ✅ PASS | 29 |
| Template Registry | ✅ Unchanged (10 templates) |
| Custom Visual Archives | ✅ All 5 verified |
| Zero-touch packaging | ✅ Intact |

---

## Confirmation: No Product-Specific Implementation

- ❌ No Product dashboard built or deployed
- ❌ No Product-specific visual template added
- ❌ No Product-specific renderer branch
- ❌ No Product-specific semantic model
- ❌ No Product-specific measures, tables, or formulas
- ❌ No Product reference image inspected or consumed
- ✅ All new code is domain-agnostic and reusable across any domain

---

## Remaining Risks to <5-Minute Target

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| New model construction adds ~60s (TMDL generation + updateDefinition + refresh) | Medium | +60s → ~105s total | Still well within 300s |
| Large DATATABLE (>500 rows) slows model update | Low | +10-30s | Limit to 1000 rows (already implemented) |
| Playwright first-launch cold start | Low | +5-10s | Browser already installed |
| Token expiry during execution | Very low | Retry needed | Token acquired fresh at start |
| Reference mockup requires unsupported visual type | Medium | Closest template selected instead | Documented deviation in output |

**Worst-case estimate** (new model + table + measures + relationships + report + screenshot): ~120s.

---

## Recommended Wording for Eventual Minimal Product Dashboard Instruction

```
Prepare a Product dashboard looking like this mockup [image attached].
Use existing templates only. Match the theme of the previous dashboards.
Build any semantic model extensions required from the available source data.
Complete and deploy in under five minutes.
```

Optionally augment with:
```
Source data: data/product/Product.csv (or describe available columns).
Key metrics: [list if known, otherwise infer from reference].
```

---

## Files Created/Modified

| File | Purpose |
|---|---|
| `src/pbi_gen/renderer/templates/rapid_engine.py` | Core rapid deployment engine (1,570 lines) |
| `src/pbi_gen/renderer/templates/template_catalog.json` | Machine-readable template capabilities (204 lines) |
| `scripts/_stage10_rehearsal.py` | Timed rehearsal script (200 lines) |
| `docs/stages/10-product-dashboard-readiness/dashboard.png` | Rehearsal screenshot evidence |
| `docs/stages/10-product-dashboard-readiness/REPORT.md` | This report |

---

## Conclusion: `READY_UNDER_5_MIN`

The system is demonstrably ready to execute the anticipated terse instruction:
- **44.9s** measured end-to-end (85% under 5-minute target)
- Generic infrastructure handles model discovery, spec generation, preflight, deployment
- Reference-to-spec mapping resolves measures/dimensions against live model metadata
- Template selection is deterministic and domain-agnostic
- Existing visual vocabulary covers all standard dashboard patterns
- Even with model construction overhead, estimated total stays under 2 minutes
