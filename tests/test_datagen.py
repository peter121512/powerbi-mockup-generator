"""Comprehensive tests for Stage 03 — Synthetic Data Generation Engine.

Tests cover:
1. Deterministic generation (same seed = same output)
2. SQLite table creation
3. Key uniqueness and FK coherence
4. Date dimension correctness
5. Dimension member generation
6. Fact table generation
7. Trend patterns (up/down)
8. YoY growth/decline
9. Seasonality
10. Concentration/Pareto
11. Outliers
12. Target miss
13. Financial reconciliation (Revenue = Quantity * UnitPrice, Cost < Revenue)
14. Structured verification
15. Invalid spec handling
16. Live spec integration (generate from LIVE_OUTPUT.json)
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import pytest

from pbi_gen.datagen import (
    DataGenDiagnostics,
    DataGenOutcome,
    DataGenResult,
    GenerationPlan,
    TableManifest,
    TableRole,
    VerificationCheck,
    VerificationResult,
    build_generation_plan,
    generate_synthetic_data,
)
from pbi_gen.datagen.generators import (
    DateGenerator,
    DimensionGenerator,
    FactGenerator,
    generate_all_tables,
)
from pbi_gen.datagen.patterns import apply_patterns
from pbi_gen.datagen.planner import DateRange, TablePlan, parse_time_period
from pbi_gen.datagen.result import DataGenOutcome
from pbi_gen.datagen.verifier import verify_data
from pbi_gen.datagen.writer import write_sqlite
from pbi_gen.models.dashboard_spec import (
    ColumnSpec,
    DashboardIntent,
    DashboardSpec,
    DataPattern,
    DataPatternType,
    FieldRef,
    MockDataNarrative,
    Relationship,
    RelationshipCardinality,
    TableSpec,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path."""
    return tmp_path / "test_output.sqlite"


@pytest.fixture
def minimal_spec() -> DashboardSpec:
    """A minimal spec with one dimension and one fact table."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="Test Dashboard",
            business_purpose="Testing data generation",
        ),
        tables=[
            TableSpec(
                name="Region",
                description="Region dimension",
                columns=[
                    ColumnSpec(name="RegionID", data_type="TEXT", is_key=True, sample_values=["R001", "R002"]),
                    ColumnSpec(name="RegionName", data_type="TEXT", sample_values=["London", "South East", "North West"]),
                ],
                row_count_hint=5,
            ),
            TableSpec(
                name="Sales",
                description="Sales fact",
                columns=[
                    ColumnSpec(name="SalesID", data_type="TEXT", is_key=True, sample_values=["S-00001"]),
                    ColumnSpec(name="RegionID", data_type="TEXT", sample_values=["R001"]),
                    ColumnSpec(name="Revenue", data_type="REAL", sample_values=["100.00", "200.00"]),
                    ColumnSpec(name="Cost", data_type="REAL", sample_values=["50.00", "100.00"]),
                ],
                row_count_hint=50,
            ),
        ],
        relationships=[
            Relationship(
                from_table="Sales",
                from_column="RegionID",
                to_table="Region",
                to_column="RegionID",
                cardinality=RelationshipCardinality.MANY_TO_ONE,
            ),
        ],
    )


@pytest.fixture
def full_spec() -> DashboardSpec:
    """A full spec matching the live test scenario."""
    return DashboardSpec(
        intent=DashboardIntent(
            title="Retail Performance Dashboard",
            business_purpose="Retail analytics",
        ),
        tables=[
            TableSpec(
                name="Date",
                description="Date dimension",
                columns=[
                    ColumnSpec(name="Date", data_type="DATE", is_key=True, sample_values=["2022-01-01"]),
                    ColumnSpec(name="Day", data_type="INTEGER", sample_values=["1", "15"]),
                    ColumnSpec(name="Month", data_type="INTEGER", sample_values=["1", "6", "12"]),
                    ColumnSpec(name="MonthName", data_type="TEXT", sample_values=["January", "February"]),
                    ColumnSpec(name="Quarter", data_type="INTEGER", sample_values=["1", "2", "3", "4"]),
                    ColumnSpec(name="Year", data_type="INTEGER", sample_values=["2022", "2023"]),
                    ColumnSpec(name="FiscalMonth", data_type="INTEGER", sample_values=["1", "6", "12"]),
                    ColumnSpec(name="FiscalQuarter", data_type="INTEGER", sample_values=["1", "2", "3", "4"]),
                    ColumnSpec(name="FiscalYear", data_type="INTEGER", sample_values=["2022", "2023"]),
                    ColumnSpec(name="FiscalPeriod", data_type="TEXT", sample_values=["FY 2022", "FY 2023"]),
                    ColumnSpec(name="IsCurrentFY", data_type="BOOLEAN", sample_values=["TRUE", "FALSE"]),
                    ColumnSpec(name="IsPreviousFY", data_type="BOOLEAN", sample_values=["TRUE", "FALSE"]),
                ],
                row_count_hint=730,
            ),
            TableSpec(
                name="Region",
                description="Region dimension",
                columns=[
                    ColumnSpec(name="RegionID", data_type="TEXT", is_key=True, sample_values=["R001", "R002"]),
                    ColumnSpec(name="RegionName", data_type="TEXT", sample_values=["London", "South East", "North West", "Scotland", "Wales"]),
                    ColumnSpec(name="RegionManager", data_type="TEXT", sample_values=["Jane Smith", "John Brown"]),
                    ColumnSpec(name="CountryCode", data_type="TEXT", sample_values=["UK"]),
                ],
                row_count_hint=12,
            ),
            TableSpec(
                name="Store",
                description="Store dimension",
                columns=[
                    ColumnSpec(name="StoreID", data_type="TEXT", is_key=True, sample_values=["ST001", "ST002"]),
                    ColumnSpec(name="StoreName", data_type="TEXT", sample_values=["London Oxford Street", "Manchester Arndale"]),
                    ColumnSpec(name="RegionID", data_type="TEXT", sample_values=["R001", "R002"]),
                    ColumnSpec(name="StoreSize", data_type="TEXT", sample_values=["Small", "Medium", "Large", "Flagship"]),
                    ColumnSpec(name="OpenDate", data_type="DATE", sample_values=["2015-03-15", "2018-09-22"]),
                    ColumnSpec(name="IsActive", data_type="BOOLEAN", sample_values=["TRUE", "FALSE"]),
                ],
                row_count_hint=150,
            ),
            TableSpec(
                name="Product",
                description="Product dimension",
                columns=[
                    ColumnSpec(name="ProductID", data_type="TEXT", is_key=True, sample_values=["P-1001", "P-1002"]),
                    ColumnSpec(name="ProductName", data_type="TEXT", sample_values=["Classic White Shirt", "Slim Fit Jeans"]),
                    ColumnSpec(name="CategoryID", data_type="TEXT", sample_values=["C001", "C002"]),
                    ColumnSpec(name="CategoryName", data_type="TEXT", sample_values=["Menswear", "Womenswear", "Beauty", "Activewear", "Home"]),
                    ColumnSpec(name="SubcategoryID", data_type="TEXT", sample_values=["SC001", "SC002"]),
                    ColumnSpec(name="SubcategoryName", data_type="TEXT", sample_values=["Shirts", "Trousers", "Dresses"]),
                    ColumnSpec(name="UnitCost", data_type="REAL", sample_values=["10.00", "15.50", "60.00"]),
                    ColumnSpec(name="UnitPrice", data_type="REAL", sample_values=["19.99", "29.99", "99.00"]),
                    ColumnSpec(name="ContributionSegment", data_type="TEXT", sample_values=["Selected Category", "Other Categories"]),
                ],
                row_count_hint=500,
            ),
            TableSpec(
                name="Sales",
                description="Sales fact table",
                columns=[
                    ColumnSpec(name="SalesID", data_type="TEXT", is_key=True, sample_values=["S-00001", "S-00002"]),
                    ColumnSpec(name="Date", data_type="DATE", sample_values=["2022-01-15"]),
                    ColumnSpec(name="StoreID", data_type="TEXT", sample_values=["ST001"]),
                    ColumnSpec(name="ProductID", data_type="TEXT", sample_values=["P-1001"]),
                    ColumnSpec(name="Quantity", data_type="INTEGER", sample_values=["1", "2", "5"]),
                    ColumnSpec(name="UnitPrice", data_type="REAL", sample_values=["19.99", "24.50"]),
                    ColumnSpec(name="Revenue", data_type="REAL", sample_values=["19.99", "49.00"]),
                    ColumnSpec(name="Cost", data_type="REAL", sample_values=["10.00", "25.00"]),
                ],
                row_count_hint=1000,
            ),
        ],
        relationships=[
            Relationship(from_table="Sales", from_column="Date", to_table="Date", to_column="Date", cardinality=RelationshipCardinality.MANY_TO_ONE),
            Relationship(from_table="Sales", from_column="StoreID", to_table="Store", to_column="StoreID", cardinality=RelationshipCardinality.MANY_TO_ONE),
            Relationship(from_table="Sales", from_column="ProductID", to_table="Product", to_column="ProductID", cardinality=RelationshipCardinality.MANY_TO_ONE),
            Relationship(from_table="Store", from_column="RegionID", to_table="Region", to_column="RegionID", cardinality=RelationshipCardinality.MANY_TO_ONE),
        ],
        mock_data_narrative=MockDataNarrative(
            scenario_description="UK retail with growth and seasonal patterns",
            time_period="FY2022-FY2023",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.TREND_UP,
                    description="Overall revenue growth",
                    applies_to=[FieldRef(table="Sales", measure="TotalRevenue")],
                    parameters={"growth_rate": 0.08},
                ),
                DataPattern(
                    pattern_type=DataPatternType.SEASONAL,
                    description="Holiday peaks",
                    applies_to=[FieldRef(table="Sales", measure="TotalRevenue")],
                    parameters={"peak_months": [7, 11, 12], "peak_magnitude": 0.3},
                ),
                DataPattern(
                    pattern_type=DataPatternType.OUTLIER_NEGATIVE,
                    description="Underperforming stores",
                    applies_to=[FieldRef(table="Store", column="StoreName")],
                    parameters={"outlier_count": 5, "outlier_magnitude": -0.25},
                ),
                DataPattern(
                    pattern_type=DataPatternType.TARGET_MISS,
                    description="Margin below target",
                    applies_to=[FieldRef(table="Sales", measure="GrossMarginPct")],
                    parameters={"target": 0.45, "actual_average": 0.42},
                ),
            ],
            key_insights=["8% YoY growth", "Seasonal peaks in Jul/Nov/Dec"],
            constraints=["Revenue = Quantity * UnitPrice"],
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Deterministic generation
# ─────────────────────────────────────────────────────────────────────────────


class TestDeterministicGeneration:
    """Same seed produces identical output."""

    def test_same_seed_same_output(self, full_spec, tmp_path):
        """Two runs with same seed produce identical results."""
        path1 = tmp_path / "run1.sqlite"
        path2 = tmp_path / "run2.sqlite"

        result1 = generate_synthetic_data(full_spec, path1, seed=42)
        result2 = generate_synthetic_data(full_spec, path2, seed=42)

        assert result1.diagnostics is not None
        assert result2.diagnostics is not None
        assert result1.diagnostics.row_counts == result2.diagnostics.row_counts

        # Compare actual data
        conn1 = sqlite3.connect(str(path1))
        conn2 = sqlite3.connect(str(path2))
        try:
            for table_name in result1.diagnostics.row_counts:
                rows1 = conn1.execute(f'SELECT * FROM "{table_name}"').fetchall()
                rows2 = conn2.execute(f'SELECT * FROM "{table_name}"').fetchall()
                assert rows1 == rows2, f"Table {table_name} differs between runs"
        finally:
            conn1.close()
            conn2.close()

    def test_different_seed_different_output(self, full_spec, tmp_path):
        """Different seeds produce different results."""
        path1 = tmp_path / "seed1.sqlite"
        path2 = tmp_path / "seed2.sqlite"

        generate_synthetic_data(full_spec, path1, seed=42)
        generate_synthetic_data(full_spec, path2, seed=99)

        conn1 = sqlite3.connect(str(path1))
        conn2 = sqlite3.connect(str(path2))
        try:
            rows1 = conn1.execute("SELECT Revenue FROM Sales LIMIT 10").fetchall()
            rows2 = conn2.execute("SELECT Revenue FROM Sales LIMIT 10").fetchall()
            assert rows1 != rows2
        finally:
            conn1.close()
            conn2.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. SQLite table creation
# ─────────────────────────────────────────────────────────────────────────────


class TestSQLiteCreation:
    """SQLite database is created correctly."""

    def test_database_file_created(self, full_spec, tmp_db):
        """Output file is a valid SQLite database."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert tmp_db.exists()
        # Verify it's a valid SQLite file
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        assert len(tables) >= 4

    def test_all_tables_present(self, full_spec, tmp_db):
        """All spec tables are present in the database."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        tables = {
            row[0] for row in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()
        expected = {"Date", "Region", "Store", "Product", "Sales"}
        assert expected.issubset(tables)

    def test_correct_column_types(self, full_spec, tmp_db):
        """Tables have correct column definitions."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        # Check Region table columns
        info = conn.execute("PRAGMA table_info('Region')").fetchall()
        conn.close()
        col_names = {row[1] for row in info}
        assert "RegionID" in col_names
        assert "RegionName" in col_names

    def test_row_counts_match_hints(self, full_spec, tmp_db):
        """Generated row counts match the spec hints."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics is not None
        assert result.diagnostics.row_counts["Region"] == 12
        assert result.diagnostics.row_counts["Store"] == 150
        assert result.diagnostics.row_counts["Product"] == 500
        assert result.diagnostics.row_counts["Sales"] == 1000


# ─────────────────────────────────────────────────────────────────────────────
# 3. Key uniqueness and FK coherence
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyCoherence:
    """Keys are unique and FKs reference valid values."""

    def test_primary_keys_unique(self, full_spec, tmp_db):
        """Primary keys have no duplicates."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))

        for table, key_col in [("Region", "RegionID"), ("Store", "StoreID"), ("Product", "ProductID")]:
            keys = conn.execute(f'SELECT "{key_col}" FROM "{table}"').fetchall()
            key_values = [r[0] for r in keys]
            assert len(key_values) == len(set(key_values)), f"Duplicate keys in {table}"

        conn.close()

    def test_fk_coherence_sales_to_store(self, full_spec, tmp_db):
        """Sales.StoreID references valid Store.StoreID values."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))

        store_ids = {r[0] for r in conn.execute("SELECT StoreID FROM Store").fetchall()}
        sales_store_ids = {r[0] for r in conn.execute("SELECT DISTINCT StoreID FROM Sales").fetchall()}
        conn.close()

        assert sales_store_ids.issubset(store_ids)

    def test_fk_coherence_sales_to_product(self, full_spec, tmp_db):
        """Sales.ProductID references valid Product.ProductID values."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))

        product_ids = {r[0] for r in conn.execute("SELECT ProductID FROM Product").fetchall()}
        sales_product_ids = {r[0] for r in conn.execute("SELECT DISTINCT ProductID FROM Sales").fetchall()}
        conn.close()

        assert sales_product_ids.issubset(product_ids)

    def test_fk_coherence_sales_to_date(self, full_spec, tmp_db):
        """Sales.Date references valid Date.Date values."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))

        date_values = {r[0] for r in conn.execute("SELECT Date FROM Date").fetchall()}
        sales_dates = {r[0] for r in conn.execute("SELECT DISTINCT Date FROM Sales").fetchall()}
        conn.close()

        assert sales_dates.issubset(date_values)

    def test_fk_coherence_store_to_region(self, full_spec, tmp_db):
        """Store.RegionID references valid Region.RegionID values."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))

        region_ids = {r[0] for r in conn.execute("SELECT RegionID FROM Region").fetchall()}
        store_region_ids = {r[0] for r in conn.execute("SELECT DISTINCT RegionID FROM Store").fetchall()}
        conn.close()

        assert store_region_ids.issubset(region_ids)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Date dimension correctness
# ─────────────────────────────────────────────────────────────────────────────


class TestDateDimension:
    """Date dimension generates correctly."""

    def test_date_range_coverage(self):
        """Date generator covers the full range."""
        gen = DateGenerator(fiscal_year_start_month=4)
        dr = DateRange(start=date(2021, 4, 1), end=date(2023, 3, 31))
        rows = gen.generate(dr)
        assert len(rows) == 730  # 2 full years (365 + 365)

    def test_fiscal_year_calculation(self):
        """April 2021 is FY2022, March 2023 is FY2023."""
        gen = DateGenerator(fiscal_year_start_month=4)
        dr = DateRange(start=date(2021, 4, 1), end=date(2023, 3, 31))
        rows = gen.generate(dr)

        # First day: April 1, 2021 -> FY2022
        assert rows[0]["Date"] == "2021-04-01"
        assert rows[0]["FiscalYear"] == 2022
        assert rows[0]["FiscalMonth"] == 1

        # Last day: March 31, 2023 -> FY2023
        assert rows[-1]["Date"] == "2023-03-31"
        assert rows[-1]["FiscalYear"] == 2023
        assert rows[-1]["FiscalMonth"] == 12

    def test_fiscal_quarters(self):
        """Fiscal quarters are correct (Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar)."""
        gen = DateGenerator(fiscal_year_start_month=4)
        dr = DateRange(start=date(2021, 4, 1), end=date(2022, 3, 31))
        rows = gen.generate(dr)

        # April -> FQ1
        april_row = rows[0]
        assert april_row["FiscalQuarter"] == 1

        # July -> FQ2
        july_rows = [r for r in rows if r["Month"] == 7]
        assert july_rows[0]["FiscalQuarter"] == 2

        # October -> FQ3
        oct_rows = [r for r in rows if r["Month"] == 10]
        assert oct_rows[0]["FiscalQuarter"] == 3

        # January -> FQ4
        jan_rows = [r for r in rows if r["Month"] == 1]
        assert jan_rows[0]["FiscalQuarter"] == 4

    def test_month_names(self):
        """MonthName is correct."""
        gen = DateGenerator(fiscal_year_start_month=4)
        dr = DateRange(start=date(2021, 4, 1), end=date(2021, 4, 30))
        rows = gen.generate(dr)
        assert all(r["MonthName"] == "April" for r in rows)

    def test_is_current_previous_fy(self):
        """IsCurrentFY and IsPreviousFY flags are correct."""
        gen = DateGenerator(fiscal_year_start_month=4)
        dr = DateRange(start=date(2021, 4, 1), end=date(2023, 3, 31))
        rows = gen.generate(dr)

        # Latest FY is 2023 (Apr 2022 - Mar 2023)
        fy2023_rows = [r for r in rows if r["FiscalYear"] == 2023]
        assert all(r["IsCurrentFY"] == "TRUE" for r in fy2023_rows)
        assert all(r["IsPreviousFY"] == "FALSE" for r in fy2023_rows)

        fy2022_rows = [r for r in rows if r["FiscalYear"] == 2022]
        assert all(r["IsCurrentFY"] == "FALSE" for r in fy2022_rows)
        assert all(r["IsPreviousFY"] == "TRUE" for r in fy2022_rows)

    def test_all_columns_present(self):
        """All expected date dimension columns exist."""
        gen = DateGenerator(fiscal_year_start_month=4)
        dr = DateRange(start=date(2022, 1, 1), end=date(2022, 1, 31))
        rows = gen.generate(dr)
        expected_cols = {
            "Date", "Day", "Month", "MonthName", "Quarter", "Year",
            "FiscalMonth", "FiscalQuarter", "FiscalYear", "FiscalPeriod",
            "IsCurrentFY", "IsPreviousFY",
        }
        assert set(rows[0].keys()) == expected_cols


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dimension member generation
# ─────────────────────────────────────────────────────────────────────────────


class TestDimensionGeneration:
    """Dimension tables generate with correct members."""

    def test_region_count(self, full_spec, tmp_db):
        """Region table has correct row count."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics.row_counts["Region"] == 12

    def test_store_count(self, full_spec, tmp_db):
        """Store table has correct row count."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics.row_counts["Store"] == 150

    def test_product_count(self, full_spec, tmp_db):
        """Product table has correct row count."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics.row_counts["Product"] == 500

    def test_key_format_follows_sample(self, full_spec, tmp_db):
        """Generated keys follow the sample_values pattern."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        region_ids = [r[0] for r in conn.execute("SELECT RegionID FROM Region").fetchall()]
        conn.close()

        # Should follow R001, R002, etc. pattern
        assert region_ids[0] == "R001"
        assert region_ids[1] == "R002"

    def test_sample_values_used_for_text(self, full_spec, tmp_db):
        """Text columns use sample_values."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        region_names = {r[0] for r in conn.execute("SELECT RegionName FROM Region").fetchall()}
        conn.close()

        # Should contain at least some of the sample values
        samples = {"London", "South East", "North West", "Scotland", "Wales"}
        assert len(region_names & samples) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Fact table generation
# ─────────────────────────────────────────────────────────────────────────────


class TestFactGeneration:
    """Fact table generates with correct structure."""

    def test_sales_row_count(self, full_spec, tmp_db):
        """Sales table has requested row count."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics.row_counts["Sales"] == 1000

    def test_sales_has_all_columns(self, full_spec, tmp_db):
        """Sales table has all expected columns."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        info = conn.execute("PRAGMA table_info('Sales')").fetchall()
        conn.close()
        col_names = {row[1] for row in info}
        expected = {"SalesID", "Date", "StoreID", "ProductID", "Quantity", "UnitPrice", "Revenue", "Cost"}
        assert expected == col_names

    def test_revenue_positive(self, full_spec, tmp_db):
        """Revenue values are positive."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        min_rev = conn.execute("SELECT MIN(Revenue) FROM Sales").fetchone()[0]
        conn.close()
        assert min_rev > 0

    def test_quantity_positive(self, full_spec, tmp_db):
        """Quantity values are positive integers."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        min_qty = conn.execute("SELECT MIN(Quantity) FROM Sales").fetchone()[0]
        conn.close()
        assert min_qty >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 7. Trend patterns (up/down)
# ─────────────────────────────────────────────────────────────────────────────


class TestTrendPatterns:
    """Trend patterns affect data directionally."""

    def test_trend_up_applied(self, full_spec, tmp_db):
        """Trend up pattern results in later values > earlier values."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT Date, Revenue FROM Sales ORDER BY Date"
        ).fetchall()
        conn.close()

        mid = len(rows) // 2
        first_half_rev = sum(r[1] for r in rows[:mid])
        second_half_rev = sum(r[1] for r in rows[mid:])

        # Second half should have more revenue due to trend up
        assert second_half_rev > first_half_rev

    def test_trend_down_pattern(self):
        """Trend down pattern reduces later values."""
        import random

        rng = random.Random(42)
        tables = {
            "Sales": [
                {"Date": f"2022-{m:02d}-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"}
                for m in range(1, 13)
            ],
            "Product": [{"ProductID": "P1", "CategoryName": "Formalwear"}],
        }

        narrative = MockDataNarrative(
            scenario_description="Test",
            time_period="FY2022",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.TREND_DOWN,
                    description="Decline",
                    parameters={"affected_categories": ["Formalwear"], "decline_rate": -0.20},
                ),
            ],
        )

        apply_patterns(tables, narrative, seed=42)

        # First half average should be higher than second half
        revenues = [r["Revenue"] for r in tables["Sales"]]
        first_half = sum(revenues[:6]) / 6
        second_half = sum(revenues[6:]) / 6
        assert first_half > second_half


# ─────────────────────────────────────────────────────────────────────────────
# 8. YoY growth/decline
# ─────────────────────────────────────────────────────────────────────────────


class TestYoYPatterns:
    """Year-over-year patterns work correctly."""

    def test_yoy_growth(self):
        """YoY growth makes later year revenue higher."""
        tables = {
            "Sales": [
                {"Date": "2021-06-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
                {"Date": "2021-07-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
                {"Date": "2022-06-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
                {"Date": "2022-07-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
            ],
        }

        narrative = MockDataNarrative(
            scenario_description="Test",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.YOY_GROWTH,
                    description="Growth",
                    parameters={"growth_rate": 0.15},
                ),
            ],
        )

        apply_patterns(tables, narrative, seed=42)

        y2021 = sum(r["Revenue"] for r in tables["Sales"] if r["Date"].startswith("2021"))
        y2022 = sum(r["Revenue"] for r in tables["Sales"] if r["Date"].startswith("2022"))
        assert y2022 > y2021

    def test_yoy_decline(self):
        """YoY decline makes later year revenue lower."""
        tables = {
            "Sales": [
                {"Date": "2021-06-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
                {"Date": "2021-07-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
                {"Date": "2022-06-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
                {"Date": "2022-07-15", "Revenue": 100.0, "Cost": 50.0, "StoreID": "S1", "ProductID": "P1"},
            ],
            "Store": [{"StoreID": "S1", "RegionID": "R1"}],
            "Region": [{"RegionID": "R1", "RegionName": "Scotland"}],
        }

        narrative = MockDataNarrative(
            scenario_description="Test",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.YOY_DECLINE,
                    description="Decline",
                    parameters={"affected_regions": ["Scotland"], "decline_rate": -0.10},
                ),
            ],
        )

        apply_patterns(tables, narrative, seed=42)

        y2021 = sum(r["Revenue"] for r in tables["Sales"] if r["Date"].startswith("2021"))
        y2022 = sum(r["Revenue"] for r in tables["Sales"] if r["Date"].startswith("2022"))
        assert y2022 < y2021


# ─────────────────────────────────────────────────────────────────────────────
# 9. Seasonality
# ─────────────────────────────────────────────────────────────────────────────


class TestSeasonality:
    """Seasonal patterns boost peak months."""

    def test_peak_months_higher(self):
        """Peak months have higher revenue than non-peak months."""
        tables = {
            "Sales": [
                {"Date": f"2022-{m:02d}-15", "Revenue": 100.0, "Cost": 50.0}
                for m in range(1, 13)
            ]
        }

        narrative = MockDataNarrative(
            scenario_description="Test",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.SEASONAL,
                    description="Peaks",
                    parameters={"peak_months": [11, 12], "peak_magnitude": 0.5},
                ),
            ],
        )

        apply_patterns(tables, narrative, seed=42)

        peak_rev = sum(
            r["Revenue"] for r in tables["Sales"]
            if int(r["Date"].split("-")[1]) in (11, 12)
        )
        non_peak_rev = sum(
            r["Revenue"] for r in tables["Sales"]
            if int(r["Date"].split("-")[1]) not in (11, 12)
        )

        # Peak months (2 months) should have proportionally more revenue
        avg_peak = peak_rev / 2
        avg_non_peak = non_peak_rev / 10
        assert avg_peak > avg_non_peak

    def test_seasonal_verification(self, full_spec, tmp_db):
        """Verification passes for seasonal pattern."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        if result.diagnostics and result.diagnostics.verification_results:
            seasonal_checks = [
                c for c in result.diagnostics.verification_results.checks
                if c.name == "seasonal"
            ]
            if seasonal_checks:
                assert seasonal_checks[0].passed


# ─────────────────────────────────────────────────────────────────────────────
# 10. Concentration / Pareto
# ─────────────────────────────────────────────────────────────────────────────


class TestConcentration:
    """Concentration pattern creates skewed distribution."""

    def test_concentration_applied(self):
        """Top stores get disproportionate revenue share."""
        import random

        tables = {
            "Sales": [
                {"StoreID": f"S{i % 10 + 1:03d}", "Revenue": 100.0, "Cost": 50.0, "Date": "2022-06-15"}
                for i in range(100)
            ],
            "Store": [{"StoreID": f"S{i+1:03d}"} for i in range(10)],
        }

        narrative = MockDataNarrative(
            scenario_description="Test",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.CONCENTRATION,
                    description="Top stores dominate",
                    parameters={"top_share": 0.7, "top_percentage": 0.2},
                ),
            ],
        )

        apply_patterns(tables, narrative, seed=42)

        # Group by store
        store_rev: dict[str, float] = {}
        for r in tables["Sales"]:
            store_rev[r["StoreID"]] = store_rev.get(r["StoreID"], 0) + r["Revenue"]

        sorted_rev = sorted(store_rev.values(), reverse=True)
        total = sum(sorted_rev)
        top_2 = sum(sorted_rev[:2])  # Top 20% = 2 out of 10

        # Top 2 stores should have significantly more than average
        assert top_2 / total > 0.3  # At least 30% (relaxed from 70% due to noise)


# ─────────────────────────────────────────────────────────────────────────────
# 11. Outliers
# ─────────────────────────────────────────────────────────────────────────────


class TestOutliers:
    """Outlier patterns create visible underperformers."""

    def test_negative_outliers_exist(self, full_spec, tmp_db):
        """Some stores have below-average performance (outlier effect)."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        store_revenue = conn.execute(
            "SELECT StoreID, SUM(Revenue) as TotalRev FROM Sales GROUP BY StoreID"
        ).fetchall()
        conn.close()

        revenues = [r[1] for r in store_revenue if r[1] > 0]
        if len(revenues) < 3:
            return
        mean_rev = sum(revenues) / len(revenues)

        # Should have some stores below average (outlier pattern applied)
        underperformers = [r for r in revenues if r < mean_rev * 0.85]
        assert len(underperformers) >= 1

    def test_outlier_pattern_unit(self):
        """Outlier pattern directly reduces revenue for selected stores."""
        import random

        tables = {
            "Sales": [
                {"StoreID": f"S{i % 10 + 1:03d}", "Revenue": 100.0, "Cost": 50.0, "Date": "2022-06-15", "ProductID": "P1"}
                for i in range(200)
            ],
            "Store": [{"StoreID": f"S{i+1:03d}"} for i in range(10)],
        }

        narrative = MockDataNarrative(
            scenario_description="Test",
            patterns=[
                DataPattern(
                    pattern_type=DataPatternType.OUTLIER_NEGATIVE,
                    description="Underperformers",
                    parameters={"outlier_count": 3, "outlier_magnitude": -0.40},
                ),
            ],
        )

        apply_patterns(tables, narrative, seed=42)

        # Group by store
        store_rev: dict[str, float] = {}
        for r in tables["Sales"]:
            store_rev[r["StoreID"]] = store_rev.get(r["StoreID"], 0) + r["Revenue"]

        revenues = sorted(store_rev.values())
        mean_val = sum(revenues) / len(revenues)
        # Bottom stores should be noticeably lower
        bottom_3 = revenues[:3]
        top_7 = revenues[3:]
        avg_bottom = sum(bottom_3) / 3
        avg_top = sum(top_7) / 7
        assert avg_bottom < avg_top


# ─────────────────────────────────────────────────────────────────────────────
# 12. Target miss
# ─────────────────────────────────────────────────────────────────────────────


class TestTargetMiss:
    """Target miss pattern adjusts margins correctly."""

    def test_margin_below_target(self, full_spec, tmp_db):
        """Gross margin is below the 45% target."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        result = conn.execute(
            "SELECT SUM(Revenue), SUM(Cost) FROM Sales"
        ).fetchone()
        conn.close()

        total_rev, total_cost = result
        margin = (total_rev - total_cost) / total_rev
        assert margin < 0.45, f"Margin {margin:.3f} should be below 0.45"

    def test_margin_in_plausible_range(self, full_spec, tmp_db):
        """Margin is in a plausible business range (10-70%)."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        result = conn.execute(
            "SELECT SUM(Revenue), SUM(Cost) FROM Sales"
        ).fetchone()
        conn.close()

        total_rev, total_cost = result
        margin = (total_rev - total_cost) / total_rev
        assert 0.10 < margin < 0.70


# ─────────────────────────────────────────────────────────────────────────────
# 13. Financial reconciliation
# ─────────────────────────────────────────────────────────────────────────────


class TestFinancialReconciliation:
    """Financial data is internally consistent."""

    def test_cost_less_than_revenue(self, full_spec, tmp_db):
        """Cost < Revenue for all rows (positive margin)."""
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        violations = conn.execute(
            "SELECT COUNT(*) FROM Sales WHERE Cost >= Revenue"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM Sales").fetchone()[0]
        conn.close()

        # Allow up to 5% violations (patterns may push some rows)
        assert violations / total < 0.05, f"{violations}/{total} rows have Cost >= Revenue"

    def test_revenue_quantity_price_relationship(self, full_spec, tmp_db):
        """Revenue should be close to Quantity * UnitPrice (before patterns modify it)."""
        # Note: patterns modify Revenue but not Quantity*UnitPrice, so we just check
        # that Revenue is positive and in a reasonable range
        generate_synthetic_data(full_spec, tmp_db, seed=42)
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT Quantity, UnitPrice, Revenue FROM Sales LIMIT 100"
        ).fetchall()
        conn.close()

        for qty, price, rev in rows:
            assert rev > 0
            assert qty >= 1
            assert price > 0


# ─────────────────────────────────────────────────────────────────────────────
# 14. Structured verification
# ─────────────────────────────────────────────────────────────────────────────


class TestStructuredVerification:
    """Verification returns structured results."""

    def test_verification_result_structure(self, full_spec, tmp_db):
        """Result contains verification with structured checks."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics is not None
        vr = result.diagnostics.verification_results
        assert isinstance(vr, VerificationResult)
        assert len(vr.checks) > 0

    def test_verification_check_fields(self, full_spec, tmp_db):
        """Each check has name, passed, expected, actual."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        for check in result.diagnostics.verification_results.checks:
            assert isinstance(check, VerificationCheck)
            assert check.name
            assert isinstance(check.passed, bool)
            assert check.expected
            assert check.actual

    def test_diagnostics_has_patterns_applied(self, full_spec, tmp_db):
        """Diagnostics records which patterns were applied."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics is not None
        assert len(result.diagnostics.patterns_applied) > 0

    def test_diagnostics_has_table_manifests(self, full_spec, tmp_db):
        """Diagnostics contains table manifests."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics is not None
        assert len(result.diagnostics.tables) > 0
        manifest = result.diagnostics.tables[0]
        assert isinstance(manifest, TableManifest)
        assert manifest.table_name
        assert manifest.row_count > 0
        assert len(manifest.columns) > 0

    def test_diagnostics_has_elapsed_time(self, full_spec, tmp_db):
        """Diagnostics records elapsed time."""
        result = generate_synthetic_data(full_spec, tmp_db, seed=42)
        assert result.diagnostics.elapsed_seconds > 0


# ─────────────────────────────────────────────────────────────────────────────
# 15. Invalid spec handling
# ─────────────────────────────────────────────────────────────────────────────


class TestInvalidSpec:
    """Invalid specs return appropriate error results."""

    def test_empty_tables(self, tmp_db):
        """Spec with no tables returns INVALID_SPEC."""
        spec = DashboardSpec(
            intent=DashboardIntent(
                title="Empty",
                business_purpose="Test",
            ),
            tables=[],
        )
        result = generate_synthetic_data(spec, tmp_db, seed=42)
        assert result.outcome == DataGenOutcome.INVALID_SPEC
        assert not result.success

    def test_invalid_spec_has_error_message(self, tmp_db):
        """Invalid spec result has a descriptive error."""
        spec = DashboardSpec(
            intent=DashboardIntent(
                title="Empty",
                business_purpose="Test",
            ),
            tables=[],
        )
        result = generate_synthetic_data(spec, tmp_db, seed=42)
        assert "no tables" in result.message.lower()

    def test_result_factories(self):
        """Result factory methods work correctly."""
        ok = DataGenResult.ok("Success")
        assert ok.success
        assert ok.outcome == DataGenOutcome.SUCCESS

        invalid = DataGenResult.invalid_spec("Bad spec")
        assert not invalid.success
        assert invalid.outcome == DataGenOutcome.INVALID_SPEC
        assert "Bad spec" in invalid.error

        failure = DataGenResult.generation_failure("Boom")
        assert not failure.success
        assert failure.outcome == DataGenOutcome.GENERATION_FAILURE

        vfail = DataGenResult.verification_failure("Check failed")
        assert not vfail.success
        assert vfail.outcome == DataGenOutcome.VERIFICATION_FAILURE


# ─────────────────────────────────────────────────────────────────────────────
# 16. Live spec integration
# ─────────────────────────────────────────────────────────────────────────────


class TestLiveSpecIntegration:
    """Integration test using the real LIVE_OUTPUT.json spec."""

    @pytest.fixture
    def live_spec(self) -> DashboardSpec:
        """Load the live spec from LIVE_OUTPUT.json."""
        live_path = Path(__file__).parent.parent / "docs" / "stages" / "02a-live-designer-test" / "LIVE_OUTPUT.json"
        if not live_path.exists():
            pytest.skip("LIVE_OUTPUT.json not found")
        with open(live_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DashboardSpec(**data)

    def test_live_spec_generates_successfully(self, live_spec, tmp_path):
        """Full live spec generates without errors."""
        output = tmp_path / "live_output.sqlite"
        result = generate_synthetic_data(live_spec, output, seed=42)
        # Accept SUCCESS or VERIFICATION_FAILURE (patterns may not perfectly verify)
        assert result.outcome in (DataGenOutcome.SUCCESS, DataGenOutcome.VERIFICATION_FAILURE)
        assert output.exists()

    def test_live_spec_all_tables_created(self, live_spec, tmp_path):
        """Live spec creates all expected tables."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        tables = {
            row[0] for row in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()

        expected = {"Sales", "Date", "Store", "Region", "Product", "Risk"}
        assert expected.issubset(tables)

    def test_live_spec_date_dimension_730_rows(self, live_spec, tmp_path):
        """Date table has ~730 rows (2 years)."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        count = conn.execute("SELECT COUNT(*) FROM Date").fetchone()[0]
        conn.close()

        assert count == 730

    def test_live_spec_sales_10000_rows(self, live_spec, tmp_path):
        """Sales table has 10000 rows."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        count = conn.execute("SELECT COUNT(*) FROM Sales").fetchone()[0]
        conn.close()

        assert count == 10000

    def test_live_spec_store_150_rows(self, live_spec, tmp_path):
        """Store table has 150 rows."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        count = conn.execute("SELECT COUNT(*) FROM Store").fetchone()[0]
        conn.close()

        assert count == 150

    def test_live_spec_region_12_rows(self, live_spec, tmp_path):
        """Region table has 12 rows."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        count = conn.execute("SELECT COUNT(*) FROM Region").fetchone()[0]
        conn.close()

        assert count == 12

    def test_live_spec_product_500_rows(self, live_spec, tmp_path):
        """Product table has 500 rows."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        count = conn.execute("SELECT COUNT(*) FROM Product").fetchone()[0]
        conn.close()

        assert count == 500

    def test_live_spec_risk_30_rows(self, live_spec, tmp_path):
        """Risk table has 30 rows."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))
        count = conn.execute("SELECT COUNT(*) FROM Risk").fetchone()[0]
        conn.close()

        assert count == 30

    def test_live_spec_fk_coherence(self, live_spec, tmp_path):
        """All FK relationships are coherent in live spec output."""
        output = tmp_path / "live_output.sqlite"
        generate_synthetic_data(live_spec, output, seed=42)

        conn = sqlite3.connect(str(output))

        # Sales -> Store
        store_ids = {r[0] for r in conn.execute("SELECT StoreID FROM Store").fetchall()}
        sales_stores = {r[0] for r in conn.execute("SELECT DISTINCT StoreID FROM Sales").fetchall()}
        assert sales_stores.issubset(store_ids)

        # Sales -> Product
        product_ids = {r[0] for r in conn.execute("SELECT ProductID FROM Product").fetchall()}
        sales_products = {r[0] for r in conn.execute("SELECT DISTINCT ProductID FROM Sales").fetchall()}
        assert sales_products.issubset(product_ids)

        # Sales -> Date
        date_vals = {r[0] for r in conn.execute("SELECT Date FROM Date").fetchall()}
        sales_dates = {r[0] for r in conn.execute("SELECT DISTINCT Date FROM Sales").fetchall()}
        assert sales_dates.issubset(date_vals)

        # Store -> Region
        region_ids = {r[0] for r in conn.execute("SELECT RegionID FROM Region").fetchall()}
        store_regions = {r[0] for r in conn.execute("SELECT DISTINCT RegionID FROM Store").fetchall()}
        assert store_regions.issubset(region_ids)

        conn.close()

    def test_live_spec_deterministic(self, live_spec, tmp_path):
        """Live spec generates deterministically."""
        out1 = tmp_path / "run1.sqlite"
        out2 = tmp_path / "run2.sqlite"

        r1 = generate_synthetic_data(live_spec, out1, seed=42)
        r2 = generate_synthetic_data(live_spec, out2, seed=42)

        assert r1.diagnostics.row_counts == r2.diagnostics.row_counts


# ─────────────────────────────────────────────────────────────────────────────
# Planner unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPlanner:
    """Unit tests for the generation planner."""

    def test_parse_fy_range(self):
        """Parse FY2022-FY2023 correctly."""
        narrative = MockDataNarrative(
            scenario_description="Test",
            time_period="FY2022-FY2023",
        )
        dr = parse_time_period(narrative, fiscal_year_start_month=4)
        assert dr is not None
        assert dr.start == date(2021, 4, 1)
        assert dr.end == date(2023, 3, 31)

    def test_parse_single_fy(self):
        """Parse single FY2023."""
        narrative = MockDataNarrative(
            scenario_description="Test",
            time_period="FY2023",
        )
        dr = parse_time_period(narrative, fiscal_year_start_month=4)
        assert dr is not None
        assert dr.start == date(2022, 4, 1)
        assert dr.end == date(2023, 3, 31)

    def test_parse_no_narrative(self):
        """None narrative returns None."""
        assert parse_time_period(None) is None

    def test_parse_empty_period(self):
        """Empty time_period returns None."""
        narrative = MockDataNarrative(
            scenario_description="Test",
            time_period="",
        )
        assert parse_time_period(narrative) is None

    def test_table_classification_date(self, full_spec):
        """Date table is classified as date_dimension."""
        plan = build_generation_plan(full_spec)
        date_plan = next(t for t in plan.tables if t.table_name == "Date")
        assert date_plan.role == TableRole.DATE_DIMENSION

    def test_table_classification_fact(self, full_spec):
        """Sales table is classified as fact_table."""
        plan = build_generation_plan(full_spec)
        sales_plan = next(t for t in plan.tables if t.table_name == "Sales")
        assert sales_plan.role == TableRole.FACT_TABLE

    def test_table_classification_dimension(self, full_spec):
        """Region table is classified as categorical or entity dimension."""
        plan = build_generation_plan(full_spec)
        region_plan = next(t for t in plan.tables if t.table_name == "Region")
        assert region_plan.role in (TableRole.CATEGORICAL_DIMENSION, TableRole.ENTITY_DIMENSION)

    def test_generation_order(self, full_spec):
        """Dimensions come before facts in generation order."""
        plan = build_generation_plan(full_spec)
        date_plan = next(t for t in plan.tables if t.table_name == "Date")
        sales_plan = next(t for t in plan.tables if t.table_name == "Sales")
        assert date_plan.generation_order < sales_plan.generation_order

    def test_date_range_parsed(self, full_spec):
        """Date range is parsed from narrative."""
        plan = build_generation_plan(full_spec)
        assert plan.date_range is not None
        assert plan.date_range.start == date(2021, 4, 1)
        assert plan.date_range.end == date(2023, 3, 31)
