"""SQLite writer for generated synthetic data.

Creates a SQLite database with typed tables and efficiently inserts
generated data. Maps Power BI data types to SQLite storage types.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from pbi_gen.datagen.planner import GenerationPlan, TablePlan
from pbi_gen.models.dashboard_spec import ColumnSpec


# Power BI / spec data type to SQLite type mapping
_TYPE_MAP: dict[str, str] = {
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "INT": "INTEGER",
    "REAL": "REAL",
    "FLOAT": "REAL",
    "DECIMAL": "REAL",
    "DATE": "TEXT",  # SQLite has no native DATE; store as TEXT in ISO format
    "DATETIME": "TEXT",
    "BOOLEAN": "TEXT",  # Store as 'TRUE'/'FALSE' text
}


def _sqlite_type(data_type: str) -> str:
    """Map a spec data type to a SQLite column type."""
    return _TYPE_MAP.get(data_type.upper(), "TEXT")


def _build_create_table_sql(plan: TablePlan) -> str:
    """Build a CREATE TABLE statement from a TablePlan."""
    col_defs: list[str] = []
    pk_cols: list[str] = []

    for col in plan.columns:
        sqlite_type = _sqlite_type(col.data_type)
        col_def = f'"{col.name}" {sqlite_type}'
        if col.is_key:
            pk_cols.append(f'"{col.name}"')
        col_defs.append(col_def)

    # Add primary key constraint
    if pk_cols:
        col_defs.append(f"PRIMARY KEY ({', '.join(pk_cols)})")

    cols_sql = ",\n  ".join(col_defs)
    return f'CREATE TABLE IF NOT EXISTS "{plan.table_name}" (\n  {cols_sql}\n);'


def write_sqlite(
    output_path: Path,
    tables: dict[str, list[dict[str, Any]]],
    plan: GenerationPlan,
) -> None:
    """Write all generated tables to a SQLite database.

    Creates the database file at output_path. If the file already exists,
    it will be overwritten.

    Args:
        output_path: Path for the output .sqlite file.
        tables: Dict mapping table name to list of row dicts.
        plan: The generation plan containing table schemas.
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing file to start fresh
    if output_path.exists():
        output_path.unlink()

    conn = sqlite3.connect(str(output_path))
    try:
        cursor = conn.cursor()

        # Create tables and insert data in plan order
        for table_plan in plan.ordered_tables:
            table_name = table_plan.table_name
            if table_name not in tables:
                continue

            # Create table
            create_sql = _build_create_table_sql(table_plan)
            cursor.execute(create_sql)

            # Insert data
            rows = tables[table_name]
            if not rows:
                continue

            # Get column names from plan (preserves order)
            col_names = [col.name for col in table_plan.columns]

            # Build insert statement
            placeholders = ", ".join(["?"] * len(col_names))
            quoted_cols = ", ".join([f'"{c}"' for c in col_names])
            insert_sql = f'INSERT INTO "{table_name}" ({quoted_cols}) VALUES ({placeholders})'

            # Batch insert for efficiency
            batch: list[tuple] = []
            for row in rows:
                values = tuple(row.get(col, None) for col in col_names)
                batch.append(values)

                if len(batch) >= 1000:
                    cursor.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining
            if batch:
                cursor.executemany(insert_sql, batch)

        conn.commit()
    finally:
        conn.close()
