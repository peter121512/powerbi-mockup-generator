"""TMDL generation for the Power BI semantic model.

Generates TMDL text files for tables, columns, measures, and relationships
from the DashboardSpec data model definitions.
"""

from __future__ import annotations

from uuid import uuid4

from pbi_gen.models import ColumnSpec, DashboardSpec, MeasureSpec, Relationship, TableSpec


# ─────────────────────────────────────────────────────────────────────────────
# Data type mapping
# ─────────────────────────────────────────────────────────────────────────────

COLUMN_TYPE_MAP: dict[str, str] = {
    "TEXT": "string",
    "INTEGER": "int64",
    "REAL": "double",
    "DATE": "dateTime",
    "DATETIME": "dateTime",
    "BOOLEAN": "boolean",
}

# Default summarizeBy per data type
_SUMMARIZE_MAP: dict[str, str] = {
    "string": "none",
    "int64": "sum",
    "double": "sum",
    "dateTime": "none",
    "boolean": "none",
}


def map_column_type(data_type: str) -> str:
    """Map a DashboardSpec data type to a TMDL dataType string."""
    return COLUMN_TYPE_MAP.get(data_type.upper(), "string")


def _make_lineage_tag(seed: str = "") -> str:
    """Generate a deterministic-style UUID for lineage tags.

    Uses uuid4 for uniqueness. The seed parameter is reserved for future
    deterministic generation.
    """
    return str(uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# TMDL Generation
# ─────────────────────────────────────────────────────────────────────────────


def generate_model_tmdl() -> str:
    """Generate the model.tmdl content."""
    return (
        "model Model\n"
        "    culture: en-US\n"
        "    defaultPowerBIDataSourceVersion: powerBIV3\n"
    )


def _render_column(col: ColumnSpec, table_name: str) -> str:
    """Render a single column definition in TMDL."""
    tmdl_type = map_column_type(col.data_type)
    summarize = "none" if col.is_key else _SUMMARIZE_MAP.get(tmdl_type, "none")

    lines = [
        f"\n    column {col.name}",
        f"        dataType: {tmdl_type}",
    ]
    if col.is_key:
        lines.append("        isKey: true")
    lines.append(f"        lineageTag: {_make_lineage_tag()}")
    lines.append(f"        sourceColumn: {col.name}")
    lines.append(f"        summarizeBy: {summarize}")

    return "\n".join(lines)


def _render_measure(measure: MeasureSpec, table_name: str) -> str:
    """Render a single measure definition in TMDL."""
    # Quote the measure name if it contains spaces
    name_str = f"'{measure.name}'" if " " in measure.name else measure.name
    lines = [
        f"\n    measure {name_str} = {measure.expression}",
    ]
    if measure.format_string:
        lines.append(f"        formatString: {measure.format_string}")
    lines.append(f"        lineageTag: {_make_lineage_tag()}")
    return "\n".join(lines)


def _render_partition(table_name: str, m_expression: str | None = None) -> str:
    """Render a partition definition for a table.

    Args:
        table_name: Name of the table.
        m_expression: Optional M expression to use as the partition source.
            If provided, the expression is embedded directly. Otherwise a
            placeholder Csv.Document expression is used.

    Returns:
        TMDL partition text block.
    """
    if m_expression is not None:
        # Embed the provided M expression with correct TMDL indentation
        indented_lines = []
        for line in m_expression.splitlines():
            indented_lines.append(f"            {line}" if line.strip() else "")
        source_block = "\n".join(indented_lines)
        lines = [
            f"\n    partition {table_name} = m",
            "        mode: import",
            "        source =",
            source_block,
        ]
    else:
        lines = [
            f"\n    partition {table_name} = m",
            "        mode: import",
            "        source =",
            "            let",
            f'                Source = Csv.Document(Web.Contents("data/{table_name}.csv"), [Delimiter=",", Encoding=65001]),',
            '                #"Promoted Headers" = Table.PromoteHeaders(Source)',
            "            in",
            '                #"Promoted Headers"',
        ]
    return "\n".join(lines)


def generate_table_tmdl(
    table: TableSpec,
    measures: list[MeasureSpec] | None = None,
    partition_sources: dict[str, str] | None = None,
) -> str:
    """Generate a complete table TMDL file.

    Args:
        table: The table specification.
        measures: All measures; only those homed to this table will be rendered.
        partition_sources: Optional mapping of {table_name: m_expression}.
            When provided, the M expression for this table is used instead of
            the default placeholder.

    Returns:
        Complete TMDL text for the table file.
    """
    table_measures = [m for m in (measures or []) if m.table == table.name]

    lines = [
        f"table {table.name}",
        f"    lineageTag: {_make_lineage_tag()}",
    ]

    # Columns
    for col in table.columns:
        lines.append(_render_column(col, table.name))

    # Measures
    for measure in table_measures:
        lines.append(_render_measure(measure, table.name))

    # Partition — use supplied M expression if available
    m_expression = (partition_sources or {}).get(table.name)
    lines.append(_render_partition(table.name, m_expression))

    return "\n".join(lines) + "\n"


def generate_relationships_tmdl(relationships: list[Relationship]) -> str:
    """Generate the relationships.tmdl file content.

    Args:
        relationships: List of relationship definitions.

    Returns:
        TMDL text for the relationships file.
    """
    if not relationships:
        return ""

    sections = []
    for rel in relationships:
        tag = _make_lineage_tag()
        section = (
            f"relationship {tag}\n"
            f"    fromColumn: {rel.from_table}.{rel.from_column}\n"
            f"    toColumn: {rel.to_table}.{rel.to_column}"
        )
        sections.append(section)

    return "\n\n".join(sections) + "\n"


def generate_definition_pbism() -> dict:
    """Generate the definition.pbism JSON content."""
    return {
        "version": "4.0",
        "settings": {},
    }
