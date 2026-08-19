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


# Threshold: tables with more rows than this use URL-based M expressions
# rather than inline embedding.
INLINE_ROW_THRESHOLD = 1000


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


def generate_inline_m_from_db(table_name: str, db_path: Path) -> str:
    """Generate an inline M expression directly from a SQLite table.

    Convenience function that reads from the database without requiring
    an intermediate CSV export.

    Args:
        table_name: Name of the table in the database.
        db_path: Path to the SQLite database.

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
    return _build_inline_expression(columns, str_rows)


def _build_inline_expression(headers: list[str], rows: list[list[str]]) -> str:
    """Build a Table.FromRows M expression with compressed inline data.

    Args:
        headers: Column names.
        rows: List of row values (all as strings).

    Returns:
        M expression string.
    """
    # Build the JSON array of arrays
    json_data = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
    json_bytes = json_data.encode("utf-8")

    # Compress with deflate and base64-encode
    compressed = zlib.compress(json_bytes, level=9)
    # Strip the zlib header (first 2 bytes) and checksum (last 4 bytes)
    # to get raw deflate — Power BI uses raw deflate
    raw_deflate = compressed[2:-4]
    encoded = base64.b64encode(raw_deflate).decode("ascii")

    # Build the type table column spec
    col_specs = ", ".join(f"{col} = text" for col in headers)

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
