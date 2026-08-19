# Stage 02a — Live AI Designer Integration Test: REPORT

## Exact test performed

Executed `DashboardDesigner.design_dashboard()` through the full public path (prompt construction → Bedrock Converse API → JSON extraction → Pydantic validation → semantic validation → clarification gate) using the exact prompt specified in the task:

> Create an executive retail performance dashboard for a UK retailer. The primary audience is the CEO and CFO. Show revenue, gross margin, YoY growth, regional performance, product/category performance and major underperformance risks. It should feel premium, restrained and boardroom-ready. Include useful filters for period, region and category.

## Provider / model / region

- **Provider**: Amazon Bedrock (Converse API)
- **Model**: `anthropic.claude-3-7-sonnet-20250219-v1:0` (Claude 3.7 Sonnet)
- **Region**: `eu-west-2`
- **Max tokens**: 32768
- **Temperature**: 0.4
- **No credentials committed** — used locally configured AWS CLI credentials.

## Technical outcome

**DesignOutcome: SUCCESS**

- Elapsed time: **162.1 seconds**
- The full pipeline completed: Bedrock call → JSON parsed → Pydantic validated → semantic validation passed (0 issues) → clarification gate passed (should_clarify=False).
- Generated spec saved as `LIVE_OUTPUT.json` (84KB, 4 pages, 29 visuals, 6 tables, 11 measures).

## Generated artefact

`docs/stages/02a-live-designer-test/LIVE_OUTPUT.json`

## Generated dashboard architecture

| Page | Role | Visuals | Filters |
|------|------|---------|---------|
| Executive Overview | executive_overview | 8 (4 KPI cards, 2 line charts, 2 bar charts) | 3 (period, region, category) |
| Regional Analysis | diagnostic | 7 (3 KPI cards, map, line chart, 2 bar charts) | 2 |
| Category Analysis | diagnostic | 7 (3 KPI cards, donut, line chart, 2 bar charts) | 2 |
| Risk Analysis | diagnostic | 7 (3 KPI cards, scatter, 3 tables) | 3 |

**Semantic model**: 6 tables (Sales, Date, Store, Region, Product, Risk) with 7 relationships, 11 DAX measures including YoY calculations, margin percentages, and risk aggregations.

**Mock data narrative**: 8 analytical patterns (YoY growth, seasonal trends, regional concentration, margin compression, category Pareto, underperformance outliers) with 6 discoverable key insights.

## Quality assessment

### Analytical coherence — **Strong**

The spec derives 5 key analytical questions from the requirement and builds pages that systematically answer them. Each visual has an explicit `analytical_purpose`. The measures are correctly formulated DAX expressions addressing the stated requirements. The Risk Analysis page adds genuine value by surfacing underperformance in a structured way.

### Executive usefulness — **Strong**

The executive overview uses KPI cards for headline numbers (revenue, margin, YoY growth, risk count), trend charts for trajectory, and comparison charts for regional/category context. This follows proven executive dashboard patterns. The 4-page architecture provides summary → diagnostic drill-down, which is appropriate for CEO/CFO.

### Visual-choice appropriateness — **Strong**

- Cards for KPIs ✓
- Line charts for trends over time ✓
- Clustered column/bar for comparisons ✓
- Map for geographic data ✓
- Donut for category contribution (5 categories — acceptable) ✓
- Scatter for risk matrix (innovative choice) ✓
- Tables for detailed risk lists ✓
- No gratuitous gauges, pie charts for many categories, or dashboard wallpaper ✓

### Layout / information hierarchy — **Good**

Visuals use a 3-tier priority system: KPI cards at priority 1, trend/overview visuals at priority 2, detailed breakdown at priority 3. Grid positions show logical grouping. However, the grid uses 12×12 rather than 12×8, which is a minor deviation from the default schema but valid.

### Filters / interactions — **Good**

- 3 slicers on the overview page (period, region, category) — minimal and useful
- Drill-through from overview to detail pages ✓
- Navigation buttons between pages ✓
- Cross-highlight as default interaction ✓
- No excessive filters

### Enterprise aesthetic intent — **Strong**

- Style family: `corporate_restrained` ✓
- Colour roles: deep navy primary, forest green positive, burgundy negative, warm gold accent, slate grey neutral ✓
- Typography: Segoe UI Semibold headings / Segoe UI body ✓
- Density: comfortable with generous whitespace ✓
- Card style: subtle shadow ✓
- Design tone: "premium, restrained and boardroom-ready" ✓
- Emphasis rules include: KPIs largest, negative variance in burgundy, underperformance highlighted ✓

### Mock-data story — **Strong**

The narrative describes a coherent business scenario: a UK retailer with 8% overall growth, regional variation (London strong, Scotland weak), category variation (Beauty/Activewear growing, Formalwear declining), and margin compression from promotional activity. This is genuinely demonstrable data with discoverable insights, not random numbers.

### Structural validity — **Perfect**

- 0 semantic validation issues (all FieldRefs resolve correctly)
- All page IDs unique
- All visual IDs unique within pages
- All relationships reference valid tables/columns
- All filter fields reference valid tables/columns
- No out-of-bounds visual positions

## Clarification-gate result

**should_clarify = False** — correct behaviour for this clear, well-specified prompt. The model generated 4 routine assumptions (fiscal year, margin definition, physical stores, multi-category) but none triggered the critical-impact threshold. 7 confidence assessments showed strong evidence-for on all high-impact dimensions.

## Defects found and fixes made

| Defect | Fix | Impact |
|--------|-----|--------|
| Default model ID `anthropic.claude-sonnet-4-20250514-v1:0` does not exist in eu-west-2 | Changed to `anthropic.claude-3-7-sonnet-20250219-v1:0` | Provider would fail on every call |
| No boto3 read timeout configuration | Added `botocore.config.Config(read_timeout=...)` to Bedrock client | Calls would timeout at default 60s |
| Default `max_tokens=16384` is too low for full spec generation | Increased to `max_tokens=32768` | Specs were truncated mid-JSON |
| No truncation detection (stop_reason check) | Added `max_tokens` stop_reason check in service | Truncated JSON was reported as "not valid JSON" rather than a clear truncation error |
| Prompt allowed reasoning preamble before JSON | Strengthened output format instructions to forbid any non-JSON text | Claude Sonnet 4.5 produced 5KB of reasoning before the JSON |
| Default `timeout_seconds=120` too short | Increased to `timeout_seconds=300` | Complex generation can take 160-370s |

All fixes are small, clearly Stage-02-scoped integration defects as the task's fix policy permits.

## Full automated test result

```
$ .venv\Scripts\pytest.exe tests\ -v
125 passed in 1.67s
```

All Stage 01 (64) and Stage 02 (61) automated tests pass. No tests require network access.

## Known limitations

1. **Generation time** — 162s for a comprehensive spec is slow for interactive CLI use. A faster model (Haiku) or streaming would improve UX.
2. **Claude Sonnet 4.5 extended thinking** — The EU inference profile `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` works but produces reasoning commentary before JSON. Claude 3.7 Sonnet follows the JSON-only instruction correctly.
3. **Grid dimensions** — The model generated a 12×12 grid rather than the default 12×8. This is valid but may need normalisation before rendering.
4. **No cost tracking** — The live call consumed Bedrock tokens but there's no cost reporting in the diagnostics.

## Recommendation

**The project is ready to proceed to the next stage.** The designer produces analytically coherent, structurally valid, enterprise-quality dashboard specifications from natural language. The clarification gate, semantic validator, and typed result model all work correctly in production conditions.

Recommended next focus: synthetic data generation (to make the spec demonstrable as an actual dashboard) or conversational revision (to complete the interactive refinement loop).
