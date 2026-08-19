"""Data staging for Power BI deployment.

Exports SQLite data to formats consumable by Power BI semantic models:
- CSV files for blob/URL-based loading
- Inline M expressions with embedded data (Table.FromRows) for dev/local use
- URL-based M expressions for production blob storage

The key insight: fabric-cicd deploys TMDL definitions but doesn't upload data.
Data reaches the model via M expressions in TMDL partitions that resolve during
dataset refresh.
"""

from __future__ import annotations

import base64
import csv
import json
import sqlite3
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pbi_gen.models.dashboard_spec import TableSpec


# Threshold: tables with more rows than this use URL-based M expressions
# rather than inline embedding.
INLINE_ROW_THRESHOLD = 50000


# Mapping from DashboardSpec data types to Power Query M types.
# These types are used in the Table.FromRows `type table` declaration so that
# Power BI does NOT need to infer or implicitly convert column types during refresh.
#
# NOTE: date/datetime remain as 'text' in the Table.FromRows type table because
# the JSON data contains ISO format strings (e.g. "2021-04-01") which M cannot
# directly parse as dates in Table.FromRows. A subsequent Table.TransformColumnTypes
# step handles the explicit conversion from text to date.
_M_TYPE_MAP: dict[str, str] = {
    "TEXT": "text",
    "INTEGER": "Int64.Type",
    "INT": "Int64.Type",
    "REAL": "number",
    "FLOAT": "number",
    "DECIMAL": "number",
    "DATE": "text",
    "DATETIME": "text",
    "BOOLEAN": "logical",
}

# Types that require an explicit conversion step after Table.FromRows.
# Maps spec data type → M type for Table.TransformColumnTypes.
_M_CONVERSION_TYPES: dict[str, str] = {
    "DATE": "date",
    "DATETIME": "datetime",
}


def export_to_csv(db_path: Path, output_dir: Path) -> dict[str, Path]:
    """Export each SQLite table to a CSV file.

    Args:
        db_path: Path to the SQLite database.
        output_dir: Directory to write CSV files into (created if missing).

    Returns:
        Mapping of {table_name: csv_path} for all exported tables.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]

        result: dict[str, Path] = {}
        for table_name in table_names:
            csv_path = output_dir / f"{table_name}.csv"
            cursor.execute(f"SELECT * FROM [{table_name}]")  # noqa: S608
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)

            result[table_name] = csv_path

        return result
    finally:
        conn.close()


def generate_m_expression(table_name: str, csv_url: str) -> str:
    """Generate a Power Query M expression that loads from a CSV URL.

    Used for production deployment where data is hosted on blob storage
    or another accessible HTTP endpoint.

    Args:
        table_name: Name of the table (for documentation purposes).
        csv_url: Publicly accessible URL to the CSV file.

    Returns:
        Valid Power Query M expression string.
    """
    return (
        "let\n"
        f'    Source = Csv.Document(Web.Contents("{csv_url}"), '
        '[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),\n'
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n'
        "in\n"
        '    #"Promoted Headers"'
    )


def generate_inline_m_expression(table_name: str, csv_path: Path) -> str:
    """Generate an M expression with embedded data.

    For small tables (<=INLINE_ROW_THRESHOLD rows), embeds the data directly
    using Table.FromRows with compressed JSON. For larger tables, falls back
    to Csv.Document with a relative path reference.

    The inline approach:
    1. Read all rows from CSV
    2. Convert to JSON array of arrays
    3. Compress with deflate, encode to base64
    4. Embed in M expression as Table.FromRows(Json.Document(Binary.Decompress(...)))

    Args:
        table_name: Name of the table.
        csv_path: Path to the CSV file with headers.

    Returns:
        Valid Power Query M expression string.
    """
    csv_path = Path(csv_path)

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    if len(rows) > INLINE_ROW_THRESHOLD:
        # Fall back to Csv.Document for large tables
        return (
            "let\n"
            f'    Source = Csv.Document(Web.Contents("data/{table_name}.csv"), '
            '[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),\n'
            '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n'
            "in\n"
            '    #"Promoted Headers"'
        )

    return _build_inline_expression(headers, rows)


def generate_inline_m_from_db(
    table_name: str,
    db_path: Path,
    table_spec: "TableSpec | None" = None,
) -> str:
    """Generate an inline M expression directly from a SQLite table.

    Convenience function that reads from the database without requiring
    an intermediate CSV export.

    When *table_spec* is provided, proper M column types (date, number, logical)
    are declared in the ``type table`` clause. This avoids Power BI needing to
    implicitly convert text values during dataset refresh, which can fail for
    dateTime and boolean columns depending on locale.

    Args:
        table_name: Name of the table in the database.
        db_path: Path to the SQLite database.
        table_spec: Optional TableSpec with column metadata for type mapping.

    Returns:
        Valid Power Query M expression string.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}]")  # noqa: S608
        columns = [desc[0] for desc in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
    finally:
        conn.close()

    if len(rows) > INLINE_ROW_THRESHOLD:
        return (
            "let\n"
            f'    Source = Csv.Document(Web.Contents("data/{table_name}.csv"), '
            '[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),\n'
            '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n'
            "in\n"
            '    #"Promoted Headers"'
        )

    # Convert all values to strings for M expression compatibility
    str_rows = [[str(v) if v is not None else "" for v in row] for row in rows]

    # Build column type mapping from table_spec if available
    column_types: dict[str, str] | None = None
    conversion_columns: list[tuple[str, str]] | None = None
    if table_spec:
        column_types = _build_column_type_map(table_spec)
        conversion_columns = _build_conversion_columns(table_spec)

    return _build_inline_expression(columns, str_rows, column_types=column_types, conversion_columns=conversion_columns)


def _build_column_type_map(table_spec: "TableSpec") -> dict[str, str]:
    """Build a mapping of column name → M type from a TableSpec.

    Maps the DashboardSpec data types to Power Query M types used in
    the ``type table`` clause of Table.FromRows.
    """
    type_map: dict[str, str] = {}
    for col in table_spec.columns:
        m_type = _M_TYPE_MAP.get(col.data_type.upper(), "text")
        type_map[col.name] = m_type
    return type_map


def _build_conversion_columns(table_spec: "TableSpec") -> list[tuple[str, str]]:
    """Identify columns that need explicit type conversion after Table.FromRows.

    Returns a list of (column_name, m_type) tuples for columns that need
    a Table.TransformColumnTypes step.
    """
    conversions: list[tuple[str, str]] = []
    for col in table_spec.columns:
        conv_type = _M_CONVERSION_TYPES.get(col.data_type.upper())
        if conv_type:
            conversions.append((col.name, conv_type))
    return conversions


def _build_inline_expression(headers: list[str], rows: list[list[str]], column_types: dict[str, str] | None = None, conversion_columns: list[tuple[str, str]] | None = None) -> str:
    """Build a Table.FromRows M expression with compressed inline data.

    Args:
        headers: Column names.
        rows: List of row values (all as strings).
        column_types: Optional mapping of column_name -> M type (text, date, number, etc.)
        conversion_columns: Optional list of (column_name, m_type) for columns needing
            explicit type conversion via Table.TransformColumnTypes.

    Returns:
        M expression string.
    """
    # Convert None/null values to empty strings for JSON serialization
    clean_rows = []
    for row in rows:
        clean_row = [str(v) if v is not None else "" for v in row]
        clean_rows.append(clean_row)

    # Build the JSON array of arrays
    json_data = json.dumps(clean_rows, separators=(",", ":"), ensure_ascii=False)
    json_bytes = json_data.encode("utf-8")

    # Compress with deflate and base64-encode
    compressed = zlib.compress(json_bytes, level=9)
    # Strip the zlib header (first 2 bytes) and checksum (last 4 bytes)
    # to get raw deflate — Power BI uses raw deflate
    raw_deflate = compressed[2:-4]
    encoded = base64.b64encode(raw_deflate).decode("ascii")

    # Build the type table column spec
    type_map = column_types or {}
    col_specs = ", ".join(
        f"{col} = {type_map.get(col, 'text')}" for col in headers
    )

    # If there are date/datetime columns that need conversion, add a transformation step
    if conversion_columns:
        # Build the conversion list for Table.TransformColumnTypes
        # M syntax: {{"ColName", type date}, {"ColName2", type datetime}}
        conv_items = ", ".join(
            f'{{"{col}", type {m_type}}}' for col, m_type in conversion_columns
        )
        conv_list = "{" + conv_items + "}"
        return (
            "let\n"
            "    Source = Table.FromRows(\n"
            "        Json.Document(Binary.Decompress("
            f'Binary.FromText("{encoded}", BinaryEncoding.Base64), '
            "Compression.Deflate)),\n"
            f"        type table [{col_specs}]\n"
            "    ),\n"
            f'    #"Converted Types" = Table.TransformColumnTypes(Source, {conv_list})\n'
            "in\n"
            '    #"Converted Types"'
        )

    return (
        "let\n"
        "    Source = Table.FromRows(\n"
        "        Json.Document(Binary.Decompress("
        f'Binary.FromText("{encoded}", BinaryEncoding.Base64), '
        "Compression.Deflate)),\n"
        f"        type table [{col_specs}]\n"
        "    )\n"
        "in\n"
        "    Source"
    )
