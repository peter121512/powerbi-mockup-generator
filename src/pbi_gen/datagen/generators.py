"""Table data generators for synthetic data generation.

Provides generators for date dimensions, entity/categorical dimensions,
and fact tables. All generators use seeded random for reproducibility.
"""

from __future__ import annotations

import calendar
import random
from datetime import date, timedelta
from typing import Any

from pbi_gen.datagen.planner import (
    DateRange,
    ForeignKey,
    GenerationPlan,
    TablePlan,
    TableRole,
)
from pbi_gen.models.dashboard_spec import ColumnSpec


class DateGenerator:
    """Generates a complete date dimension table.

    Produces daily rows with calendar and fiscal year attributes.
    UK fiscal year (April-March) is the default.
    """

    def __init__(self, fiscal_year_start_month: int = 4):
        self.fiscal_year_start_month = fiscal_year_start_month

    def generate(self, date_range: DateRange) -> list[dict[str, Any]]:
        """Generate date dimension rows for every day in the range."""
        rows: list[dict[str, Any]] = []
        current = date_range.start
        end = date_range.end

        # Determine the "latest" fiscal year for IsCurrentFY/IsPreviousFY
        latest_fy = self._get_fiscal_year(end)

        while current <= end:
            fy = self._get_fiscal_year(current)
            fm = self._get_fiscal_month(current)
            fq = self._get_fiscal_quarter(fm)

            row = {
                "Date": current.isoformat(),
                "Day": current.day,
                "Month": current.month,
                "MonthName": calendar.month_name[current.month],
                "Quarter": (current.month - 1) // 3 + 1,
                "Year": current.year,
                "FiscalMonth": fm,
                "FiscalQuarter": fq,
                "FiscalYear": fy,
                "FiscalPeriod": f"FY {fy}",
                "IsCurrentFY": str(fy == latest_fy).upper(),
                "IsPreviousFY": str(fy == latest_fy - 1).upper(),
            }
            rows.append(row)
            current += timedelta(days=1)

        return rows

    def _get_fiscal_year(self, d: date) -> int:
        """UK fiscal year: if month >= start month, FY = year + 1, else FY = year."""
        if d.month >= self.fiscal_year_start_month:
            return d.year + 1
        return d.year

    def _get_fiscal_month(self, d: date) -> int:
        """Fiscal month: April=1, May=2, ..., March=12."""
        month_offset = d.month - self.fiscal_year_start_month
        if month_offset < 0:
            month_offset += 12
        return month_offset + 1

    def _get_fiscal_quarter(self, fiscal_month: int) -> int:
        """Fiscal quarter from fiscal month."""
        return (fiscal_month - 1) // 3 + 1


class DimensionGenerator:
    """Generates dimension table data using sample_values and column specs."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def generate(
        self,
        plan: TablePlan,
        generated_tables: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Generate dimension rows with unique keys and realistic values."""
        rows: list[dict[str, Any]] = []
        row_count = plan.row_count

        # Pre-resolve FK values
        fk_values: dict[str, list[Any]] = {}
        for fk in plan.foreign_keys:
            if fk.to_table in generated_tables:
                table_data = generated_tables[fk.to_table]
                if fk.target_is_key:
                    values = list({row[fk.to_column] for row in table_data if fk.to_column in row})
                else:
                    # FK points to a non-key column - get unique values
                    values = list({row[fk.to_column] for row in table_data if fk.to_column in row})
                fk_values[fk.from_column] = values

        for i in range(row_count):
            row: dict[str, Any] = {}
            for col in plan.columns:
                if col.is_key:
                    row[col.name] = self._generate_key(col, i, plan.table_name)
                elif col.name in fk_values:
                    # Assign FK value
                    available = fk_values[col.name]
                    if available:
                        row[col.name] = self.rng.choice(available)
                    else:
                        row[col.name] = self._generate_value(col, i)
                else:
                    row[col.name] = self._generate_value(col, i)
            rows.append(row)

        return rows

    def _generate_key(self, col: ColumnSpec, index: int, table_name: str) -> Any:
        """Generate a unique key value."""
        # Use sample_values pattern if available
        if col.sample_values:
            sample = col.sample_values[0]
            # Try to detect pattern like "ST001", "P-1001", "R001"
            import re
            match = re.match(r"^([A-Za-z-]+)(\d+)$", sample)
            if match:
                prefix = match.group(1)
                num_len = len(match.group(2))
                return f"{prefix}{str(index + 1).zfill(num_len)}"

        # Fallback: table initial + zero-padded index
        prefix = table_name[0].upper()
        return f"{prefix}{str(index + 1).zfill(4)}"

    def _generate_value(self, col: ColumnSpec, index: int) -> Any:
        """Generate a value for a non-key column."""
        dtype = col.data_type.upper()

        if col.sample_values:
            if dtype in ("INTEGER", "INT"):
                # Parse numeric sample values
                try:
                    numeric_samples = [int(s) for s in col.sample_values]
                    return self.rng.choice(numeric_samples)
                except ValueError:
                    pass
            elif dtype in ("REAL", "FLOAT", "DECIMAL"):
                try:
                    numeric_samples = [float(s) for s in col.sample_values]
                    low = min(numeric_samples)
                    high = max(numeric_samples)
                    return round(self.rng.uniform(low, high), 2)
                except ValueError:
                    pass
            elif dtype == "BOOLEAN":
                return self.rng.choice(col.sample_values)
            elif dtype in ("DATE", "DATETIME"):
                return self.rng.choice(col.sample_values)
            else:
                # TEXT - cycle through sample values with variation
                if len(col.sample_values) >= plan_row_count_threshold(col):
                    return col.sample_values[index % len(col.sample_values)]
                else:
                    return self.rng.choice(col.sample_values)

        # No sample values - generate by type
        if dtype in ("INTEGER", "INT"):
            return self.rng.randint(1, 100)
        elif dtype in ("REAL", "FLOAT", "DECIMAL"):
            return round(self.rng.uniform(1.0, 100.0), 2)
        elif dtype == "BOOLEAN":
            return self.rng.choice(["TRUE", "FALSE"])
        elif dtype in ("DATE", "DATETIME"):
            return "2022-06-15"
        else:
            return f"{col.name}_{index + 1}"


def plan_row_count_threshold(col: ColumnSpec) -> int:
    """Threshold for cycling vs random sampling of sample values."""
    return 3


class FactGenerator:
    """Generates fact table rows with valid FK references and realistic measures."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def generate(
        self,
        plan: TablePlan,
        generated_tables: dict[str, list[dict[str, Any]]],
        date_range: DateRange | None = None,
    ) -> list[dict[str, Any]]:
        """Generate fact rows referencing valid dimension keys.

        For sales-type facts, generates at date × store × product grain
        with base revenue/cost values.
        """
        rows: list[dict[str, Any]] = []
        row_count = plan.row_count

        # Resolve FK pools
        fk_pools: dict[str, list[Any]] = {}
        for fk in plan.foreign_keys:
            if fk.to_table in generated_tables:
                table_data = generated_tables[fk.to_table]
                if fk.target_is_key:
                    values = list({row[fk.to_column] for row in table_data if fk.to_column in row})
                else:
                    values = list({row[fk.to_column] for row in table_data if fk.to_column in row})
                fk_pools[fk.from_column] = sorted(values)
            else:
                fk_pools[fk.from_column] = []

        # Identify date FK column, product/store FK columns
        date_fk_col: str | None = None
        for fk in plan.foreign_keys:
            if fk.to_table.lower() == "date":
                date_fk_col = fk.from_column
                break

        # Also check date columns directly
        if not date_fk_col:
            for col_name in plan.date_columns:
                if col_name.lower() == "date":
                    date_fk_col = col_name
                    break

        # Get dates pool
        dates_pool: list[str] = []
        if date_fk_col and "Date" in generated_tables:
            dates_pool = [row["Date"] for row in generated_tables["Date"]]
            fk_pools[date_fk_col] = dates_pool

        # Identify unit price/cost columns from Product table if available
        product_prices: dict[str, tuple[float, float]] = {}  # ProductID -> (UnitCost, UnitPrice)
        if "Product" in generated_tables:
            for prod_row in generated_tables["Product"]:
                pid = prod_row.get("ProductID", "")
                ucost = prod_row.get("UnitCost", 10.0)
                uprice = prod_row.get("UnitPrice", 20.0)
                if isinstance(ucost, str):
                    try:
                        ucost = float(ucost)
                    except ValueError:
                        ucost = 10.0
                if isinstance(uprice, str):
                    try:
                        uprice = float(uprice)
                    except ValueError:
                        uprice = 20.0
                product_prices[pid] = (ucost, uprice)

        for i in range(row_count):
            row: dict[str, Any] = {}
            chosen_product_id: str | None = None

            for col in plan.columns:
                if col.is_key:
                    row[col.name] = self._generate_key(col, i, plan.table_name)
                elif col.name in fk_pools:
                    pool = fk_pools[col.name]
                    if pool:
                        row[col.name] = self.rng.choice(pool)
                    else:
                        row[col.name] = self._generate_value(col, i)
                    # Track product choice for price lookup
                    if col.name.lower() == "productid":
                        chosen_product_id = row[col.name]
                else:
                    row[col.name] = self._generate_value(col, i)

            # Fix financial columns for sales-type tables
            if chosen_product_id and chosen_product_id in product_prices:
                ucost, uprice = product_prices[chosen_product_id]
            else:
                ucost = self.rng.uniform(5.0, 50.0)
                uprice = ucost * self.rng.uniform(1.3, 2.5)

            # Set Quantity, UnitPrice, Revenue, Cost if they exist
            if "Quantity" in row:
                qty = self.rng.randint(1, 8)
                row["Quantity"] = qty
            else:
                qty = 1

            if "UnitPrice" in row:
                row["UnitPrice"] = round(uprice, 2)

            if "Revenue" in row:
                row["Revenue"] = round(qty * uprice, 2)

            if "Cost" in row:
                row["Cost"] = round(qty * ucost, 2)

            rows.append(row)

        return rows

    def _generate_key(self, col: ColumnSpec, index: int, table_name: str) -> Any:
        """Generate a unique key value for fact table."""
        if col.sample_values:
            sample = col.sample_values[0]
            import re
            match = re.match(r"^([A-Za-z-]+)(\d+)$", sample)
            if match:
                prefix = match.group(1)
                num_len = len(match.group(2))
                return f"{prefix}{str(index + 1).zfill(num_len)}"

        prefix = table_name[0].upper()
        return f"{prefix}-{str(index + 1).zfill(5)}"

    def _generate_value(self, col: ColumnSpec, index: int) -> Any:
        """Generate a base value for a non-key, non-FK column."""
        dtype = col.data_type.upper()

        if dtype in ("INTEGER", "INT"):
            if col.sample_values:
                try:
                    vals = [int(s) for s in col.sample_values]
                    return self.rng.randint(min(vals), max(vals))
                except ValueError:
                    pass
            return self.rng.randint(1, 10)

        elif dtype in ("REAL", "FLOAT", "DECIMAL"):
            if col.sample_values:
                try:
                    vals = [float(s) for s in col.sample_values]
                    return round(self.rng.uniform(min(vals), max(vals)), 2)
                except ValueError:
                    pass
            return round(self.rng.uniform(10.0, 100.0), 2)

        elif dtype == "BOOLEAN":
            return self.rng.choice(["TRUE", "FALSE"])

        elif dtype in ("DATE", "DATETIME"):
            return "2022-06-15"

        else:
            if col.sample_values:
                return self.rng.choice(col.sample_values)
            return f"{col.name}_{index + 1}"


def generate_all_tables(
    plan: GenerationPlan,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """Generate all tables according to the plan.

    Returns a dict mapping table name -> list of row dicts.
    """
    rng = random.Random(seed)
    generated: dict[str, list[dict[str, Any]]] = {}

    date_gen = DateGenerator(fiscal_year_start_month=plan.fiscal_year_start_month)
    dim_gen = DimensionGenerator(rng)
    fact_gen = FactGenerator(rng)

    for table_plan in plan.ordered_tables:
        if table_plan.role == TableRole.DATE_DIMENSION:
            if plan.date_range:
                generated[table_plan.table_name] = date_gen.generate(plan.date_range)
            else:
                # Fallback: generate 365 days of current year
                fallback_range = DateRange(
                    start=date(2022, 1, 1),
                    end=date(2022, 12, 31),
                )
                generated[table_plan.table_name] = date_gen.generate(fallback_range)
        elif table_plan.role == TableRole.FACT_TABLE:
            generated[table_plan.table_name] = fact_gen.generate(
                table_plan, generated, plan.date_range
            )
        else:
            # Dimension or helper tables
            generated[table_plan.table_name] = dim_gen.generate(
                table_plan, generated
            )

    return generated
