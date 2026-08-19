"""Comprehensive tests for the PBIP/PBIR renderer (Stage 04).

Tests cover:
1. Project skeleton creation
2. Semantic model TMDL generation
3. Column type mapping
4. Measure/DAX rendering
5. Relationship TMDL rendering
6. Page generation
7. Grid-to-canvas layout translation
8. Visual type mapping
9. Field bindings
10. Filter/slicer rendering
11. Theme generation
12. Unsupported visual fallback
13. No silent visual loss
14. Output structural validation
15. Deterministic render
16. Full LIVE_OUTPUT.json integration
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from pbi_gen.models import (
    ColourRole,
    ColumnSpec,
    DashboardIntent,
    DashboardSpec,
    FieldRef,
    FilterSpec,
    FilterType,
    MeasureSpec,
    PageLayout,
    PageSpec,
    PresentationMode,
    Relationship,
    RelationshipCardinality,
    TableSpec,
    ThemeSpec,
    TypographySpec,
    VisualPosition,
    VisualSpec,
    VisualType,
)
from pbi_gen.renderer import (
    CanvasPosition,
    FidelityManifest,
    RenderOutcome,
    RenderResult,
    VISUAL_TYPE_MAP,
    build_field_ref,
    build_query_ref,
    build_query_state,
    grid_to_canvas,
    map_visual_type,
    position_to_dict,
    render_powerbi_project,
)
from pbi_gen.renderer.layout import DEFAULT_PADDING_PX
from pbi_gen.renderer.semantic_model import (
    COLUMN_TYPE_MAP,
    generate_model_tmdl,
    generate_relationships_tmdl,
    generate_table_tmdl,
    map_column_type,
)
from pbi_gen.renderer.theme import generate_theme
from pbi_gen.renderer.validator import validate_pbip_project


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test output."""
    d = tempfile.mkdtemp(prefix="test_renderer_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def minimal_spec():
    """Create a minimal valid DashboardSpec for testing."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="Test Dashboard",
            business_purpose="Testing",
        ),
        pages=[
            PageSpec(
                id="page-test",
                title="Test Page",
                visuals=[
                    VisualSpec(
                        id="vis-test-card",
                        visual_type=VisualType.CARD,
                        title="Test Card",
                        value_fields=[
                            FieldRef(table="Sales", measure="TotalRevenue"),
                        ],
                        position=VisualPosition(x=0, y=0, width=3, height=1),
                    ),
                ],
            ),
        ],
        tables=[
            TableSpec(
                name="Sales",
                columns=[
                    ColumnSpec(name="SalesID", data_type="TEXT", is_key=True),
                    ColumnSpec(name="Revenue", data_type="REAL"),
                ],
            ),
        ],
        measures=[
            MeasureSpec(
                name="TotalRevenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
                format_string="£#,0",
            ),
        ],
    )


@pytest.fixture
def multi_page_spec():
    """Create a multi-page spec with various visual types."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="Multi Page Dashboard",
            business_purpose="Testing multiple pages and visual types",
        ),
        pages=[
            PageSpec(
                id="page-overview",
                title="Overview",
                sort_order=0,
                visuals=[
                    VisualSpec(
                        id="vis-card-1",
                        visual_type=VisualType.CARD,
                        title="Revenue",
                        value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
                        position=VisualPosition(x=0, y=0, width=3, height=1),
                    ),
                    VisualSpec(
                        id="vis-line-1",
                        visual_type=VisualType.LINE_CHART,
                        title="Trend",
                        category_fields=[FieldRef(table="Date", column="MonthName")],
                        value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
                        position=VisualPosition(x=0, y=1, width=8, height=3),
                    ),
                    VisualSpec(
                        id="vis-bar-1",
                        visual_type=VisualType.CLUSTERED_BAR,
                        title="By Region",
                        category_fields=[FieldRef(table="Region", column="RegionName")],
                        value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
                        position=VisualPosition(x=8, y=1, width=4, height=3),
                    ),
                ],
                filters=[
                    FilterSpec(
                        id="filter-year",
                        filter_type=FilterType.SLICER,
                        field=FieldRef(table="Date", column="Year"),
                        label="Year",
                    ),
                ],
            ),
            PageSpec(
                id="page-detail",
                title="Detail",
                sort_order=1,
                visuals=[
                    VisualSpec(
                        id="vis-table-1",
                        visual_type=VisualType.TABLE,
                        title="Sales Detail",
                        category_fields=[
                            FieldRef(table="Store", column="StoreName"),
                        ],
                        value_fields=[
                            FieldRef(table="Sales", measure="TotalRevenue"),
                        ],
                        position=VisualPosition(x=0, y=0, width=12, height=6),
                    ),
                ],
            ),
        ],
        tables=[
            TableSpec(
                name="Sales",
                columns=[
                    ColumnSpec(name="SalesID", data_type="TEXT", is_key=True),
                    ColumnSpec(name="Revenue", data_type="REAL"),
                    ColumnSpec(name="Date", data_type="DATE"),
                    ColumnSpec(name="StoreID", data_type="TEXT"),
                ],
            ),
            TableSpec(
                name="Date",
                columns=[
                    ColumnSpec(name="Date", data_type="DATE", is_key=True),
                    ColumnSpec(name="MonthName", data_type="TEXT"),
                    ColumnSpec(name="Year", data_type="INTEGER"),
                ],
            ),
            TableSpec(
                name="Store",
                columns=[
                    ColumnSpec(name="StoreID", data_type="TEXT", is_key=True),
                    ColumnSpec(name="StoreName", data_type="TEXT"),
                    ColumnSpec(name="RegionID", data_type="TEXT"),
                ],
            ),
            TableSpec(
                name="Region",
                columns=[
                    ColumnSpec(name="RegionID", data_type="TEXT", is_key=True),
                    ColumnSpec(name="RegionName", data_type="TEXT"),
                ],
            ),
        ],
        relationships=[
            Relationship(
                from_table="Sales",
                from_column="Date",
                to_table="Date",
                to_column="Date",
            ),
            Relationship(
                from_table="Sales",
                from_column="StoreID",
                to_table="Store",
                to_column="StoreID",
            ),
            Relationship(
                from_table="Store",
                from_column="RegionID",
                to_table="Region",
                to_column="RegionID",
            ),
        ],
        measures=[
            MeasureSpec(
                name="TotalRevenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
                format_string="£#,0",
            ),
        ],
        theme=ThemeSpec(
            presentation_mode=PresentationMode.LIGHT,
            style_family="corporate_restrained",
            colour_roles=[
                ColourRole(role="primary", intent="corporate identity"),
                ColourRole(role="positive", intent="growth", hex_value="#007E33"),
                ColourRole(role="negative", intent="decline", hex_value="#CC0000"),
            ],
            typography=TypographySpec(
                heading_font="Segoe UI Light",
                body_font="Segoe UI",
                base_size_pt=10.0,
            ),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Project Skeleton Creation
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectSkeleton:
    """Tests for project directory structure creation."""

    def test_creates_project_root(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        assert result.success
        assert result.output_path.is_dir()

    def test_creates_pbip_file(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        pbip = result.output_path / f"{result.project_name}.pbip"
        assert pbip.is_file()

    def test_creates_gitignore(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        gitignore = result.output_path / ".gitignore"
        assert gitignore.is_file()

    def test_creates_semantic_model_dir(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        sm_dir = result.output_path / f"{result.project_name}.SemanticModel"
        assert sm_dir.is_dir()

    def test_creates_report_dir(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        rpt_dir = result.output_path / f"{result.project_name}.Report"
        assert rpt_dir.is_dir()

    def test_creates_semantic_model_definition(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        sm_def = result.output_path / f"{result.project_name}.SemanticModel" / "definition"
        assert sm_def.is_dir()
        assert (sm_def / "model.tmdl").is_file()
        assert (sm_def / "tables").is_dir()

    def test_creates_report_definition(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        rpt_def = result.output_path / f"{result.project_name}.Report" / "definition"
        assert rpt_def.is_dir()
        assert (rpt_def / "report.json").is_file()
        assert (rpt_def / "version.json").is_file()
        assert (rpt_def / "pages" / "pages.json").is_file()

    def test_creates_platform_files(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        sm_platform = result.output_path / f"{result.project_name}.SemanticModel" / ".platform"
        rpt_platform = result.output_path / f"{result.project_name}.Report" / ".platform"
        assert sm_platform.is_file()
        assert rpt_platform.is_file()

    def test_creates_theme_file(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        theme = (
            result.output_path
            / f"{result.project_name}.Report"
            / "StaticResources"
            / "RegisteredResources"
            / "theme.json"
        )
        assert theme.is_file()

    def test_custom_project_name(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir, project_name="CustomName")
        assert result.project_name == "CustomName"
        assert result.output_path.name == "CustomName"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Semantic Model TMDL Generation
# ─────────────────────────────────────────────────────────────────────────────


class TestSemanticModelTMDL:
    """Tests for TMDL generation."""

    def test_model_tmdl_content(self):
        content = generate_model_tmdl()
        assert "model Model" in content
        assert "culture: en-US" in content
        assert "defaultPowerBIDataSourceVersion: powerBI_V3" in content

    def test_table_tmdl_has_table_name(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="SalesID", data_type="TEXT", is_key=True)],
        )
        content = generate_table_tmdl(table)
        assert content.startswith("table Sales")

    def test_table_tmdl_has_lineage_tag(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="SalesID", data_type="TEXT", is_key=True)],
        )
        content = generate_table_tmdl(table)
        assert "lineageTag:" in content

    def test_table_tmdl_has_columns(self):
        table = TableSpec(
            name="Sales",
            columns=[
                ColumnSpec(name="SalesID", data_type="TEXT", is_key=True),
                ColumnSpec(name="Revenue", data_type="REAL"),
            ],
        )
        content = generate_table_tmdl(table)
        assert "column SalesID" in content
        assert "column Revenue" in content

    def test_table_tmdl_key_column(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="SalesID", data_type="TEXT", is_key=True)],
        )
        content = generate_table_tmdl(table)
        assert "isKey: true" in content

    def test_table_tmdl_has_partition(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="SalesID", data_type="TEXT", is_key=True)],
        )
        content = generate_table_tmdl(table)
        assert "partition Sales = m" in content
        assert "mode: import" in content

    def test_table_tmdl_partition_references_csv(self):
        table = TableSpec(
            name="Store",
            columns=[ColumnSpec(name="StoreID", data_type="TEXT", is_key=True)],
        )
        content = generate_table_tmdl(table)
        assert "data/Store.csv" in content

    def test_table_file_written_per_table(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        tables_dir = (
            result.output_path
            / f"{result.project_name}.SemanticModel"
            / "definition"
            / "tables"
        )
        assert (tables_dir / "Sales.tmdl").is_file()
        assert (tables_dir / "Date.tmdl").is_file()
        assert (tables_dir / "Store.tmdl").is_file()
        assert (tables_dir / "Region.tmdl").is_file()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Column Type Mapping
# ─────────────────────────────────────────────────────────────────────────────


class TestColumnTypeMapping:
    """Tests for column data type mapping."""

    def test_text_to_string(self):
        assert map_column_type("TEXT") == "string"

    def test_integer_to_int64(self):
        assert map_column_type("INTEGER") == "int64"

    def test_real_to_double(self):
        assert map_column_type("REAL") == "double"

    def test_date_to_datetime(self):
        assert map_column_type("DATE") == "dateTime"

    def test_datetime_to_datetime(self):
        assert map_column_type("DATETIME") == "dateTime"

    def test_boolean_to_boolean(self):
        assert map_column_type("BOOLEAN") == "boolean"

    def test_case_insensitive(self):
        assert map_column_type("text") == "string"
        assert map_column_type("Text") == "string"

    def test_unknown_defaults_to_string(self):
        assert map_column_type("UNKNOWN") == "string"

    def test_tmdl_uses_correct_type(self):
        table = TableSpec(
            name="T",
            columns=[
                ColumnSpec(name="A", data_type="INTEGER"),
                ColumnSpec(name="B", data_type="REAL"),
                ColumnSpec(name="C", data_type="BOOLEAN"),
            ],
        )
        content = generate_table_tmdl(table)
        assert "dataType: int64" in content
        assert "dataType: double" in content
        assert "dataType: boolean" in content


# ─────────────────────────────────────────────────────────────────────────────
# 4. Measure/DAX Rendering
# ─────────────────────────────────────────────────────────────────────────────


class TestMeasureRendering:
    """Tests for DAX measure rendering in TMDL."""

    def test_measure_in_table_tmdl(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="Revenue", data_type="REAL")],
        )
        measures = [
            MeasureSpec(
                name="TotalRevenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
                format_string="£#,0",
            )
        ]
        content = generate_table_tmdl(table, measures)
        assert "measure TotalRevenue = SUM(Sales[Revenue])" in content
        assert "formatString: £#,0" in content

    def test_measure_with_spaces_is_quoted(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="Revenue", data_type="REAL")],
        )
        measures = [
            MeasureSpec(
                name="Total Revenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
            )
        ]
        content = generate_table_tmdl(table, measures)
        assert "measure 'Total Revenue' = SUM(Sales[Revenue])" in content

    def test_measure_has_lineage_tag(self):
        table = TableSpec(
            name="Sales",
            columns=[ColumnSpec(name="Revenue", data_type="REAL")],
        )
        measures = [
            MeasureSpec(
                name="TotalRevenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
            )
        ]
        content = generate_table_tmdl(table, measures)
        # Find the measure section and check it has a lineageTag
        lines = content.split("\n")
        measure_idx = next(i for i, l in enumerate(lines) if "measure TotalRevenue" in l)
        # lineageTag should be within next few lines
        nearby = "\n".join(lines[measure_idx : measure_idx + 5])
        assert "lineageTag:" in nearby

    def test_measure_only_in_home_table(self):
        table = TableSpec(
            name="Date",
            columns=[ColumnSpec(name="Date", data_type="DATE", is_key=True)],
        )
        measures = [
            MeasureSpec(
                name="TotalRevenue",
                expression="SUM(Sales[Revenue])",
                table="Sales",
            )
        ]
        content = generate_table_tmdl(table, measures)
        assert "measure" not in content


# ─────────────────────────────────────────────────────────────────────────────
# 5. Relationship TMDL Rendering
# ─────────────────────────────────────────────────────────────────────────────


class TestRelationshipRendering:
    """Tests for relationship TMDL generation."""

    def test_relationship_has_from_to(self):
        rels = [
            Relationship(
                from_table="Sales",
                from_column="StoreID",
                to_table="Store",
                to_column="StoreID",
            )
        ]
        content = generate_relationships_tmdl(rels)
        assert "fromColumn: Sales.StoreID" in content
        assert "toColumn: Store.StoreID" in content

    def test_relationship_has_identifier(self):
        rels = [
            Relationship(
                from_table="Sales",
                from_column="Date",
                to_table="Date",
                to_column="Date",
            )
        ]
        content = generate_relationships_tmdl(rels)
        assert content.startswith("relationship ")

    def test_multiple_relationships(self):
        rels = [
            Relationship(from_table="Sales", from_column="StoreID", to_table="Store", to_column="StoreID"),
            Relationship(from_table="Store", from_column="RegionID", to_table="Region", to_column="RegionID"),
        ]
        content = generate_relationships_tmdl(rels)
        assert "Sales.StoreID" in content
        assert "Store.RegionID" in content

    def test_empty_relationships(self):
        content = generate_relationships_tmdl([])
        assert content == ""

    def test_relationship_file_written(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        rel_file = (
            result.output_path
            / f"{result.project_name}.SemanticModel"
            / "definition"
            / "relationships.tmdl"
        )
        assert rel_file.is_file()
        content = rel_file.read_text(encoding="utf-8")
        assert "Sales.Date" in content


# ─────────────────────────────────────────────────────────────────────────────
# 6. Page Generation
# ─────────────────────────────────────────────────────────────────────────────


class TestPageGeneration:
    """Tests for report page generation."""

    def test_pages_json_has_all_pages(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        pages_json_path = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition"
            / "pages"
            / "pages.json"
        )
        data = json.loads(pages_json_path.read_text(encoding="utf-8"))
        assert len(data["pageOrder"]) == 2
        assert "page-overview" in data["pageOrder"]
        assert "page-detail" in data["pageOrder"]

    def test_pages_ordered_by_sort_order(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        pages_json_path = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition"
            / "pages"
            / "pages.json"
        )
        data = json.loads(pages_json_path.read_text(encoding="utf-8"))
        assert data["pageOrder"][0] == "page-overview"
        assert data["activePageName"] == "page-overview"

    def test_page_json_has_correct_fields(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        page_json_path = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition"
            / "pages"
            / "page-overview"
            / "page.json"
        )
        data = json.loads(page_json_path.read_text(encoding="utf-8"))
        assert data["name"] == "page-overview"
        assert data["displayName"] == "Overview"
        assert data["displayOption"] == "FitToPage"
        assert data["height"] == 720
        assert data["width"] == 1280

    def test_page_directory_created_per_page(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        pages_dir = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition"
            / "pages"
        )
        assert (pages_dir / "page-overview" / "page.json").is_file()
        assert (pages_dir / "page-detail" / "page.json").is_file()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Grid-to-Canvas Layout Translation
# ─────────────────────────────────────────────────────────────────────────────


class TestLayoutTranslation:
    """Tests for grid-to-canvas position translation."""

    def test_origin_position(self):
        pos = VisualPosition(x=0, y=0, width=3, height=1)
        layout = PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8)
        result = grid_to_canvas(pos, layout)
        assert result.x == DEFAULT_PADDING_PX
        assert result.y == DEFAULT_PADDING_PX

    def test_width_calculation(self):
        pos = VisualPosition(x=0, y=0, width=6, height=4)
        layout = PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8)
        result = grid_to_canvas(pos, layout)
        expected_width = (6 * (1280 / 12)) - 2 * DEFAULT_PADDING_PX
        assert result.width == round(expected_width, 2)

    def test_height_calculation(self):
        pos = VisualPosition(x=0, y=0, width=6, height=4)
        layout = PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8)
        result = grid_to_canvas(pos, layout)
        expected_height = (4 * (720 / 8)) - 2 * DEFAULT_PADDING_PX
        assert result.height == round(expected_height, 2)

    def test_offset_position(self):
        pos = VisualPosition(x=3, y=2, width=6, height=3)
        layout = PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8)
        result = grid_to_canvas(pos, layout)
        expected_x = 3 * (1280 / 12) + DEFAULT_PADDING_PX
        expected_y = 2 * (720 / 8) + DEFAULT_PADDING_PX
        assert result.x == round(expected_x, 2)
        assert result.y == round(expected_y, 2)

    def test_z_index_passthrough(self):
        pos = VisualPosition(x=0, y=0, width=3, height=1)
        layout = PageLayout()
        result = grid_to_canvas(pos, layout, z_index=2000)
        assert result.z == 2000

    def test_tab_order_passthrough(self):
        pos = VisualPosition(x=0, y=0, width=3, height=1)
        layout = PageLayout()
        result = grid_to_canvas(pos, layout, tab_order=5)
        assert result.tab_order == 5

    def test_position_to_dict(self):
        cp = CanvasPosition(x=10.0, y=20.0, z=1000, width=300.0, height=150.0, tab_order=2)
        d = position_to_dict(cp)
        assert d == {
            "x": 10.0,
            "y": 20.0,
            "z": 1000,
            "width": 300.0,
            "height": 150.0,
            "tabOrder": 2,
        }

    def test_full_width_visual(self):
        pos = VisualPosition(x=0, y=0, width=12, height=8)
        layout = PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8)
        result = grid_to_canvas(pos, layout)
        # Full width minus padding
        assert result.width == round(1280 - 2 * DEFAULT_PADDING_PX, 2)
        assert result.height == round(720 - 2 * DEFAULT_PADDING_PX, 2)

    def test_custom_padding(self):
        pos = VisualPosition(x=0, y=0, width=3, height=1)
        layout = PageLayout(width=1280, height=720, grid_columns=12, grid_rows=8)
        result = grid_to_canvas(pos, layout, padding=0)
        assert result.x == 0
        assert result.y == 0
        cell_width = 1280 / 12
        assert result.width == round(3 * cell_width, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Visual Type Mapping
# ─────────────────────────────────────────────────────────────────────────────


class TestVisualTypeMapping:
    """Tests for visual type mapping."""

    def test_card_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.CARD, title="T")
        pbi_type, is_fallback, _ = map_visual_type(v)
        assert pbi_type == "card"
        assert not is_fallback

    def test_line_chart_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.LINE_CHART, title="T")
        pbi_type, is_fallback, _ = map_visual_type(v)
        assert pbi_type == "lineChart"
        assert not is_fallback

    def test_clustered_bar_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.CLUSTERED_BAR, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "clusteredBarChart"

    def test_clustered_column_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.CLUSTERED_COLUMN, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "clusteredColumnChart"

    def test_table_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.TABLE, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "tableEx"

    def test_slicer_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.SLICER, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "slicer"

    def test_map_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.MAP, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "map"

    def test_scatter_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.SCATTER, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "scatterChart"

    def test_donut_mapping(self):
        v = VisualSpec(id="x", visual_type=VisualType.DONUT_CHART, title="T")
        pbi_type, _, _ = map_visual_type(v)
        assert pbi_type == "donutChart"

    def test_kpi_fallback_to_card(self):
        v = VisualSpec(id="x", visual_type=VisualType.KPI, title="T")
        pbi_type, is_fallback, reason = map_visual_type(v)
        assert pbi_type == "card"
        assert is_fallback
        assert "KPI" in reason

    def test_all_enum_values_have_mapping(self):
        """Every VisualType enum should produce a valid type."""
        for vt in VisualType:
            v = VisualSpec(id="x", visual_type=vt, title="T")
            pbi_type, _, _ = map_visual_type(v)
            assert pbi_type is not None
            assert len(pbi_type) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Field Bindings
# ─────────────────────────────────────────────────────────────────────────────


class TestFieldBindings:
    """Tests for field reference building."""

    def test_column_field_ref(self):
        field = FieldRef(table="Date", column="MonthName")
        ref = build_field_ref(field)
        assert ref == {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "Date"}},
                "Property": "MonthName",
            }
        }

    def test_measure_field_ref(self):
        field = FieldRef(table="Sales", measure="TotalRevenue")
        ref = build_field_ref(field)
        assert ref == {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "Sales"}},
                "Property": "TotalRevenue",
            }
        }

    def test_query_ref_column(self):
        field = FieldRef(table="Date", column="Year")
        assert build_query_ref(field) == "Date.Year"

    def test_query_ref_measure(self):
        field = FieldRef(table="Sales", measure="TotalRevenue")
        assert build_query_ref(field) == "Sales.TotalRevenue"

    def test_card_query_state(self):
        visual = VisualSpec(
            id="x",
            visual_type=VisualType.CARD,
            title="T",
            value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
        )
        state = build_query_state(visual, "card")
        assert "Values" in state
        assert len(state["Values"]["projections"]) == 1
        proj = state["Values"]["projections"][0]
        assert proj["queryRef"] == "Sales.TotalRevenue"
        assert "Measure" in proj["field"]

    def test_line_query_state(self):
        visual = VisualSpec(
            id="x",
            visual_type=VisualType.LINE_CHART,
            title="T",
            category_fields=[FieldRef(table="Date", column="MonthName")],
            value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
        )
        state = build_query_state(visual, "lineChart")
        assert "Category" in state
        assert "Y" in state
        assert state["Category"]["projections"][0]["queryRef"] == "Date.MonthName"
        assert state["Y"]["projections"][0]["queryRef"] == "Sales.TotalRevenue"

    def test_slicer_query_state(self):
        visual = VisualSpec(
            id="x",
            visual_type=VisualType.SLICER,
            title="T",
            category_fields=[FieldRef(table="Region", column="RegionName")],
        )
        state = build_query_state(visual, "slicer")
        assert "Values" in state
        assert state["Values"]["projections"][0]["queryRef"] == "Region.RegionName"

    def test_scatter_query_state(self):
        visual = VisualSpec(
            id="x",
            visual_type=VisualType.SCATTER,
            title="T",
            category_fields=[FieldRef(table="Store", column="StoreName")],
            value_fields=[
                FieldRef(table="Sales", measure="TotalRevenue"),
                FieldRef(table="Sales", measure="GrossProfit"),
            ],
        )
        state = build_query_state(visual, "scatterChart")
        assert "Category" in state
        assert "X" in state
        assert "Y" in state

    def test_map_query_state(self):
        visual = VisualSpec(
            id="x",
            visual_type=VisualType.MAP,
            title="T",
            category_fields=[FieldRef(table="Region", column="RegionName")],
            value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
        )
        state = build_query_state(visual, "map")
        assert "Category" in state
        assert "Size" in state


# ─────────────────────────────────────────────────────────────────────────────
# 10. Filter/Slicer Rendering
# ─────────────────────────────────────────────────────────────────────────────


class TestFilterRendering:
    """Tests for filter/slicer visual generation."""

    def test_filter_rendered_as_slicer(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        # The filter should be rendered as a visual in the page directory
        visuals_dir = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition"
            / "pages"
            / "page-overview"
            / "visuals"
        )
        # Find the filter visual (filter-year ID)
        filter_dir = visuals_dir / "filter-year"
        assert filter_dir.is_dir()
        visual_json = json.loads((filter_dir / "visual.json").read_text(encoding="utf-8"))
        assert visual_json["visual"]["visualType"] == "slicer"

    def test_filter_has_query_state(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        filter_dir = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition"
            / "pages"
            / "page-overview"
            / "visuals"
            / "filter-year"
        )
        visual_json = json.loads((filter_dir / "visual.json").read_text(encoding="utf-8"))
        query_state = visual_json["visual"]["query"]["queryState"]
        assert "Values" in query_state
        proj = query_state["Values"]["projections"][0]
        assert proj["queryRef"] == "Date.Year"


# ─────────────────────────────────────────────────────────────────────────────
# 11. Theme Generation
# ─────────────────────────────────────────────────────────────────────────────


class TestThemeGeneration:
    """Tests for theme JSON generation."""

    def test_theme_has_name(self):
        theme = ThemeSpec(style_family="corporate_restrained")
        result = generate_theme(theme)
        assert "CustomTheme" in result["name"]

    def test_theme_has_data_colors(self):
        theme = ThemeSpec(style_family="corporate_restrained")
        result = generate_theme(theme)
        assert len(result["dataColors"]) == 5

    def test_theme_uses_explicit_colours(self):
        theme = ThemeSpec(
            colour_roles=[
                ColourRole(role="primary", hex_value="#FF0000"),
                ColourRole(role="accent", hex_value="#00FF00"),
            ],
        )
        result = generate_theme(theme)
        assert "#FF0000" in result["dataColors"]
        assert "#00FF00" in result["dataColors"]

    def test_light_mode_background(self):
        theme = ThemeSpec(presentation_mode=PresentationMode.LIGHT)
        result = generate_theme(theme)
        assert result["background"] == "#FFFFFF"

    def test_dark_mode_background(self):
        theme = ThemeSpec(presentation_mode=PresentationMode.DARK)
        result = generate_theme(theme)
        assert result["background"] == "#1F2937"

    def test_theme_text_classes(self):
        theme = ThemeSpec(
            typography=TypographySpec(
                heading_font="Arial",
                body_font="Verdana",
                base_size_pt=12.0,
            )
        )
        result = generate_theme(theme)
        assert result["textClasses"]["title"]["fontFace"] == "Arial"
        assert result["textClasses"]["label"]["fontFace"] == "Verdana"
        assert result["textClasses"]["title"]["fontSize"] == 16
        assert result["textClasses"]["label"]["fontSize"] == 12

    def test_theme_written_to_file(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        theme_path = (
            result.output_path
            / f"{result.project_name}.Report"
            / "StaticResources"
            / "RegisteredResources"
            / "theme.json"
        )
        data = json.loads(theme_path.read_text(encoding="utf-8"))
        assert "dataColors" in data
        assert "#007E33" in data["dataColors"]


# ─────────────────────────────────────────────────────────────────────────────
# 12. Unsupported Visual Fallback
# ─────────────────────────────────────────────────────────────────────────────


class TestUnsupportedVisualFallback:
    """Tests for fallback handling of unsupported visual types."""

    def test_kpi_falls_back_to_card(self):
        v = VisualSpec(id="x", visual_type=VisualType.KPI, title="T")
        pbi_type, is_fallback, reason = map_visual_type(v)
        assert pbi_type == "card"
        assert is_fallback

    def test_fallback_tracked_in_fidelity(self, tmp_dir):
        spec = DashboardSpec(
            intent=DashboardIntent(title="Test", business_purpose="T"),
            pages=[
                PageSpec(
                    id="p1",
                    title="P",
                    visuals=[
                        VisualSpec(
                            id="vis-kpi",
                            visual_type=VisualType.KPI,
                            title="KPI",
                            value_fields=[FieldRef(table="Sales", measure="TotalRevenue")],
                        ),
                    ],
                ),
            ],
            tables=[TableSpec(name="Sales", columns=[ColumnSpec(name="Revenue", data_type="REAL")])],
            measures=[MeasureSpec(name="TotalRevenue", expression="SUM(Sales[Revenue])", table="Sales")],
        )
        result = render_powerbi_project(spec, tmp_dir)
        assert result.success
        assert result.fidelity.fallback_visuals == 1
        detail = result.fidelity.visual_details[0]
        assert detail.is_fallback
        assert detail.rendered_type == "card"


# ─────────────────────────────────────────────────────────────────────────────
# 13. No Silent Visual Loss
# ─────────────────────────────────────────────────────────────────────────────


class TestNoSilentVisualLoss:
    """Tests ensuring all visuals are rendered without silent drops."""

    def test_all_visuals_rendered(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        assert result.fidelity.all_rendered
        # 3 visuals on page 1 + 1 on page 2 = 4
        assert result.fidelity.rendered_visuals == 4
        assert result.fidelity.total_visuals == 4

    def test_visual_count_matches_spec(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        expected = sum(len(p.visuals) for p in multi_page_spec.pages)
        assert result.fidelity.rendered_visuals == expected

    def test_visual_files_exist_on_disk(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        # Check all visual directories exist
        for page in multi_page_spec.pages:
            visuals_dir = (
                result.output_path
                / f"{result.project_name}.Report"
                / "definition"
                / "pages"
                / page.id
                / "visuals"
            )
            for visual in page.visuals:
                assert (visuals_dir / visual.id / "visual.json").is_file(), (
                    f"Missing visual file for {visual.id} on page {page.id}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 14. Output Structural Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestStructuralValidation:
    """Tests for the post-render structural validator."""

    def test_valid_project_passes(self, tmp_dir, multi_page_spec):
        result = render_powerbi_project(multi_page_spec, tmp_dir)
        assert result.success
        assert result.validation.passed

    def test_validation_checks_all_pass(self, tmp_dir, minimal_spec):
        result = render_powerbi_project(minimal_spec, tmp_dir)
        for check in result.validation.checks:
            assert check.passed, f"Failed check: {check.name} - {check.message}"

    def test_invalid_project_detected(self, tmp_dir):
        """Validate against a non-existent project."""
        fake_root = tmp_dir / "nonexistent"
        fake_root.mkdir()
        validation = validate_pbip_project(fake_root, "Fake")
        assert not validation.passed


# ─────────────────────────────────────────────────────────────────────────────
# 15. Deterministic Render
# ─────────────────────────────────────────────────────────────────────────────


class TestDeterministicRender:
    """Tests that same input produces structurally identical output."""

    def test_same_structure_twice(self, tmp_dir, minimal_spec):
        dir1 = tmp_dir / "run1"
        dir2 = tmp_dir / "run2"
        result1 = render_powerbi_project(minimal_spec, dir1)
        result2 = render_powerbi_project(minimal_spec, dir2)

        # Both succeed
        assert result1.success
        assert result2.success

        # Same project name
        assert result1.project_name == result2.project_name

        # Same fidelity counts
        assert result1.fidelity.rendered_visuals == result2.fidelity.rendered_visuals
        assert result1.fidelity.rendered_pages == result2.fidelity.rendered_pages

    def test_same_page_structure(self, tmp_dir, multi_page_spec):
        dir1 = tmp_dir / "run1"
        dir2 = tmp_dir / "run2"
        render_powerbi_project(multi_page_spec, dir1)
        render_powerbi_project(multi_page_spec, dir2)

        # Compare pages.json (deterministic content)
        name = "MultiPageDashboard"
        p1 = dir1 / name / f"{name}.Report" / "definition" / "pages" / "pages.json"
        p2 = dir2 / name / f"{name}.Report" / "definition" / "pages" / "pages.json"
        assert json.loads(p1.read_text()) == json.loads(p2.read_text())

    def test_same_visual_query_structure(self, tmp_dir, minimal_spec):
        dir1 = tmp_dir / "run1"
        dir2 = tmp_dir / "run2"
        render_powerbi_project(minimal_spec, dir1)
        render_powerbi_project(minimal_spec, dir2)

        name = "TestDashboard"
        v1 = (
            dir1 / name / f"{name}.Report" / "definition" / "pages"
            / "page-test" / "visuals" / "vis-test-card" / "visual.json"
        )
        v2 = (
            dir2 / name / f"{name}.Report" / "definition" / "pages"
            / "page-test" / "visuals" / "vis-test-card" / "visual.json"
        )
        data1 = json.loads(v1.read_text())
        data2 = json.loads(v2.read_text())
        # Query state should be identical
        assert data1["visual"]["query"] == data2["visual"]["query"]
        # Position should be identical
        assert data1["position"] == data2["position"]


# ─────────────────────────────────────────────────────────────────────────────
# 16. Full LIVE_OUTPUT.json Integration Render
# ─────────────────────────────────────────────────────────────────────────────


class TestLiveOutputIntegration:
    """Integration test using the actual LIVE_OUTPUT.json from Stage 02a."""

    @pytest.fixture
    def live_spec(self):
        """Load the live spec from LIVE_OUTPUT.json."""
        live_path = (
            Path(__file__).parent.parent
            / "docs"
            / "stages"
            / "02a-live-designer-test"
            / "LIVE_OUTPUT.json"
        )
        if not live_path.exists():
            pytest.skip("LIVE_OUTPUT.json not found")
        data = json.loads(live_path.read_text(encoding="utf-8"))
        return DashboardSpec.model_validate(data)

    def test_live_spec_renders_successfully(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        assert result.success, f"Render failed: {result.message}"

    def test_live_spec_all_pages_rendered(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        assert result.fidelity.rendered_pages == 4

    def test_live_spec_all_visuals_rendered(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        assert result.fidelity.all_rendered
        # Total visuals: 8 + 7 + 7 + 7 = 29
        assert result.fidelity.rendered_visuals == result.fidelity.total_visuals

    def test_live_spec_all_tables_have_tmdl(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        tables_dir = (
            result.output_path
            / f"{result.project_name}.SemanticModel"
            / "definition"
            / "tables"
        )
        expected_tables = {"Sales", "Date", "Store", "Region", "Product", "Risk"}
        actual_tables = {f.stem for f in tables_dir.glob("*.tmdl")}
        assert expected_tables == actual_tables

    def test_live_spec_measures_in_tmdl(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        sales_tmdl = (
            result.output_path
            / f"{result.project_name}.SemanticModel"
            / "definition"
            / "tables"
            / "Sales.tmdl"
        )
        content = sales_tmdl.read_text(encoding="utf-8")
        assert "TotalRevenue" in content
        assert "GrossMarginPct" in content
        assert "YoYGrowthPct" in content

    def test_live_spec_relationships_rendered(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        rel_file = (
            result.output_path
            / f"{result.project_name}.SemanticModel"
            / "definition"
            / "relationships.tmdl"
        )
        assert rel_file.is_file()
        content = rel_file.read_text(encoding="utf-8")
        # Should have 6 relationships (Risk.CategoryID→Product.CategoryID removed as invalid)
        assert content.count("relationship ") == 6

    def test_live_spec_validation_passes(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        assert result.validation.passed
        for check in result.validation.checks:
            assert check.passed, f"Failed: {check.name} - {check.message}"

    def test_live_spec_theme_has_corporate_style(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        theme_path = (
            result.output_path
            / f"{result.project_name}.Report"
            / "StaticResources"
            / "RegisteredResources"
            / "theme.json"
        )
        data = json.loads(theme_path.read_text(encoding="utf-8"))
        assert "corporate_restrained" in data["name"]
        assert len(data["dataColors"]) == 5

    def test_live_spec_pbir_references_model(self, tmp_dir, live_spec):
        result = render_powerbi_project(live_spec, tmp_dir)
        pbir = (
            result.output_path
            / f"{result.project_name}.Report"
            / "definition.pbir"
        )
        data = json.loads(pbir.read_text(encoding="utf-8"))
        ref_path = data["datasetReference"]["byPath"]["path"]
        assert ".SemanticModel" in ref_path


# ─────────────────────────────────────────────────────────────────────────────
# Edge Cases and Error Handling
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_pages_returns_invalid_spec(self, tmp_dir):
        spec = DashboardSpec(
            intent=DashboardIntent(title="Empty", business_purpose="T"),
            pages=[],
            tables=[TableSpec(name="T", columns=[ColumnSpec(name="C", data_type="TEXT")])],
        )
        result = render_powerbi_project(spec, tmp_dir)
        assert result.outcome == RenderOutcome.INVALID_SPEC

    def test_empty_tables_returns_invalid_spec(self, tmp_dir):
        spec = DashboardSpec(
            intent=DashboardIntent(title="Empty", business_purpose="T"),
            pages=[PageSpec(id="p", title="P", visuals=[
                VisualSpec(id="v", visual_type=VisualType.CARD, title="T",
                           value_fields=[FieldRef(table="S", measure="M")])
            ])],
            tables=[],
        )
        result = render_powerbi_project(spec, tmp_dir)
        assert result.outcome == RenderOutcome.INVALID_SPEC

    def test_visual_with_no_fields(self, tmp_dir):
        """A visual with no fields should still render (empty query)."""
        spec = DashboardSpec(
            intent=DashboardIntent(title="Test", business_purpose="T"),
            pages=[
                PageSpec(
                    id="p1",
                    title="P",
                    visuals=[
                        VisualSpec(id="v1", visual_type=VisualType.TEXT_BOX, title="Title"),
                    ],
                ),
            ],
            tables=[TableSpec(name="T", columns=[ColumnSpec(name="C", data_type="TEXT")])],
        )
        result = render_powerbi_project(spec, tmp_dir)
        assert result.success

    def test_special_characters_in_title(self, tmp_dir):
        """Special characters in the title should be sanitized."""
        spec = DashboardSpec(
            intent=DashboardIntent(
                title="Test: Dashboard (v2) / Final!",
                business_purpose="T",
            ),
            pages=[
                PageSpec(
                    id="p1",
                    title="P",
                    visuals=[
                        VisualSpec(
                            id="v1",
                            visual_type=VisualType.CARD,
                            title="T",
                            value_fields=[FieldRef(table="S", measure="M")],
                        ),
                    ],
                ),
            ],
            tables=[TableSpec(name="S", columns=[ColumnSpec(name="C", data_type="TEXT")])],
            measures=[MeasureSpec(name="M", expression="1", table="S")],
        )
        result = render_powerbi_project(spec, tmp_dir)
        assert result.success
        # Project name should not have special chars
        assert ":" not in result.project_name
        assert "/" not in result.project_name
