"""Tests for Stage 05 data staging and deployment infrastructure.

Covers:
- CSV export from SQLite
- M expression generation (URL-based and inline)
- Inline data embedding with compression
- Deployment result model
- Partition sources integration with TMDL renderer
"""

from __future__ import annotations

import base64
import csv
import json
import sqlite3
import tempfile
import zlib
from pathlib import Path

import pytest

from pbi_gen.deploy.orchestrator import DeploymentOutcome, DeploymentResult
from pbi_gen.deploy.staging import (
    INLINE_ROW_THRESHOLD,
    export_to_csv,
    generate_inline_m_expression,
    generate_inline_m_from_db,
    generate_m_expression,
)
from pbi_gen.models import ColumnSpec, TableSpec
from pbi_gen.datagen import validate_key_integrity
from pbi_gen.datagen.planner import (
    ForeignKey,
    GenerationPlan,
    TablePlan,
    TableRole,
)
from pbi_gen.renderer.semantic_model import generate_table_tmdl


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a small SQLite database for testing."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create a Region table
    cursor.execute("""
        CREATE TABLE Region (
            RegionID TEXT PRIMARY KEY,
            RegionName TEXT,
            RegionManager TEXT,
            CountryCode TEXT
        )
    """)
    cursor.executemany(
        "INSERT INTO Region VALUES (?, ?, ?, ?)",
        [
            ("R001", "North East", "Alice Smith", "GB"),
            ("R002", "South West", "Bob Jones", "GB"),
            ("R003", "Midlands", "Carol White", "GB"),
        ],
    )

    # Create a Product table
    cursor.execute("""
        CREATE TABLE Product (
            ProductID TEXT PRIMARY KEY,
            ProductName TEXT,
            Category TEXT,
            UnitPrice REAL
        )
    """)
    cursor.executemany(
        "INSERT INTO Product VALUES (?, ?, ?, ?)",
        [
            ("P001", "Widget A", "Electronics", 29.99),
            ("P002", "Widget B", "Electronics", 49.99),
            ("P003", "Gadget C", "Accessories", 9.99),
        ],
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def large_db(tmp_path: Path) -> Path:
    """Create a SQLite database with >INLINE_ROW_THRESHOLD rows."""
    db_path = tmp_path / "large.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE Sales (
            SaleID TEXT PRIMARY KEY,
            Amount REAL,
            Quantity INTEGER
        )
    """)
    rows = [(f"S{i:05d}", float(i) * 1.5, i % 100) for i in range(INLINE_ROW_THRESHOLD + 100)]
    cursor.executemany("INSERT INTO Sales VALUES (?, ?, ?)", rows)

    conn.commit()
    conn.close()
    return db_path


# ─────────────────────────────────────────────────────────────────────────────
# CSV Export Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCsvExport:
    """Tests for export_to_csv function."""

    def test_exports_all_tables(self, tmp_db: Path, tmp_path: Path):
        """Each SQLite table gets its own CSV file."""
        output_dir = tmp_path / "csv_output"
        result = export_to_csv(tmp_db, output_dir)

        assert "Region" in result
        assert "Product" in result
        assert len(result) == 2

    def test_csv_files_exist(self, tmp_db: Path, tmp_path: Path):
        """Exported CSV files actually exist on disk."""
        output_dir = tmp_path / "csv_output"
        result = export_to_csv(tmp_db, output_dir)

        for table_name, csv_path in result.items():
            assert csv_path.exists(), f"CSV for {table_name} not found"
            assert csv_path.suffix == ".csv"

    def test_csv_has_headers(self, tmp_db: Path, tmp_path: Path):
        """CSV files contain correct column headers."""
        output_dir = tmp_path / "csv_output"
        result = export_to_csv(tmp_db, output_dir)

        with open(result["Region"], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert headers == ["RegionID", "RegionName", "RegionManager", "CountryCode"]

    def test_csv_has_correct_row_count(self, tmp_db: Path, tmp_path: Path):
        """CSV files contain all rows from the table."""
        output_dir = tmp_path / "csv_output"
        result = export_to_csv(tmp_db, output_dir)

        with open(result["Region"], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
        assert len(rows) == 3

    def test_csv_data_values(self, tmp_db: Path, tmp_path: Path):
        """CSV data contains correct values."""
        output_dir = tmp_path / "csv_output"
        result = export_to_csv(tmp_db, output_dir)

        with open(result["Product"], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

        # First row
        assert rows[0][0] == "P001"
        assert rows[0][1] == "Widget A"
        assert rows[0][2] == "Electronics"

    def test_creates_output_directory(self, tmp_db: Path, tmp_path: Path):
        """Output directory is created if it doesn't exist."""
        output_dir = tmp_path / "nested" / "dir" / "csv"
        result = export_to_csv(tmp_db, output_dir)

        assert output_dir.exists()
        assert len(result) > 0

    def test_no_absolute_paths_in_csv(self, tmp_db: Path, tmp_path: Path):
        """CSV filenames don't leak absolute paths into the content."""
        output_dir = tmp_path / "csv_output"
        result = export_to_csv(tmp_db, output_dir)

        for csv_path in result.values():
            content = csv_path.read_text(encoding="utf-8")
            # Should not contain any filesystem paths
            assert "C:\\" not in content
            assert "/home/" not in content
            assert "/Users/" not in content


# ─────────────────────────────────────────────────────────────────────────────
# M Expression (URL-based) Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestUrlMExpression:
    """Tests for generate_m_expression (URL-based)."""

    def test_contains_csv_url(self):
        """M expression references the provided URL."""
        url = "https://storage.blob.core.windows.net/data/Sales.csv"
        expr = generate_m_expression("Sales", url)
        assert url in expr

    def test_has_let_in_structure(self):
        """M expression follows let/in pattern."""
        expr = generate_m_expression("Sales", "https://example.com/data.csv")
        assert expr.startswith("let")
        assert "in\n" in expr

    def test_uses_csv_document(self):
        """M expression uses Csv.Document for parsing."""
        expr = generate_m_expression("Sales", "https://example.com/data.csv")
        assert "Csv.Document" in expr

    def test_uses_web_contents(self):
        """M expression uses Web.Contents for URL access."""
        expr = generate_m_expression("Sales", "https://example.com/data.csv")
        assert "Web.Contents" in expr

    def test_promotes_headers(self):
        """M expression promotes first row to headers."""
        expr = generate_m_expression("Sales", "https://example.com/data.csv")
        assert "PromoteHeaders" in expr

    def test_no_secrets_in_expression(self):
        """M expression doesn't contain auth tokens or secrets."""
        expr = generate_m_expression("Sales", "https://storage.blob.core.windows.net/data/Sales.csv")
        assert "Bearer" not in expr
        assert "token" not in expr.lower().replace("fromtext", "")
        assert "password" not in expr.lower()

    def test_no_absolute_paths(self):
        """M expression doesn't contain filesystem paths."""
        expr = generate_m_expression("Sales", "https://example.com/data.csv")
        assert "C:\\" not in expr
        assert "/home/" not in expr


# ─────────────────────────────────────────────────────────────────────────────
# Inline M Expression Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInlineMExpression:
    """Tests for generate_inline_m_expression (embedded data)."""

    def test_small_table_uses_table_from_rows(self, tmp_db: Path, tmp_path: Path):
        """Small tables use Table.FromRows for inline data."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr = generate_inline_m_expression("Region", csv_paths["Region"])
        assert "Table.FromRows" in expr

    def test_small_table_has_compressed_data(self, tmp_db: Path, tmp_path: Path):
        """Inline expression uses compressed base64 data."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr = generate_inline_m_expression("Region", csv_paths["Region"])
        assert "Binary.FromText" in expr
        assert "BinaryEncoding.Base64" in expr
        assert "Compression.Deflate" in expr

    def test_inline_has_type_table(self, tmp_db: Path, tmp_path: Path):
        """Inline expression declares column types."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr = generate_inline_m_expression("Region", csv_paths["Region"])
        assert "type table [" in expr
        assert "RegionID = text" in expr
        assert "RegionName = text" in expr

    def test_inline_data_is_decompressible(self, tmp_db: Path, tmp_path: Path):
        """The embedded base64 data can be decoded and decompressed."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr = generate_inline_m_expression("Region", csv_paths["Region"])

        # Extract the base64 string
        start = expr.index('Binary.FromText("') + len('Binary.FromText("')
        end = expr.index('", BinaryEncoding.Base64)')
        b64_data = expr[start:end]

        # Decode and decompress
        compressed = base64.b64decode(b64_data)
        # Add zlib header and checksum for decompression
        decompressed = zlib.decompress(compressed, -15)  # raw deflate
        data = json.loads(decompressed)

        # Should be a list of lists
        assert isinstance(data, list)
        assert len(data) == 3  # 3 regions
        assert data[0] == ["R001", "North East", "Alice Smith", "GB"]

    def test_inline_has_let_in_structure(self, tmp_db: Path, tmp_path: Path):
        """Inline expression follows let/in pattern."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr = generate_inline_m_expression("Region", csv_paths["Region"])
        assert expr.strip().startswith("let")
        assert "\nin\n" in expr

    def test_large_table_falls_back_to_csv(self, large_db: Path, tmp_path: Path):
        """Tables above threshold use Csv.Document fallback."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(large_db, output_dir)

        expr = generate_inline_m_expression("Sales", csv_paths["Sales"])
        assert "Csv.Document" in expr
        assert "Table.FromRows" not in expr

    def test_no_absolute_paths_in_inline(self, tmp_db: Path, tmp_path: Path):
        """Inline expression doesn't leak filesystem paths."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr = generate_inline_m_expression("Region", csv_paths["Region"])
        assert str(tmp_path) not in expr
        assert "C:\\" not in expr


# ─────────────────────────────────────────────────────────────────────────────
# Inline M from DB Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestInlineMFromDb:
    """Tests for generate_inline_m_from_db (direct from SQLite)."""

    def test_generates_from_db_directly(self, tmp_db: Path):
        """Can generate inline M without intermediate CSV."""
        expr = generate_inline_m_from_db("Region", tmp_db)
        assert "Table.FromRows" in expr
        assert "Binary.FromText" in expr

    def test_data_matches_csv_approach(self, tmp_db: Path, tmp_path: Path):
        """DB-direct and CSV approaches produce equivalent data."""
        output_dir = tmp_path / "csv_output"
        csv_paths = export_to_csv(tmp_db, output_dir)

        expr_csv = generate_inline_m_expression("Region", csv_paths["Region"])
        expr_db = generate_inline_m_from_db("Region", tmp_db)

        # Both should have Table.FromRows
        assert "Table.FromRows" in expr_csv
        assert "Table.FromRows" in expr_db

        # Extract and compare the actual data
        def _extract_data(expr: str) -> list:
            start = expr.index('Binary.FromText("') + len('Binary.FromText("')
            end = expr.index('", BinaryEncoding.Base64)')
            b64_data = expr[start:end]
            compressed = base64.b64decode(b64_data)
            decompressed = zlib.decompress(compressed, -15)
            return json.loads(decompressed)

        data_csv = _extract_data(expr_csv)
        data_db = _extract_data(expr_db)
        assert data_csv == data_db

    def test_large_table_falls_back(self, large_db: Path):
        """Large tables use Csv.Document fallback from DB too."""
        expr = generate_inline_m_from_db("Sales", large_db)
        assert "Csv.Document" in expr
        assert "Table.FromRows" not in expr

    def test_no_db_path_in_expression(self, tmp_db: Path):
        """The database path doesn't appear in the M expression."""
        expr = generate_inline_m_from_db("Region", tmp_db)
        assert str(tmp_db) not in expr
        assert str(tmp_db.parent) not in expr

    def test_typed_columns_with_table_spec(self, tmp_db: Path):
        """When table_spec is provided, M types are used instead of all-text."""
        table_spec = TableSpec(
            name="Product",
            columns=[
                ColumnSpec(name="ProductID", data_type="TEXT", is_key=True),
                ColumnSpec(name="ProductName", data_type="TEXT"),
                ColumnSpec(name="Category", data_type="TEXT"),
                ColumnSpec(name="UnitPrice", data_type="REAL"),
            ],
        )

        expr = generate_inline_m_from_db("Product", tmp_db, table_spec=table_spec)

        # Should use proper M types
        assert "ProductID = text" in expr
        assert "ProductName = text" in expr
        assert "Category = text" in expr
        assert "UnitPrice = number" in expr

    def test_date_column_uses_date_type(self, tmp_path: Path):
        """Date columns get explicit conversion step when table_spec is provided."""
        db_path = tmp_path / "date_test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE Date (
                Date TEXT PRIMARY KEY,
                Year INTEGER,
                Month INTEGER,
                IsCurrentFY TEXT
            )
        """)
        cursor.executemany(
            "INSERT INTO Date VALUES (?, ?, ?, ?)",
            [
                ("2023-01-01", 2023, 1, "TRUE"),
                ("2023-01-02", 2023, 1, "FALSE"),
            ],
        )
        conn.commit()
        conn.close()

        table_spec = TableSpec(
            name="Date",
            columns=[
                ColumnSpec(name="Date", data_type="DATE", is_key=True),
                ColumnSpec(name="Year", data_type="INTEGER"),
                ColumnSpec(name="Month", data_type="INTEGER"),
                ColumnSpec(name="IsCurrentFY", data_type="BOOLEAN"),
            ],
        )

        expr = generate_inline_m_from_db("Date", db_path, table_spec=table_spec)

        # Date stays as text in type table (Table.FromRows can't parse dates from JSON text)
        assert "Date = text" in expr
        assert "Year = Int64.Type" in expr
        assert "Month = Int64.Type" in expr
        assert "IsCurrentFY = logical" in expr
        # Conversion step added for date columns
        assert "Table.TransformColumnTypes" in expr
        assert "type date" in expr
        # The result step should be "Converted Types"
        assert '#"Converted Types"' in expr

    def test_without_table_spec_uses_all_text(self, tmp_db: Path):
        """Without table_spec, all columns default to text type (backward compat)."""
        expr = generate_inline_m_from_db("Region", tmp_db)

        assert "RegionID = text" in expr
        assert "RegionName = text" in expr
        assert "RegionManager = text" in expr
        assert "CountryCode = text" in expr


# ─────────────────────────────────────────────────────────────────────────────
# Deployment Result Model Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeploymentResult:
    """Tests for the DeploymentResult dataclass."""

    def test_all_outcome_types_exist(self):
        """All expected outcome types are defined."""
        expected = {
            "SUCCESS",
            "AUTH_FAILURE",
            "WORKSPACE_FAILURE",
            "SEMANTIC_MODEL_FAILURE",
            "REPORT_FAILURE",
            "DATA_STAGING_FAILURE",
            "REFRESH_FAILURE",
        }
        actual = {o.name for o in DeploymentOutcome}
        assert actual == expected

    def test_success_property(self):
        """success property is True only for SUCCESS outcome."""
        result = DeploymentResult(
            outcome=DeploymentOutcome.SUCCESS,
            message="OK",
        )
        assert result.success is True

    def test_failure_property(self):
        """success property is False for non-SUCCESS outcomes."""
        for outcome in DeploymentOutcome:
            if outcome == DeploymentOutcome.SUCCESS:
                continue
            result = DeploymentResult(outcome=outcome, message="fail")
            assert result.success is False, f"{outcome.name} should not be success"

    def test_default_values(self):
        """Default fields are empty/zero."""
        result = DeploymentResult(
            outcome=DeploymentOutcome.SUCCESS,
            message="test",
        )
        assert result.workspace_id == ""
        assert result.semantic_model_name == ""
        assert result.report_name == ""
        assert result.refresh_status == ""
        assert result.elapsed_seconds == 0.0
        assert result.warnings == []

    def test_warnings_list(self):
        """Warnings can be populated."""
        result = DeploymentResult(
            outcome=DeploymentOutcome.SUCCESS,
            message="done",
            warnings=["partial render", "slow refresh"],
        )
        assert len(result.warnings) == 2
        assert "partial render" in result.warnings

    def test_distinguishes_auth_from_workspace(self):
        """Auth and workspace failures have distinct outcomes."""
        auth = DeploymentResult(outcome=DeploymentOutcome.AUTH_FAILURE, message="401")
        ws = DeploymentResult(outcome=DeploymentOutcome.WORKSPACE_FAILURE, message="404")
        assert auth.outcome != ws.outcome

    def test_distinguishes_staging_from_refresh(self):
        """Data staging and refresh failures have distinct outcomes."""
        staging = DeploymentResult(outcome=DeploymentOutcome.DATA_STAGING_FAILURE, message="err")
        refresh = DeploymentResult(outcome=DeploymentOutcome.REFRESH_FAILURE, message="err")
        assert staging.outcome != refresh.outcome


# ─────────────────────────────────────────────────────────────────────────────
# Partition Sources Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPartitionSourcesIntegration:
    """Tests that partition_sources properly integrates with the TMDL renderer."""

    def test_tmdl_uses_custom_m_expression(self):
        """When partition_sources is provided, TMDL contains the custom M expression."""
        table = TableSpec(
            name="Region",
            columns=[
                ColumnSpec(name="RegionID", data_type="TEXT", is_key=True),
                ColumnSpec(name="RegionName", data_type="TEXT"),
            ],
        )
        custom_m = (
            'let\n'
            '    Source = Table.FromRows(Json.Document("[[1,2]]"), type table [A = text, B = text])\n'
            'in\n'
            '    Source'
        )
        partition_sources = {"Region": custom_m}

        tmdl = generate_table_tmdl(table, measures=None, partition_sources=partition_sources)

        assert "Table.FromRows" in tmdl
        assert 'data/Region.csv' not in tmdl

    def test_tmdl_uses_placeholder_without_sources(self):
        """Without partition_sources, TMDL uses the default placeholder."""
        table = TableSpec(
            name="Sales",
            columns=[
                ColumnSpec(name="SaleID", data_type="TEXT", is_key=True),
                ColumnSpec(name="Amount", data_type="REAL"),
            ],
        )

        tmdl = generate_table_tmdl(table, measures=None, partition_sources=None)

        assert "data/Sales.csv" in tmdl

    def test_tmdl_mixed_sources(self):
        """Tables not in partition_sources still get the placeholder."""
        table_a = TableSpec(
            name="Region",
            columns=[ColumnSpec(name="RegionID", data_type="TEXT", is_key=True)],
        )
        table_b = TableSpec(
            name="Product",
            columns=[ColumnSpec(name="ProductID", data_type="TEXT", is_key=True)],
        )

        partition_sources = {"Region": "let Source = #table({},{}) in Source"}

        tmdl_a = generate_table_tmdl(table_a, measures=None, partition_sources=partition_sources)
        tmdl_b = generate_table_tmdl(table_b, measures=None, partition_sources=partition_sources)

        assert "#table" in tmdl_a
        assert "data/Region.csv" not in tmdl_a
        assert "data/Product.csv" in tmdl_b

    def test_inline_m_integrates_with_tmdl(self, tmp_db: Path):
        """End-to-end: generate inline M from DB and verify it appears in TMDL."""
        m_expr = generate_inline_m_from_db("Region", tmp_db)

        table = TableSpec(
            name="Region",
            columns=[
                ColumnSpec(name="RegionID", data_type="TEXT", is_key=True),
                ColumnSpec(name="RegionName", data_type="TEXT"),
                ColumnSpec(name="RegionManager", data_type="TEXT"),
                ColumnSpec(name="CountryCode", data_type="TEXT"),
            ],
        )
        partition_sources = {"Region": m_expr}

        tmdl = generate_table_tmdl(table, measures=None, partition_sources=partition_sources)

        # Should contain the inline data approach
        assert "Table.FromRows" in tmdl
        assert "Binary.Decompress" in tmdl
        assert "Binary.FromText" in tmdl
        # Should NOT contain the placeholder
        assert "data/Region.csv" not in tmdl

    def test_partition_has_import_mode(self, tmp_db: Path):
        """TMDL partition always specifies import mode."""
        m_expr = generate_inline_m_from_db("Region", tmp_db)

        table = TableSpec(
            name="Region",
            columns=[ColumnSpec(name="RegionID", data_type="TEXT", is_key=True)],
        )
        partition_sources = {"Region": m_expr}

        tmdl = generate_table_tmdl(table, measures=None, partition_sources=partition_sources)
        assert "mode: import" in tmdl



# ─────────────────────────────────────────────────────────────────────────────
# Key Integrity Validation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyIntegrityValidation:
    """Tests for validate_key_integrity function."""

    def test_valid_data_passes(self):
        """Clean data with valid PKs and FKs passes validation."""
        plan = GenerationPlan(tables=[
            TablePlan(
                table_name="Region",
                role=TableRole.CATEGORICAL_DIMENSION,
                row_count=3,
                columns=[
                    ColumnSpec(name="RegionID", data_type="TEXT", is_key=True),
                    ColumnSpec(name="RegionName", data_type="TEXT"),
                ],
                key_columns=["RegionID"],
            ),
        ])
        tables = {
            "Region": [
                {"RegionID": "R001", "RegionName": "North"},
                {"RegionID": "R002", "RegionName": "South"},
                {"RegionID": "R003", "RegionName": "East"},
            ],
        }

        errors = validate_key_integrity(tables, plan)
        assert errors == []

    def test_null_pk_detected(self):
        """NULL values in primary key columns are detected."""
        plan = GenerationPlan(tables=[
            TablePlan(
                table_name="Date",
                role=TableRole.DATE_DIMENSION,
                row_count=3,
                columns=[
                    ColumnSpec(name="Date", data_type="DATE", is_key=True),
                    ColumnSpec(name="Year", data_type="INTEGER"),
                ],
                key_columns=["Date"],
            ),
        ])
        tables = {
            "Date": [
                {"Date": "2023-01-01", "Year": 2023},
                {"Date": None, "Year": 2023},
                {"Date": "2023-01-03", "Year": 2023},
            ],
        }

        errors = validate_key_integrity(tables, plan)
        assert len(errors) == 1
        assert "Date.Date (PK)" in errors[0]
        assert "NULL/empty" in errors[0]

    def test_empty_string_pk_detected(self):
        """Empty string values in primary key columns are detected."""
        plan = GenerationPlan(tables=[
            TablePlan(
                table_name="Date",
                role=TableRole.DATE_DIMENSION,
                row_count=3,
                columns=[
                    ColumnSpec(name="Date", data_type="DATE", is_key=True),
                ],
                key_columns=["Date"],
            ),
        ])
        tables = {
            "Date": [
                {"Date": "2023-01-01"},
                {"Date": ""},
                {"Date": "2023-01-03"},
            ],
        }

        errors = validate_key_integrity(tables, plan)
        assert len(errors) == 1
        assert "Date.Date (PK)" in errors[0]

    def test_duplicate_pk_detected(self):
        """Duplicate primary key values are detected."""
        plan = GenerationPlan(tables=[
            TablePlan(
                table_name="Region",
                role=TableRole.CATEGORICAL_DIMENSION,
                row_count=3,
                columns=[
                    ColumnSpec(name="RegionID", data_type="TEXT", is_key=True),
                ],
                key_columns=["RegionID"],
            ),
        ])
        tables = {
            "Region": [
                {"RegionID": "R001"},
                {"RegionID": "R001"},
                {"RegionID": "R003"},
            ],
        }

        errors = validate_key_integrity(tables, plan)
        assert len(errors) == 1
        assert "duplicate" in errors[0]

    def test_null_fk_detected(self):
        """NULL values in foreign key columns are detected."""
        plan = GenerationPlan(tables=[
            TablePlan(
                table_name="Sales",
                role=TableRole.FACT_TABLE,
                row_count=3,
                columns=[
                    ColumnSpec(name="SalesID", data_type="TEXT", is_key=True),
                    ColumnSpec(name="Date", data_type="DATE"),
                ],
                key_columns=["SalesID"],
                foreign_keys=[
                    ForeignKey(
                        from_table="Sales",
                        from_column="Date",
                        to_table="Date",
                        to_column="Date",
                    ),
                ],
            ),
        ])
        tables = {
            "Sales": [
                {"SalesID": "S001", "Date": "2023-01-01"},
                {"SalesID": "S002", "Date": None},
                {"SalesID": "S003", "Date": ""},
            ],
        }

        errors = validate_key_integrity(tables, plan)
        assert len(errors) == 1
        assert "FK" in errors[0]
        assert "2 NULL/empty" in errors[0]

    def test_live_spec_data_passes_validation(self):
        """Generated data from the live spec passes key integrity checks."""
        import json
        from pathlib import Path
        from pbi_gen.datagen import generate_synthetic_data
        from pbi_gen.models.dashboard_spec import DashboardSpec

        spec_path = Path(__file__).parent.parent / "docs" / "stages" / "02a-live-designer-test" / "LIVE_OUTPUT.json"
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = DashboardSpec.model_validate(json.load(f))

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            result = generate_synthetic_data(spec, output_path=db_path, seed=42)
            assert result.success, f"Data generation failed: {result.error}"
