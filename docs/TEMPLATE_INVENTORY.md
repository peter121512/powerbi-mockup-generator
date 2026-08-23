# Visual Template Inventory

## Available Visual Templates (10 total)

### 1. `premium_kpi` — Headline Metric Card
- **Use**: Single KPI with value + optional delta indicator
- **Page role**: Top KPI row
- **Data**: 1 measure (required) + 1 delta measure (optional)
- **Accepts**: numeric, percentage, currency
- **Size**: 245×100
- **Type**: Custom visual (dark card with spark indicator)
- **Limits**: No cross-highlight, no drill-through

### 2. `premium_trend` — Area/Line Trend Chart
- **Use**: Time-series or ordered-dimension trend with gradient fill
- **Page role**: Hero, Trend
- **Data**: 1 category axis + 1–4 measure series
- **Accepts**: category must be date/numeric/month_number — NOT string categories (shows NaN)
- **Size**: 635×240
- **Type**: Custom visual with internal Monthly/Quarterly/Annual toggle
- **Limits**: String categories break it. Best with 6–24 x-axis points.

### 3. `premium_bar` — Horizontal Bar Chart
- **Use**: Categorical comparison or ranking
- **Page role**: Breakdown, Ranking
- **Data**: 1 string category + 1–3 measures
- **Accepts**: string/categorical categories, numeric/currency/count values
- **Size**: 365×240
- **Type**: Native PBI bar chart with dark styling + data labels
- **Limits**: Best with 3–8 categories. Long labels may truncate.

### 4. `premium_column` — Vertical Column Chart
- **Use**: Categorical comparison, grouped series, distribution
- **Page role**: Hero, Breakdown, Comparison
- **Data**: 1 category + 1–4 measures
- **Accepts**: string, categorical, date, numeric_ordinal categories; numeric/currency/count values
- **Size**: 365×240
- **Type**: Native PBI column chart with legend + dark styling
- **Limits**: Best with 3–12 categories. Multiple measures → grouped columns.

### 5. `premium_donut` — Donut Chart
- **Use**: Part-to-whole composition / share
- **Page role**: Composition, Breakdown
- **Data**: 1 category + 1 measure
- **Accepts**: string/categorical categories; numeric/currency/count values
- **Size**: 470×240
- **Type**: Native PBI donut with legend + labels
- **Limits**: Best with 3–7 categories. Can pair with donut_center_kpi overlay.

### 6. `premium_table` — Data Table
- **Use**: Detailed tabular display with multiple columns
- **Page role**: Detail, Breakdown
- **Data**: 1–6 grouping columns + 1–8 value measures
- **Accepts**: string/date columns; numeric/currency/percentage/count values
- **Size**: 375×260
- **Type**: Native PBI enhanced table with dark row colours
- **Limits**: Shows ~6–8 rows. Wide tables may scroll.

### 7. `premium_waterfall` — Waterfall/Bridge Chart
- **Use**: Incremental contribution analysis (e.g., revenue → costs → profit)
- **Page role**: Breakdown, Bridge
- **Data**: 1 category + 1 measure
- **Accepts**: string/categorical categories; numeric/currency values (signed)
- **Size**: 375×260
- **Type**: Custom visual
- **Limits**: Best with 4–8 steps. Needs signed values for bridge effect.

### 8. `premium_gauge` — Radial Gauge
- **Use**: Single metric against a target/scale (NPS, satisfaction, progress)
- **Page role**: Hero, KPI
- **Data**: 1 measure
- **Accepts**: numeric, percentage
- **Size**: 365×240
- **Type**: Custom visual with animated needle
- **Limits**: Currently hardcoded to NPS-style (89 + KPI boxes). No configurable target via data.

### 9. `donut_center_kpi` — Transparent Center Overlay
- **Use**: Show a single value in the center of a donut chart
- **Page role**: Overlay (positioned over a donut)
- **Data**: 1 measure (but title text is set statically via config)
- **Size**: 100×44
- **Type**: Native PBI card (transparent background)
- **Limits**: Static title text only. Must be manually positioned over a donut.

### 10. `premium_insights` — Key Insights Panel
- **Use**: 4-row narrative insights with colored icon circles
- **Page role**: Insight (bottom right)
- **Data**: 1 measure (trigger only — text is hardcoded in visual source)
- **Size**: 365×240
- **Type**: Custom visual
- **Limits**: Text is hardcoded. Changing insight text requires rebuilding the .pbiviz. 4 fixed rows.

---

## Intent → Template Mapping

| Analytical Intent | Template(s) | Selection Rule |
|---|---|---|
| `headline_metric` | premium_kpi | Always |
| `time_trend` | premium_trend OR premium_column | premium_trend if numeric/date axis; premium_column if string categories |
| `categorical_comparison` | premium_column OR premium_bar | premium_bar if horizontal preferred |
| `ranking` | premium_bar | Always |
| `composition_share` | premium_donut | Always |
| `distribution` | premium_column | Always |
| `bridge_waterfall` | premium_waterfall | Always |
| `progress_gauge` | premium_gauge | Always |
| `detail_table` | premium_table | Always |
| `narrative_insight` | premium_insights | Always |
| `center_overlay` | donut_center_kpi | Always |

---

## Standard Page Layout Grid

- Canvas: 1280×720
- Nav rail: 140px left (dark, with active indicator)
- Content area: starts x=155, width=1115
- **KPI row**: y=70, h=100 (typically 4 KPIs evenly spaced)
- **Hero row**: y=180, h=240 (57% hero chart + 43% companion, typically donut)
- **Bottom row**: y=430, h=240 (typically 3 visuals evenly split)
- Gutter: 10px between all visuals
- Theme: dark navy (#0f1623 canvas, #151d2e surface panels, #1e293b borders)
