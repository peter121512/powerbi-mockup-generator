"""Semantic model analysis and generation planning.

Classifies tables by role, determines generation order, identifies
relationships, and parses time periods from the mock data narrative.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from pbi_gen.models.dashboard_spec import (
    ColumnSpec,
    DashboardSpec,
    MockDataNarrative,
    Relationship,
    TableSpec,
)


class TableRole(str, Enum):
    """Classification of a table's role in the semantic model."""

    DATE_DIMENSION = "date_dimension"
    CATEGORICAL_DIMENSION = "categorical_dimension"
    ENTITY_DIMENSION = "entity_dimension"
    FACT_TABLE = "fact_table"
    HELPER_TABLE = "helper_table"


@dataclass
class ForeignKey:
    """Represents a foreign key relationship."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    target_is_key: bool = True  # Whether the target column is actually a key


@dataclass
class TablePlan:
    """Generation plan for a single table."""

    table_name: str
    role: TableRole
    row_count: int
    columns: list[ColumnSpec]
    key_columns: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    generation_order: int = 0


@dataclass
class DateRange:
    """A parsed date range."""

    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass
class GenerationPlan:
    """Complete plan for generating all tables."""

    tables: list[TablePlan] = field(default_factory=list)
    date_range: DateRange | None = None
    fiscal_year_start_month: int = 4  # UK default: April

    @property
    def ordered_tables(self) -> list[TablePlan]:
        """Return tables sorted by generation order."""
        return sorted(self.tables, key=lambda t: t.generation_order)


def classify_table(
    table: TableSpec,
    relationships: list[Relationship],
    all_tables: list[TableSpec],
) -> TableRole:
    """Classify a table's role based on its structure and relationships."""
    name_lower = table.name.lower()

    # Date dimension detection
    if name_lower == "date" or name_lower.endswith("_date"):
        return TableRole.DATE_DIMENSION

    date_cols = [c for c in table.columns if c.data_type.upper() == "DATE" and c.is_key]
    if date_cols and any("month" in c.name.lower() for c in table.columns):
        return TableRole.DATE_DIMENSION

    # Fact table detection: has FK relationships to other tables (many-to-one from this table)
    outgoing_fks = [
        r for r in relationships
        if r.from_table == table.name and r.cardinality.value in ("manyToOne", "many_to_one")
    ]

    # A fact table typically has multiple FK relationships to dimension tables
    if len(outgoing_fks) >= 2:
        # Check it has numeric measure columns
        numeric_cols = [
            c for c in table.columns
            if c.data_type.upper() in ("REAL", "INTEGER", "FLOAT", "DECIMAL")
            and not c.is_key
            and not any(r.from_column == c.name for r in outgoing_fks)
        ]
        if numeric_cols:
            return TableRole.FACT_TABLE

    # Helper table detection (like Risk - has FKs but isn't really a fact)
    if outgoing_fks and not any(
        c.data_type.upper() in ("REAL", "FLOAT", "DECIMAL")
        for c in table.columns
        if not c.is_key
    ):
        # Has relationships but no numeric measure columns
        return TableRole.HELPER_TABLE

    # Entity dimension: has a key and descriptive text columns
    key_cols = [c for c in table.columns if c.is_key]
    if key_cols:
        text_cols = [c for c in table.columns if c.data_type.upper() == "TEXT" and not c.is_key]
        if len(text_cols) >= 2:
            return TableRole.ENTITY_DIMENSION

    # Categorical dimension: small table with mostly text
    if table.row_count_hint <= 50:
        return TableRole.CATEGORICAL_DIMENSION

    return TableRole.ENTITY_DIMENSION


def _identify_key_columns(table: TableSpec) -> list[str]:
    """Identify key columns in a table."""
    return [c.name for c in table.columns if c.is_key]


def _identify_date_columns(table: TableSpec) -> list[str]:
    """Identify date-typed columns."""
    return [c.name for c in table.columns if c.data_type.upper() in ("DATE", "DATETIME")]


def _build_foreign_keys(
    table: TableSpec,
    relationships: list[Relationship],
    all_tables: list[TableSpec],
) -> list[ForeignKey]:
    """Build foreign key list for a table."""
    fks = []
    for rel in relationships:
        if rel.from_table == table.name:
            # Check if target column is actually a key in the target table
            target_table = next((t for t in all_tables if t.name == rel.to_table), None)
            target_is_key = False
            if target_table:
                target_col = next(
                    (c for c in target_table.columns if c.name == rel.to_column), None
                )
                target_is_key = target_col.is_key if target_col else False

            fks.append(ForeignKey(
                from_table=rel.from_table,
                from_column=rel.from_column,
                to_table=rel.to_table,
                to_column=rel.to_column,
                target_is_key=target_is_key,
            ))
    return fks


def parse_time_period(
    narrative: MockDataNarrative | None,
    fiscal_year_start_month: int = 4,
) -> DateRange | None:
    """Parse a time_period string like 'FY2022-FY2023' into a date range.

    UK fiscal year runs April to March, so:
    - FY2022 = April 2021 to March 2022
    - FY2023 = April 2022 to March 2023
    - FY2022-FY2023 = April 2021 to March 2023
    """
    if not narrative or not narrative.time_period:
        return None

    period = narrative.time_period.strip()

    # Match patterns like 'FY2022-FY2023', 'FY2022 - FY2023'
    match = re.match(r"FY(\d{4})\s*[-–]\s*FY(\d{4})", period)
    if match:
        fy_start = int(match.group(1))
        fy_end = int(match.group(2))

        # FY starts in fiscal_year_start_month of the *previous* calendar year
        start_year = fy_start - 1
        start = date(start_year, fiscal_year_start_month, 1)

        # FY ends at end of month before fiscal_year_start_month in the FY year
        end_month = fiscal_year_start_month - 1 if fiscal_year_start_month > 1 else 12
        end_year = fy_end if end_month < fiscal_year_start_month else fy_end - 1
        # Last day of end month
        if end_month == 12:
            end = date(end_year, 12, 31)
        else:
            # Last day of end_month
            import calendar
            last_day = calendar.monthrange(end_year, end_month)[1]
            end = date(end_year, end_month, last_day)

        return DateRange(start=start, end=end)

    # Match single FY like 'FY2023'
    match = re.match(r"FY(\d{4})", period)
    if match:
        fy = int(match.group(1))
        start_year = fy - 1
        start = date(start_year, fiscal_year_start_month, 1)
        end_month = fiscal_year_start_month - 1 if fiscal_year_start_month > 1 else 12
        end_year = fy if end_month < fiscal_year_start_month else fy - 1
        import calendar
        last_day = calendar.monthrange(end_year, end_month)[1]
        end = date(end_year, end_month, last_day)
        return DateRange(start=start, end=end)

    return None


def build_generation_plan(spec: DashboardSpec) -> GenerationPlan:
    """Build a complete generation plan from a DashboardSpec.

    Classifies all tables, determines generation order (dimensions first,
    then facts/helpers), and parses the time period.
    """
    tables = spec.tables
    relationships = spec.relationships

    # Classify tables
    table_plans: list[TablePlan] = []
    for table in tables:
        role = classify_table(table, relationships, tables)
        key_cols = _identify_key_columns(table)
        date_cols = _identify_date_columns(table)
        fks = _build_foreign_keys(table, relationships, tables)

        table_plans.append(TablePlan(
            table_name=table.name,
            role=role,
            row_count=table.row_count_hint,
            columns=table.columns,
            key_columns=key_cols,
            date_columns=date_cols,
            foreign_keys=fks,
        ))

    # Determine generation order:
    # 1. Date dimension (no deps)
    # 2. Categorical/entity dimensions with no FKs
    # 3. Entity dimensions with FKs to other dimensions
    # 4. Fact tables (depend on dimensions)
    # 5. Helper tables (may depend on both dimensions and facts)
    order = 0
    for plan in table_plans:
        if plan.role == TableRole.DATE_DIMENSION:
            plan.generation_order = 0
        elif plan.role == TableRole.CATEGORICAL_DIMENSION and not plan.foreign_keys:
            plan.generation_order = 1
        elif plan.role == TableRole.ENTITY_DIMENSION and not plan.foreign_keys:
            plan.generation_order = 1
        elif plan.role in (TableRole.CATEGORICAL_DIMENSION, TableRole.ENTITY_DIMENSION):
            plan.generation_order = 2
        elif plan.role == TableRole.FACT_TABLE:
            plan.generation_order = 3
        elif plan.role == TableRole.HELPER_TABLE:
            plan.generation_order = 4
        else:
            plan.generation_order = 5

    # Parse time period
    date_range = parse_time_period(spec.mock_data_narrative)

    return GenerationPlan(
        tables=table_plans,
        date_range=date_range,
        fiscal_year_start_month=4,  # UK default
    )
