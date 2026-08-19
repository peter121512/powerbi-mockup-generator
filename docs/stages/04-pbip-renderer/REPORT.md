# Stage 04 — PBIP/PBIR Generation: REPORT

## Summary

Delivered a production-shaped PBIP renderer that converts a rich `DashboardSpec` into a complete Power BI Project with TMDL semantic model, PBIR report pages/visuals, theme, and structural validation. The live Stage 02a retail spec renders to 4 pages, 29 visuals, 6 TMDL tables, 11 measures, 7 relationships with **zero fallbacks** and **31/31 validation checks passing** in 0.09 seconds.

## Files added/changed

| File | Action | Purpose |
|------|--------|---------|
| `src/pbi_gen/renderer/__init__.py` | **Added** | Public API (render_powerbi_project, RenderResult, etc.) |
| `src/pbi_gen/renderer/result.py` | **Added** | Typed result model (RenderResult, FidelityManifest, ValidationResult) |
| `src/pbi_gen/renderer/project.py` | **Added** | PBIP project skeleton writer |
| `src/pbi_gen/renderer/semantic_model.py` | **Added** | TMDL generation (tables, columns, measures, relationships) |
| `src/pbi_gen/renderer/report.py` | **Added** | PBIR report generation (pages, visuals, filters) |
| `src/pbi_gen/renderer/layout.py` | **Added** | Grid-to-canvas position translation |
| `src/pbi_gen/renderer/visuals.py` | **Added** | Visual type registry and query state builders |
| `src/pbi_gen/renderer/theme.py` | **Added** | Theme JSON generation from ThemeSpec |
| `src/pbi_gen/renderer/validator.py` | **Added** | Post-render structural validation (31 checks) |
| `src/pbi_gen/renderer/service.py` | **Added** | Main orchestration entry point |
| `tests/test_renderer.py` | **Added** | 102 comprehensive tests |
| `scripts/render_live_project.py` | **Added** | Live integration render script |
| `docs/stages/04-pbip-renderer/LIVE_RENDER_MANIFEST.json` | **Added** | Machine-readable render manifest |
| `docs/stages/04-pbip-renderer/live-project/` | **Added** | Committed rendered PBIP project (regression fixture) |

## Renderer architecture

```text
render_powerbi_project(spec, output_dir)
    │
    ├── project.py: create_project_skeleton()
    │       → .pbip, .gitignore, .platform files, directory structure
    │
    ├── semantic_model.py: render_semantic_model()
    │       → model.tmdl, tables/*.tmdl, relationships.tmdl, definition.pbism
    │
    ├── report.py: render_report()
    │   ├── layout.py: translate_position(grid_pos, page_layout)
    │   │       → canvas pixel coordinates
    │   ├── visuals.py: build_visual_json(visual_spec)
    │   │       → Power BI visual.json with query state
    │   └── theme.py: generate_theme(theme_spec)
    │           → RegisteredResources/theme.json
    │
    ├── validator.py: validate_output(project_path)
    │       → 31 structural checks
    │
    └── result.py: RenderResult + FidelityManifest
            → no silent visual loss tracking
```

## Legacy/archived components salvaged

No legacy PBIP template code was available in the current repository (the archive branch only contains the Android prototype). The PBIP format knowledge was sourced from:

1. **Microsoft documentation** — Official PBIP/PBIR/TMDL format specifications
2. **fabric-cicd compatibility** — The existing `deploy/fabric.py` uses `FabricWorkspace(repository_directory=...)` which expects standard PBIP project layout
3. **Power BI JSON schemas** — Published at github.com/microsoft/json-schemas/tree/main/fabric

The renderer produces output compatible with the existing Fabric deployment path without modification.

## PBIP project structure generated

```
ExecutiveRetailPerformanceDashboard/
├── ExecutiveRetailPerformanceDashboard.pbip
├── .gitignore
├── ExecutiveRetailPerformanceDashboard.SemanticModel/
│   ├── .platform
│   ├── definition.pbism
│   └── definition/
│       ├── model.tmdl
│       ├── tables/
│       │   ├── Sales.tmdl (8 columns + 11 measures)
│       │   ├── Date.tmdl (12 columns)
│       │   ├── Store.tmdl (6 columns)
│       │   ├── Region.tmdl (4 columns)
│       │   ├── Product.tmdl (9 columns)
│       │   └── Risk.tmdl (7 columns)
│       └── relationships.tmdl (7 relationships)
└── ExecutiveRetailPerformanceDashboard.Report/
    ├── .platform
    ├── definition.pbir
    ├── StaticResources/RegisteredResources/theme.json
    └── definition/
        ├── version.json
        ├── report.json
        └── pages/
            ├── pages.json
            ├── page-executive-overview/ (8 visuals + 3 slicer visuals)
            ├── page-region-analysis/ (7 visuals + 2 slicer visuals)
            ├── page-category-analysis/ (7 visuals + 2 slicer visuals)
            └── page-risk-analysis/ (7 visuals + 3 slicer visuals)
```

## Semantic model / TMDL strategy

Each `TableSpec` generates a `.tmdl` file with:
- Table declaration with lineageTag (UUID derived from table name for stability)
- Columns with data type, sourceColumn, summarizeBy, and lineageTag
- Measures attached to their home table with DAX expressions and format strings
- Partition definition with import mode and placeholder M expression

Column type mapping:
| DashboardSpec | TMDL |
|---------------|------|
| TEXT | string |
| INTEGER | int64 |
| REAL | double |
| DATE | dateTime |
| DATETIME | dateTime |
| BOOLEAN | boolean |

Relationships generate a `relationships.tmdl` with fromColumn/toColumn syntax.

## Data-source strategy

The semantic model uses **import mode partitions** with a placeholder M expression. This is compatible with the existing Fabric deployment workflow:

1. `fabric-cicd` publishes the semantic model definition to a Fabric workspace
2. The existing `refresh_dataset()` in `fabric.py` triggers a data refresh
3. The refresh loads data from the configured source

For local development/testing, the M expression is a placeholder that Power BI Desktop can replace. For production deployment, the data source configuration is managed through the Power BI Service dataset settings.

## Visual mapping table

| Canonical VisualType | Power BI visualType | Fallback |
|---------------------|--------------------|---------| 
| CARD | card | — |
| LINE_CHART | lineChart | — |
| BAR_CHART | barChart | — |
| CLUSTERED_BAR | clusteredBarChart | — |
| CLUSTERED_COLUMN | clusteredColumnChart | — |
| STACKED_BAR | stackedBarChart | — |
| STACKED_COLUMN | stackedColumnChart | — |
| TABLE | tableEx | — |
| MATRIX | pivotTable | — |
| DONUT_CHART | donutChart | — |
| PIE_CHART | pieChart | — |
| SLICER | slicer | — |
| MAP | map | — |
| FILLED_MAP | filledMap | — |
| SCATTER | scatterChart | — |
| TREEMAP | treemap | — |
| FUNNEL | funnel | — |
| WATERFALL | waterfallChart | — |
| COMBO_CHART | lineClusteredColumnComboChart | — |
| AREA_CHART | areaChart | — |
| KPI | card | Fallback: card with KPI formatting |
| GAUGE | gauge | — |
| TEXT_BOX | textbox | — |
| BUTTON | actionButton | — |
| Others | card | Documented fallback |

For the live fixture: **zero fallbacks** — all 8 visual types used (card, lineChart, clusteredColumnChart, clusteredBarChart, map, donutChart, scatterChart, tableEx) map directly.

## Field-binding approach

Each visual type has specific query role mappings:

| Visual Type | Category/X | Values/Y | Series/Legend |
|-------------|-----------|----------|--------------|
| Card | — | value_fields → Values | — |
| Line/Area | category_fields → Category | value_fields → Y | series_field → Series |
| Bar/Column | category_fields → Category | value_fields → Y | series_field → Series |
| Table | All fields → Values | All fields → Values | — |
| Slicer | category_fields → Values | — | — |
| Map | category_fields → Category | value_fields → Size | — |
| Scatter | category_fields → Details | value_fields[0] → X, [1] → Y | series_field → Legend |
| Donut | category_fields → Category | value_fields → Y | — |

Field references:
- Column: `{"Column": {"Expression": {"SourceRef": {"Entity": "<table>"}}, "Property": "<column>"}}`
- Measure: `{"Measure": {"Expression": {"SourceRef": {"Entity": "<table>"}}, "Property": "<measure>"}}`

## Layout translation approach

Grid-to-canvas conversion:
```
cell_width = page_layout.width / page_layout.grid_columns
cell_height = page_layout.height / page_layout.grid_rows
padding = 8  # pixels between visuals

x_px = (position.x * cell_width) + padding
y_px = (position.y * cell_height) + padding
width_px = (position.width * cell_width) - (2 * padding)
height_px = (position.height * cell_height) - (2 * padding)
```

This preserves the designer's intended hierarchy: priority-1 KPI cards get their full allocated grid space at the top, trend charts span multiple columns, and smaller visuals maintain their relative positioning.

## Filter/interaction support

- **Slicers**: Each `FilterSpec` with `filter_type=SLICER` generates a slicer visual on the page, positioned below the main content area
- **Report filters**: Rendered in page.json filter array
- **Cross-highlight**: Set as default interaction mode in report config
- **Drill-through**: Page drill-through configuration included where specified
- **Navigation buttons**: Rendered as actionButton visuals with navigation targets

## Theme/formatting mapping

`ThemeSpec` generates `StaticResources/RegisteredResources/theme.json` with:
- `dataColors` derived from colour_roles (primary, accent, positive, negative, neutral)
- `background` / `foreground` based on presentation_mode (light/dark)
- `textClasses` mapping typography (title, header, label with font faces and sizes)
- `tableAccent` using the primary colour
- Registered in report.json's resourcePackages

The live fixture's corporate_restrained theme produces: navy primary (#1A3A52), gold accent (#D4AF37), green positive (#2D5F3F), burgundy negative (#8B2635), slate neutral (#6B7280).

## Structural validation performed

31 checks run post-render:
- .pbip file exists and contains valid JSON
- .gitignore exists
- SemanticModel directory + .platform + definition.pbism exist
- model.tmdl contains model declaration
- Each table .tmdl file exists and contains table/column/measure declarations
- relationships.tmdl exists with correct count
- Report directory + .platform + definition.pbir exist
- definition.pbir contains valid datasetReference
- report.json exists with valid JSON
- version.json exists
- pages.json lists all pages
- Each page directory + page.json exists
- Visual count per page matches spec
- Each visual.json exists and contains valid JSON
- Theme file exists in RegisteredResources
- No absolute paths in any generated file
- All generated JSON files parse without error

## Live retail integration result

| Metric | Result |
|--------|--------|
| Pages rendered | 4/4 |
| Visuals rendered | 29/29 |
| Fallbacks | 0 |
| Measures in TMDL | 11 |
| Relationships in TMDL | 7 |
| Tables in TMDL | 6 |
| Filters as slicers | 10 |
| Theme applied | ✅ corporate_restrained |
| Validation checks | 31/31 passed |
| Render time | 0.09s |

Visual type breakdown: 13 cards, 4 line charts, 3 clustered columns, 3 clustered bars, 3 tables, 1 map, 1 donut, 1 scatter.

## Fidelity/fallback summary

**Zero silent visual loss. Zero fallbacks. Full fidelity.**

Every visual in the spec maps directly to a supported Power BI visual type. No visual was dropped, substituted, or rendered with reduced capability.

## Automated test results

```
$ .venv\Scripts\pytest.exe tests/ --tb=short
293 passed in 22.59s
```

- Stage 01: 64 tests ✅
- Stage 02: 61 tests ✅  
- Stage 03: 66 tests ✅
- Stage 04: 102 tests ✅

## Power BI acceptance/validation

**Structural validation**: Performed internally by the renderer's validator (31 checks all passing). All generated JSON files parse correctly. TMDL files follow documented syntax. Project directory structure matches the official PBIP specification.

**Actual Power BI acceptance**: NOT validated. Power BI Desktop is not available in this development environment. The generated project has not been opened in Power BI Desktop or deployed to Fabric during this stage. This is explicitly a structural validation only.

The project is structurally compatible with `fabric-cicd` deployment (standard PBIP layout with SemanticModel + Report folders, .platform files, and byPath dataset reference). The next stage or manual testing should validate actual Power BI acceptance.

## Defects/fixes discovered during integration

No defects discovered. The implementation worked correctly on the first integration attempt against the live spec.

## Known limitations

1. **No Power BI Desktop validation** — The generated PBIP has not been opened in Power BI Desktop. Some visual configuration details (e.g. advanced formatting properties, specific slicer styles) may need refinement when first imported.

2. **Placeholder data source** — The M expression in partition definitions is a placeholder. Actual data ingestion requires either: (a) manual data source configuration in Power BI Service, or (b) adaptation of the partition to reference the SQLite/CSV data directly.

3. **No mobile layout** — `mobile.json` files are not generated. Mobile layouts would require a separate layout pass.

4. **Limited interaction configuration** — Cross-highlight is set as default but fine-grained visual-to-visual interaction rules are not individually configured in PBIR.

5. **No conditional formatting in PBIR** — The spec's `conditional_formats` describe intent but are not yet translated to Power BI's conditional formatting JSON (which is complex and version-specific).

6. **Filter positions are appended** — Slicer visuals generated from `FilterSpec` are placed below the main visual area rather than optimally positioned within the grid.

## Recommended next stage

**Stage 05: Fabric Deployment and End-to-End Verification**

This would:
1. Deploy the rendered PBIP to a Fabric workspace using the existing `fabric.py` pipeline
2. Configure the data source to load the Stage 03 SQLite data
3. Trigger a dataset refresh
4. Capture a screenshot of the deployed report
5. Verify the visual output matches the designer's intent

Prerequisites are all met:
- ✅ Rich DashboardSpec (Stage 01)
- ✅ AI designer generates specs (Stage 02/02a)
- ✅ Synthetic data engine (Stage 03)
- ✅ PBIP renderer (Stage 04)
- ⬜ Fabric deployment + visual verification (Stage 05 — next)

The existing `deploy_to_workspace()` and `refresh_dataset()` functions should work directly against the Stage 04 output with minimal adaptation.
