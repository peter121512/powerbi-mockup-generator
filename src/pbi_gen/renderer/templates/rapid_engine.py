"""Rapid dashboard deployment engine.

Provides the full pipeline from intent/reference to deployed Power BI report:
- Template selection from analytical intent
- Semantic model discovery
- Semantic model construction (fact/dim inference, measures, TMDL generation)
- Compact page-spec format
- Unified preflight validation (model + page)
- Optimised deployment path with timing

This module is DOMAIN-AGNOSTIC. It must not contain any domain-specific logic
(no Product, Customer, Financial specific code).
"""

from __future__ import annotations

import base64
import csv
import json
import time
import uuid
import zipfile
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import requests

from pbi_gen.renderer.templates.registry import (
    CUSTOM_VISUAL_GUIDS,
    DesignTokens,
    FieldRef,
    PageShell,
    TemplateRegistry,
    VisualBinding,
)
from pbi_gen.renderer.templates.builder import PageBuilder


# ─────────────────────────────────────────────────────────────────────────────
# Template Catalog & Selection
# ─────────────────────────────────────────────────────────────────────────────

_CATALOG_PATH = Path(__file__).parent / "template_catalog.json"


def load_template_catalog() -> dict:
    """Load the machine-readable template catalog."""
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


# Analytical intent → template mapping (deterministic, no LLM needed)
INTENT_TO_TEMPLATE: dict[str, list[str]] = {
    "headline_metric": ["premium_kpi"],
    "time_trend": ["premium_trend", "premium_column"],
    "categorical_comparison": ["premium_column", "premium_bar"],
    "ranking": ["premium_bar"],
    "composition_share": ["premium_donut"],
    "distribution": ["premium_column"],
    "bridge_waterfall": ["premium_waterfall"],
    "progress_gauge": ["premium_gauge"],
    "detail_table": ["premium_table"],
    "narrative_insight": ["premium_insights"],
    "center_overlay": ["donut_center_kpi"],
}


def select_template(
    intent: str,
    *,
    has_time_axis: bool = False,
    category_count: int = 0,
    measure_count: int = 1,
    prefer_horizontal: bool = False,
) -> str:
    """Select the best template for a given analytical intent.

    Returns template_id from the registry.
    """
    candidates = INTENT_TO_TEMPLATE.get(intent, [])
    if not candidates:
        raise ValueError(f"Unknown intent: {intent}. Available: {list(INTENT_TO_TEMPLATE.keys())}")

    if len(candidates) == 1:
        return candidates[0]

    # Disambiguation rules
    if intent == "time_trend":
        # premium_trend only works with numeric/date categories
        return "premium_trend" if has_time_axis else "premium_column"

    if intent == "categorical_comparison":
        if prefer_horizontal:
            return "premium_bar"
        return "premium_column"

    return candidates[0]


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Model Discovery
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColumnInfo:
    """Metadata about a single column in the model."""
    name: str
    data_type: str  # string, int64, double, boolean, dateTime
    summarize_by: str = "none"
    is_key: bool = False
    format_string: str = ""

    @property
    def is_numeric(self) -> bool:
        return self.data_type in ("int64", "double", "decimal")

    @property
    def is_date(self) -> bool:
        return self.data_type == "dateTime" or "date" in self.name.lower()

    @property
    def is_categorical(self) -> bool:
        return self.data_type == "string" and not self.is_date


@dataclass
class MeasureInfo:
    """Metadata about a DAX measure."""
    name: str
    expression: str
    format_string: str = ""
    table: str = ""

    @property
    def is_currency(self) -> bool:
        return "£" in self.format_string or "$" in self.format_string or "€" in self.format_string

    @property
    def is_percentage(self) -> bool:
        return "%" in self.format_string


@dataclass
class TableInfo:
    """Metadata about a table in the model."""
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    measures: list[MeasureInfo] = field(default_factory=list)
    row_count: Optional[int] = None
    is_calculated: bool = False

    @property
    def numeric_columns(self) -> list[ColumnInfo]:
        return [c for c in self.columns if c.is_numeric]

    @property
    def date_columns(self) -> list[ColumnInfo]:
        return [c for c in self.columns if c.is_date]

    @property
    def categorical_columns(self) -> list[ColumnInfo]:
        return [c for c in self.columns if c.is_categorical]


@dataclass
class RelationshipInfo:
    """A relationship between two tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    direction: str = "oneToMany"  # or manyToOne, manyToMany


@dataclass
class ModelMetadata:
    """Complete metadata about a semantic model."""
    model_id: str
    model_name: str
    tables: list[TableInfo] = field(default_factory=list)
    relationships: list[RelationshipInfo] = field(default_factory=list)

    def get_table(self, name: str) -> Optional[TableInfo]:
        for t in self.tables:
            if t.name == name:
                return t
        return None

    def all_measures(self) -> list[MeasureInfo]:
        measures = []
        for t in self.tables:
            for m in t.measures:
                measures.append(MeasureInfo(
                    name=m.name, expression=m.expression,
                    format_string=m.format_string, table=t.name,
                ))
        return measures

    def find_date_table(self) -> Optional[TableInfo]:
        """Find the canonical Date/calendar table."""
        for t in self.tables:
            if t.name.lower() in ("date", "calendar", "dim_date", "dimdate"):
                return t
            if len(t.date_columns) > 2 and len(t.numeric_columns) < 3:
                return t
        return None

    def has_relationship(self, from_table: str, to_table: str) -> bool:
        for r in self.relationships:
            if (r.from_table == from_table and r.to_table == to_table) or \
               (r.from_table == to_table and r.to_table == from_table):
                return True
        return False


def discover_model(
    workspace_id: str,
    model_id: str,
    headers: dict,
    fabric_api_base: str = "https://api.fabric.microsoft.com/v1",
) -> ModelMetadata:
    """Discover semantic model metadata from the Fabric REST API.

    Fetches the TMDL definition and parses table/column/measure/relationship info.
    """
    # Request definition
    r = requests.post(
        f"{fabric_api_base}/workspaces/{workspace_id}/semanticModels/{model_id}/getDefinition",
        headers=headers, json={}, timeout=30,
    )
    if r.status_code != 202:
        raise RuntimeError(f"getDefinition failed: {r.status_code} {r.text[:200]}")

    loc = r.headers.get("Location", "")
    for _ in range(20):
        time.sleep(2)
        poll = requests.get(loc, headers=headers, timeout=30)
        if poll.json().get("status") == "Succeeded":
            break
    else:
        raise RuntimeError("getDefinition timed out")

    result = requests.get(f"{loc}/result", headers=headers, timeout=30)
    definition = result.json().get("definition", result.json())
    parts = definition.get("parts", [])

    # Parse TMDL parts
    tables: list[TableInfo] = []
    relationships: list[RelationshipInfo] = []
    model_name = ""

    for part in parts:
        path = part["path"]
        content = base64.b64decode(part["payload"]).decode("utf-8")

        if path.startswith("definition/tables/") and path.endswith(".tmdl"):
            table = _parse_tmdl_table(content)
            if table:
                tables.append(table)
        elif path == "definition/model.tmdl":
            # Parse relationships from model.tmdl
            rels = _parse_tmdl_relationships(content)
            relationships.extend(rels)
        elif path == "definition/database.tmdl":
            # Extract model name
            for line in content.split("\n"):
                if line.startswith("database"):
                    model_name = line.split("database")[-1].strip().strip("'\"")

    return ModelMetadata(
        model_id=model_id,
        model_name=model_name or "UnknownModel",
        tables=tables,
        relationships=relationships,
    )


def _parse_tmdl_table(content: str) -> Optional[TableInfo]:
    """Parse a TMDL table definition into TableInfo."""
    lines = content.split("\n")
    if not lines or not lines[0].startswith("table "):
        return None

    table_name = lines[0].replace("table ", "").strip()
    columns: list[ColumnInfo] = []
    measures: list[MeasureInfo] = []
    is_calculated = False

    i = 1
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("column "):
            col_name = line.replace("column ", "").strip()
            data_type = "string"
            summarize = "none"
            fmt = ""
            i += 1
            while i < len(lines) and lines[i].startswith("\t\t"):
                prop = lines[i].strip()
                if prop.startswith("dataType:"):
                    data_type = prop.split(":", 1)[1].strip()
                elif prop.startswith("summarizeBy:"):
                    summarize = prop.split(":", 1)[1].strip()
                elif prop.startswith("formatString:"):
                    fmt = prop.split(":", 1)[1].strip()
                i += 1
            columns.append(ColumnInfo(
                name=col_name, data_type=data_type,
                summarize_by=summarize, format_string=fmt,
            ))

        elif line.startswith("measure "):
            parts = line.replace("measure ", "").split("=", 1)
            measure_name = parts[0].strip()
            expression = parts[1].strip() if len(parts) > 1 else ""
            fmt = ""
            i += 1
            # Collect multi-line expression and properties
            while i < len(lines) and lines[i].startswith("\t\t"):
                prop = lines[i].strip()
                if prop.startswith("formatString:"):
                    fmt = prop.split(":", 1)[1].strip()
                elif not prop.startswith("lineageTag:") and expression and "=" not in prop:
                    # Could be continuation of expression
                    pass
                i += 1
            measures.append(MeasureInfo(
                name=measure_name, expression=expression, format_string=fmt,
            ))

        elif line.startswith("partition ") and "calculated" in line:
            is_calculated = True
            i += 1
        else:
            i += 1

    return TableInfo(
        name=table_name, columns=columns, measures=measures,
        is_calculated=is_calculated,
    )


def _parse_tmdl_relationships(content: str) -> list[RelationshipInfo]:
    """Parse relationships from model.tmdl content."""
    relationships: list[RelationshipInfo] = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("relationship"):
            from_table = from_col = to_table = to_col = ""
            i += 1
            while i < len(lines) and (lines[i].startswith("\t") or lines[i].strip() == ""):
                prop = lines[i].strip()
                if prop.startswith("fromColumn:"):
                    # Format: fromColumn: Table.Column
                    ref = prop.split(":", 1)[1].strip()
                    if "." in ref:
                        from_table, from_col = ref.rsplit(".", 1)
                    else:
                        from_col = ref
                elif prop.startswith("toColumn:"):
                    ref = prop.split(":", 1)[1].strip()
                    if "." in ref:
                        to_table, to_col = ref.rsplit(".", 1)
                    else:
                        to_col = ref
                elif prop.startswith("fromTable:"):
                    from_table = prop.split(":", 1)[1].strip()
                elif prop.startswith("toTable:"):
                    to_table = prop.split(":", 1)[1].strip()
                i += 1
            if from_table and to_table:
                relationships.append(RelationshipInfo(
                    from_table=from_table, from_column=from_col,
                    to_table=to_table, to_column=to_col,
                ))
        else:
            i += 1

    return relationships


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Model Construction
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColumnSpec:
    """Specification for a column in a new table."""
    name: str
    data_type: str  # string, int64, double, boolean, dateTime
    summarize_by: str = "none"
    source_column: Optional[str] = None  # CSV column name if different


@dataclass
class MeasureSpec:
    """Specification for a DAX measure."""
    name: str
    expression: str
    format_string: str = "#,##0"
    description: str = ""


@dataclass
class RelationshipSpec:
    """Specification for a relationship."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class TableSpec:
    """Full specification for a new table."""
    name: str
    columns: list[ColumnSpec]
    measures: list[MeasureSpec] = field(default_factory=list)
    data_source: Optional[str] = None  # CSV path for DATATABLE
    max_rows: int = 1000


@dataclass
class ModelSpec:
    """Full specification for model construction/extension."""
    tables: list[TableSpec] = field(default_factory=list)
    relationships: list[RelationshipSpec] = field(default_factory=list)
    measures: list[MeasureSpec] = field(default_factory=list)  # Measures on existing tables


def infer_column_type(values: list[str]) -> str:
    """Infer the data type of a column from sample values."""
    if not values:
        return "string"

    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "string"

    # Check boolean
    bool_values = {"true", "false", "yes", "no", "1", "0"}
    if all(v.lower() in bool_values for v in non_empty[:100]):
        return "boolean"

    # Check numeric (int)
    try:
        [int(v) for v in non_empty[:100]]
        return "int64"
    except (ValueError, TypeError):
        pass

    # Check numeric (double)
    try:
        [float(v) for v in non_empty[:100]]
        return "double"
    except (ValueError, TypeError):
        pass

    # Check date-like
    import re
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}")
    if all(date_pattern.match(v) for v in non_empty[:50]):
        return "dateTime"

    return "string"


def infer_table_role(
    table_name: str,
    columns: list[ColumnSpec],
    row_count: int,
) -> Literal["fact", "dimension", "bridge", "unknown"]:
    """Heuristic to classify a table as fact or dimension.

    Rules:
    - High cardinality + multiple numeric additive columns → fact
    - Low cardinality + mostly categorical → dimension
    - Contains 'dim' or 'lookup' in name → dimension
    - Contains 'fact' or 'sales' or 'transactions' in name → fact
    """
    name_lower = table_name.lower()

    # Name-based heuristics
    if any(kw in name_lower for kw in ("dim", "lookup", "category", "region")):
        return "dimension"
    if any(kw in name_lower for kw in ("fact", "sales", "transactions", "orders", "events")):
        return "fact"

    # Column-based heuristics
    numeric_cols = [c for c in columns if c.data_type in ("int64", "double", "decimal")]
    categorical_cols = [c for c in columns if c.data_type == "string"]
    date_cols = [c for c in columns if c.data_type == "dateTime" or "date" in c.name.lower()]

    # Many numeric additive columns → likely fact
    if len(numeric_cols) >= 3 and row_count > 100:
        return "fact"

    # Mostly categorical with few rows → dimension
    if len(categorical_cols) > len(numeric_cols) and row_count < 100:
        return "dimension"

    # Date table
    if len(date_cols) >= 2 and "date" in name_lower:
        return "dimension"

    return "unknown"


def infer_relationships(
    tables: list[TableSpec],
    csv_data: dict[str, list[dict]],
) -> list[RelationshipSpec]:
    """Infer relationships between tables based on column name overlap and value overlap.

    Conservative: only infer when confidence is high.
    """
    relationships: list[RelationshipSpec] = []

    for i, t1 in enumerate(tables):
        for j, t2 in enumerate(tables):
            if i >= j:
                continue

            for c1 in t1.columns:
                for c2 in t2.columns:
                    # Same column name pattern suggests FK relationship
                    if c1.name == c2.name or \
                       c1.name == f"{t2.name}ID" or c2.name == f"{t1.name}ID" or \
                       c1.name.replace("ID", "") == t2.name or c2.name.replace("ID", "") == t1.name:

                        # Determine direction: smaller distinct count = dimension side
                        data1 = csv_data.get(t1.name, [])
                        data2 = csv_data.get(t2.name, [])

                        if data1 and data2:
                            vals1 = set(row.get(c1.name, "") for row in data1[:500])
                            vals2 = set(row.get(c2.name, "") for row in data2[:500])

                            # Check value overlap
                            overlap = vals1 & vals2
                            if len(overlap) < 2:
                                continue

                            # Smaller distinct count = one-side (dimension)
                            if len(vals1) <= len(vals2):
                                relationships.append(RelationshipSpec(
                                    from_table=t2.name, from_column=c2.name,
                                    to_table=t1.name, to_column=c1.name,
                                ))
                            else:
                                relationships.append(RelationshipSpec(
                                    from_table=t1.name, from_column=c1.name,
                                    to_table=t2.name, to_column=c2.name,
                                ))

    return relationships


# Common measure patterns
MEASURE_PATTERNS: dict[str, str] = {
    "sum": "SUM({table}[{column}])",
    "count": "COUNTROWS({table})",
    "distinct_count": "DISTINCTCOUNT({table}[{column}])",
    "average": "AVERAGE({table}[{column}])",
    "max": "MAX({table}[{column}])",
    "min": "MIN({table}[{column}])",
    "ratio": "DIVIDE({numerator}, {denominator})",
    "share_of_total": "DIVIDE({measure}, CALCULATE({measure}, ALL({table})))",
    "count_filtered": "COUNTROWS(FILTER({table}, {filter_expr}))",
    "sum_filtered": "CALCULATE(SUM({table}[{column}]), {filter_expr})",
}


def infer_measures(
    table: TableSpec,
    role: str,
    existing_measures: list[str] = None,
) -> list[MeasureSpec]:
    """Infer standard measures for a table based on its role and columns.

    Only generates measures that don't already exist.
    """
    existing = set(existing_measures or [])
    measures: list[MeasureSpec] = []

    numeric_cols = [c for c in table.columns if c.data_type in ("int64", "double", "decimal")]
    categorical_cols = [c for c in table.columns if c.data_type == "string"]

    if role == "fact":
        # Sum measures for numeric columns that look additive
        for col in numeric_cols:
            name_lower = col.name.lower()
            if any(kw in name_lower for kw in ("amount", "value", "revenue", "cost", "price", "quantity", "total", "sales")):
                measure_name = f"Total{col.name}" if not col.name.startswith("Total") else col.name
                if measure_name not in existing:
                    fmt = "£#,##0" if any(kw in name_lower for kw in ("revenue", "cost", "price", "value", "amount")) else "#,##0"
                    measures.append(MeasureSpec(
                        name=measure_name,
                        expression=f"SUM({table.name}[{col.name}])",
                        format_string=fmt,
                    ))

        # Count measure
        count_name = f"Total{table.name}Count"
        if count_name not in existing:
            measures.append(MeasureSpec(
                name=count_name,
                expression=f"COUNTROWS({table.name})",
                format_string="#,##0",
            ))

    return measures


def generate_tmdl_table(
    spec: TableSpec,
    csv_data: Optional[list[dict]] = None,
) -> str:
    """Generate TMDL content for a table with optional inline DATATABLE data."""
    lines = [f"table {spec.name}"]
    lines.append(f"\tlineageTag: {uuid.uuid4()}")
    lines.append("")

    # Columns
    for col in spec.columns:
        lines.append(f"\tcolumn {col.name}")
        lines.append(f"\t\tdataType: {col.data_type}")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
        lines.append(f"\t\tsummarizeBy: {col.summarize_by}")
        lines.append(f"\t\tsourceColumn: {col.source_column or col.name}")
        if col.data_type == "dateTime":
            lines.append(f'\t\tformatString: yyyy-MM-dd')
        lines.append("")

    # Measures
    for m in spec.measures:
        lines.append(f"\tmeasure {m.name} = {m.expression}")
        lines.append(f"\t\tformatString: {m.format_string}")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
        lines.append("")

    # Partition with DATATABLE
    if csv_data:
        rows = csv_data[:spec.max_rows]
        type_map = {"string": "STRING", "int64": "INTEGER", "double": "DOUBLE",
                    "boolean": "BOOLEAN", "dateTime": "DATETIME", "decimal": "DOUBLE"}

        col_defs = ", ".join(
            f'"{col.name}", {type_map.get(col.data_type, "STRING")}'
            for col in spec.columns
        )

        row_strs = []
        for row in rows:
            vals = []
            for col in spec.columns:
                raw = row.get(col.source_column or col.name, "")
                if col.data_type == "boolean":
                    vals.append("TRUE" if raw.lower() in ("true", "1", "yes") else "FALSE")
                elif col.data_type in ("int64", "double", "decimal"):
                    vals.append(str(raw) if raw else "0")
                else:
                    # Escape quotes in string values
                    escaped = str(raw).replace('"', '""')
                    vals.append(f'"{escaped}"')
            row_strs.append("{" + ", ".join(vals) + "}")

        datatable_expr = f'DATATABLE({col_defs}, {{{", ".join(row_strs)}}})'

        lines.append(f"\tpartition {spec.name} = calculated")
        lines.append(f"\t\tmode: import")
        lines.append(f"\t\tsource = {datatable_expr}")
    else:
        lines.append(f"\tpartition {spec.name} = calculated")
        lines.append(f"\t\tmode: import")
        lines.append(f"\t\tsource = DATATABLE(\"ID\", STRING, {{}})")

    return "\n".join(lines)


def build_model_update(
    model_spec: ModelSpec,
    existing_parts: list[dict],
    csv_data: dict[str, list[dict]] = None,
) -> list[dict]:
    """Build updated TMDL parts from a ModelSpec applied to existing definition parts.

    Returns the complete parts list ready for updateDefinition.
    """
    parts = list(existing_parts)
    csv_data = csv_data or {}

    # Add/replace table TMDL parts
    for table_spec in model_spec.tables:
        path = f"definition/tables/{table_spec.name}.tmdl"
        # Remove existing if present
        parts = [p for p in parts if p["path"] != path]

        data = csv_data.get(table_spec.name)
        tmdl_content = generate_tmdl_table(table_spec, data)

        parts.append({
            "path": path,
            "payload": base64.b64encode(tmdl_content.encode("utf-8")).decode(),
            "payloadType": "InlineBase64",
        })

    # Add relationships to model.tmdl if needed
    if model_spec.relationships:
        model_tmdl_part = next((p for p in parts if p["path"] == "definition/model.tmdl"), None)
        if model_tmdl_part:
            content = base64.b64decode(model_tmdl_part["payload"]).decode("utf-8")
            for rel in model_spec.relationships:
                rel_block = (
                    f"\nrelationship {uuid.uuid4()}\n"
                    f"\tfromTable: {rel.from_table}\n"
                    f"\tfromColumn: {rel.from_column}\n"
                    f"\ttoTable: {rel.to_table}\n"
                    f"\ttoColumn: {rel.to_column}\n"
                )
                content += rel_block
            model_tmdl_part["payload"] = base64.b64encode(content.encode("utf-8")).decode()

    return parts


# ─────────────────────────────────────────────────────────────────────────────
# Compact Page Spec
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VisualSpec:
    """Compact specification for a single visual on a page."""
    template_id: str
    title: str
    bindings: dict[str, list[dict]]  # role_name -> [{"entity": ..., "property": ..., "is_measure": ...}]
    position: tuple[int, int, int, int]  # x, y, w, h
    config: dict = field(default_factory=dict)


def make_donut_composite(
    donut_position: tuple[int, int, int, int],
    donut_title: str,
    donut_category: dict,
    donut_measure: dict,
    center_title: str,
    center_measure: dict,
    center_subtitle: str = "",
    *,
    overlay_w: int = 100,
    overlay_h: int = 44,
    has_title: bool = True,
    has_legend: bool = True,
    title_font_size: int = 18,
) -> list[VisualSpec]:
    """Create a donut + center KPI pair with auto-computed center position.

    Returns a list of 2 VisualSpecs: the donut and its center overlay.
    The center overlay position is computed from the donut bounds using
    the composite geometry rules (accounting for title/legend offsets).
    """
    from pbi_gen.renderer.templates.composites import compute_donut_center

    center_pos = compute_donut_center(
        *donut_position,
        overlay_w=overlay_w,
        overlay_h=overlay_h,
        has_title=has_title,
        has_legend=has_legend,
    )

    donut_spec = VisualSpec(
        template_id="premium_donut",
        title=donut_title,
        bindings={
            "category": [donut_category],
            "values": [donut_measure],
        },
        position=donut_position,
    )

    center_spec = VisualSpec(
        template_id="donut_center_kpi",
        title=center_title,
        bindings={"measure": [center_measure]},
        position=center_pos,
        config={
            "title_color": "#ffffff",
            "title_font_size": title_font_size,
            "title_bold": True,
            "show_background": False,
            "show_border": False,
            "subtitle": center_subtitle,
        },
    )

    return [donut_spec, center_spec]


@dataclass
class PageSpec:
    """Compact specification for a complete dashboard page."""
    page_name: str
    display_name: str
    title: str
    subtitle: str = ""
    nav_items: list[tuple[str, str]] = field(default_factory=list)
    active_nav: str = ""
    slicers: list[dict] = field(default_factory=list)
    visuals: list[VisualSpec] = field(default_factory=list)
    width: int = 1280
    height: int = 720

    # Semantic model reference
    semantic_model_id: str = ""
    semantic_model_name: str = ""


def page_spec_to_shell(spec: PageSpec) -> PageShell:
    """Convert a PageSpec to a PageShell."""
    slicer_refs = [
        FieldRef(entity=s["entity"], property=s["property"], is_measure=False)
        for s in spec.slicers
    ]
    return PageShell(
        page_name=spec.page_name,
        display_name=spec.display_name,
        title=spec.title,
        subtitle=spec.subtitle,
        nav_items=[(label, name) for label, name in spec.nav_items],
        active_nav=spec.active_nav,
        slicers=slicer_refs,
        width=spec.width,
        height=spec.height,
    )


def page_spec_to_bindings(spec: PageSpec) -> list[VisualBinding]:
    """Convert a PageSpec's visuals to VisualBindings."""
    bindings = []
    for v in spec.visuals:
        data_bindings: dict[str, list[FieldRef]] = {}
        for role_name, fields in v.bindings.items():
            data_bindings[role_name] = [
                FieldRef(
                    entity=f["entity"],
                    property=f["property"],
                    is_measure=f.get("is_measure", False),
                )
                for f in fields
            ]
        bindings.append(VisualBinding(
            template_id=v.template_id,
            title=v.title,
            data_bindings=data_bindings,
            position=v.position,
            config_overrides=v.config,
        ))
    return bindings


# ─────────────────────────────────────────────────────────────────────────────
# Preflight Validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationError:
    """A single validation error."""
    level: Literal["error", "warning"]
    category: str  # model, page, binding
    message: str


@dataclass
class PreflightResult:
    """Result of preflight validation."""
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, category: str, message: str):
        self.errors.append(ValidationError(level="error", category=category, message=message))

    def add_warning(self, category: str, message: str):
        self.warnings.append(ValidationError(level="warning", category=category, message=message))

    def summary(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"❌ {len(self.errors)} error(s):")
            for e in self.errors:
                lines.append(f"  [{e.category}] {e.message}")
        if self.warnings:
            lines.append(f"⚠️ {len(self.warnings)} warning(s):")
            for w in self.warnings:
                lines.append(f"  [{w.category}] {w.message}")
        if not self.errors and not self.warnings:
            lines.append("✅ Preflight passed — no issues found")
        return "\n".join(lines)


def validate_model_spec(
    model_spec: ModelSpec,
    csv_data: dict[str, list[dict]] = None,
) -> PreflightResult:
    """Validate a ModelSpec before deployment."""
    result = PreflightResult()
    csv_data = csv_data or {}

    for table in model_spec.tables:
        # Check columns exist
        if not table.columns:
            result.add_error("model", f"Table '{table.name}' has no columns")

        # Check data types are valid
        valid_types = {"string", "int64", "double", "boolean", "dateTime", "decimal"}
        for col in table.columns:
            if col.data_type not in valid_types:
                result.add_error("model", f"Table '{table.name}'.{col.name} has invalid type '{col.data_type}'")

        # Check measures reference valid columns
        for m in table.measures:
            if not m.expression:
                result.add_error("model", f"Measure '{m.name}' on '{table.name}' has empty expression")

    # Check relationship keys exist
    all_table_names = {t.name for t in model_spec.tables}
    for rel in model_spec.relationships:
        from_table = next((t for t in model_spec.tables if t.name == rel.from_table), None)
        to_table = next((t for t in model_spec.tables if t.name == rel.to_table), None)

        if from_table:
            col_names = {c.name for c in from_table.columns}
            if rel.from_column not in col_names:
                result.add_error("model", f"Relationship from '{rel.from_table}.{rel.from_column}' — column not found")

        if to_table:
            col_names = {c.name for c in to_table.columns}
            if rel.to_column not in col_names:
                result.add_error("model", f"Relationship to '{rel.to_table}.{rel.to_column}' — column not found")

        # Check type compatibility
        if from_table and to_table:
            from_col = next((c for c in from_table.columns if c.name == rel.from_column), None)
            to_col = next((c for c in to_table.columns if c.name == rel.to_column), None)
            if from_col and to_col and from_col.data_type != to_col.data_type:
                result.add_warning("model",
                    f"Relationship {rel.from_table}.{rel.from_column} ({from_col.data_type}) → "
                    f"{rel.to_table}.{rel.to_column} ({to_col.data_type}): type mismatch")

    return result


def validate_page_spec(
    spec: PageSpec,
    model: Optional[ModelMetadata] = None,
) -> PreflightResult:
    """Validate a PageSpec before deployment."""
    result = PreflightResult()
    registry = TemplateRegistry.default()

    for i, visual in enumerate(spec.visuals):
        # Check template exists
        try:
            template = registry.get(visual.template_id)
        except KeyError as e:
            result.add_error("page", f"Visual #{i} ({visual.title}): {e}")
            continue

        # Check required data roles are bound
        for role in template.data_roles:
            if role.required and role.name not in visual.bindings:
                result.add_error("page",
                    f"Visual '{visual.title}' ({visual.template_id}): required role '{role.name}' not bound")

        # Check fields exist in model
        if model:
            for role_name, fields in visual.bindings.items():
                for f in fields:
                    entity = f["entity"]
                    prop = f["property"]
                    is_measure = f.get("is_measure", False)

                    table = model.get_table(entity)
                    if not table:
                        result.add_error("page",
                            f"Visual '{visual.title}': entity '{entity}' not found in model")
                        continue

                    if is_measure:
                        measure_names = {m.name for m in table.measures}
                        if prop not in measure_names:
                            result.add_error("page",
                                f"Visual '{visual.title}': measure '{entity}.{prop}' not found")
                    else:
                        col_names = {c.name for c in table.columns}
                        if prop not in col_names:
                            result.add_error("page",
                                f"Visual '{visual.title}': column '{entity}.{prop}' not found")

        # Check canvas bounds
        x, y, w, h = visual.position
        if x + w > spec.width:
            result.add_warning("page",
                f"Visual '{visual.title}' exceeds canvas width: x={x} + w={w} > {spec.width}")
        if y + h > spec.height:
            result.add_warning("page",
                f"Visual '{visual.title}' exceeds canvas height: y={y} + h={h} > {spec.height}")

    # Check for duplicate visual positions (exact overlap)
    positions = [v.position for v in spec.visuals]
    for i, p1 in enumerate(positions):
        for j, p2 in enumerate(positions):
            if i >= j:
                continue
            # Check complete overlap (not partial — partial is intentional e.g. donut+center KPI)
            if p1 == p2:
                result.add_warning("page",
                    f"Visuals #{i} and #{j} have identical positions")

    return result


def run_preflight(
    page_spec: PageSpec,
    model_spec: Optional[ModelSpec] = None,
    model_metadata: Optional[ModelMetadata] = None,
    csv_data: dict[str, list[dict]] = None,
) -> PreflightResult:
    """Run unified preflight validation on both model and page specs."""
    result = PreflightResult()

    # Model validation
    if model_spec:
        model_result = validate_model_spec(model_spec, csv_data)
        result.errors.extend(model_result.errors)
        result.warnings.extend(model_result.warnings)

    # Page validation
    page_result = validate_page_spec(page_spec, model_metadata)
    result.errors.extend(page_result.errors)
    result.warnings.extend(page_result.warnings)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Deployment Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TimingRecord:
    """Records timing for each deployment phase."""
    phases: dict[str, float] = field(default_factory=dict)

    def record(self, phase: str, elapsed: float):
        self.phases[phase] = elapsed

    @property
    def total(self) -> float:
        return sum(self.phases.values())

    def summary(self) -> str:
        lines = [f"Total: {self.total:.1f}s"]
        for phase, elapsed in self.phases.items():
            lines.append(f"  {phase}: {elapsed:.1f}s")
        return "\n".join(lines)


@dataclass
class DeployResult:
    """Result of a deployment."""
    success: bool
    report_id: Optional[str] = None
    screenshot_path: Optional[str] = None
    timing: TimingRecord = field(default_factory=TimingRecord)
    errors: list[str] = field(default_factory=list)
    preflight: Optional[PreflightResult] = None


def deploy_from_page_spec(
    spec: PageSpec,
    workspace_id: str,
    headers: dict,
    *,
    visual_archives: Optional[dict[str, tuple[bytes, bytes]]] = None,
    evidence_dir: Optional[Path] = None,
    screenshot: bool = True,
    fabric_api_base: str = "https://api.fabric.microsoft.com/v1",
) -> DeployResult:
    """Deploy a complete dashboard page from a compact PageSpec.

    This is the optimised single-call deployment path.
    """
    timing = TimingRecord()
    result = DeployResult(success=False, timing=timing)

    # Phase 1: Build page
    t0 = time.time()
    shell = page_spec_to_shell(spec)
    bindings = page_spec_to_bindings(spec)

    tokens = DesignTokens()
    registry = TemplateRegistry.default()

    builder = PageBuilder(
        shell=shell,
        tokens=tokens,
        registry=registry,
        semantic_model_id=spec.semantic_model_id,
        semantic_model_name=spec.semantic_model_name,
        report_name=spec.display_name,
    )

    for binding in bindings:
        builder.add_visual(binding)

    # Load custom visual archives if not provided
    if visual_archives is None:
        visual_archives = _auto_load_visual_archives(builder.custom_visual_packages())

    parts = builder.build_pbir_parts_with_visuals(visual_archives)
    timing.record("pbir_generation", time.time() - t0)

    # Phase 2: Delete existing report
    t0 = time.time()
    report_name = spec.display_name
    r = requests.get(
        f"{fabric_api_base}/workspaces/{workspace_id}/items?type=Report",
        headers=headers, timeout=30,
    )
    for item in r.json().get("value", []):
        if item["displayName"] == report_name:
            requests.delete(
                f"{fabric_api_base}/workspaces/{workspace_id}/items/{item['id']}",
                headers=headers, timeout=30,
            )
            time.sleep(3)
            break
    timing.record("cleanup", time.time() - t0)

    # Phase 3: Create report
    t0 = time.time()
    r = requests.post(
        f"{fabric_api_base}/workspaces/{workspace_id}/items",
        headers=headers,
        json={"displayName": report_name, "type": "Report", "definition": {"parts": parts}},
        timeout=60,
    )

    if r.status_code == 202:
        loc = r.headers.get("Location", "")
        for _ in range(20):
            time.sleep(2)
            poll = requests.get(loc, headers=headers, timeout=30)
            data = poll.json()
            if data.get("status") == "Succeeded":
                break
            elif data.get("status") == "Failed":
                result.errors.append(f"Create failed: {data.get('error', {}).get('message', '')[:400]}")
                return result
    elif r.status_code not in (200, 201):
        result.errors.append(f"Create error {r.status_code}: {r.text[:300]}")
        return result

    timing.record("rest_create", time.time() - t0)

    # Phase 4: Get report ID
    t0 = time.time()
    time.sleep(2)
    r = requests.get(
        f"{fabric_api_base}/workspaces/{workspace_id}/items?type=Report",
        headers=headers, timeout=30,
    )
    report_id = next(
        (i["id"] for i in r.json().get("value", []) if i["displayName"] == report_name),
        None,
    )
    if not report_id:
        result.errors.append("Could not find report after creation")
        return result

    result.report_id = report_id
    timing.record("report_lookup", time.time() - t0)

    # Phase 5: Screenshot (optional)
    if screenshot and evidence_dir:
        t0 = time.time()
        try:
            screenshot_path = _capture_screenshot(
                workspace_id, report_id, spec.semantic_model_id,
                shell.page_name, headers, evidence_dir,
            )
            result.screenshot_path = screenshot_path
        except Exception as e:
            result.errors.append(f"Screenshot failed: {e}")
        timing.record("screenshot", time.time() - t0)

    result.success = True
    return result


def _auto_load_visual_archives(guids: list[str]) -> dict[str, tuple[bytes, bytes]]:
    """Auto-detect and load custom visual archives from the project's custom-visuals directory."""
    archives: dict[str, tuple[bytes, bytes]] = {}
    custom_vis_root = Path(__file__).parent.parent.parent.parent.parent / "custom-visuals"

    # Map GUIDs to folder names
    guid_to_folder = {v: k for k, v in CUSTOM_VISUAL_GUIDS.items()}
    folder_name_map = {
        "kpi": "premiumKPI",
        "area_chart": "premiumAreaChart",
        "gauge": "premiumGauge",
        "insights": "premiumInsights",
        "waterfall": "premiumWaterfall",
    }

    for guid in guids:
        key = guid_to_folder.get(guid)
        if not key:
            continue
        folder = folder_name_map.get(key)
        if not folder:
            continue

        pbiviz_path = custom_vis_root / folder / "dist" / f"{guid}.1.0.0.0.pbiviz"
        if pbiviz_path.exists():
            with zipfile.ZipFile(io.BytesIO(pbiviz_path.read_bytes())) as z:
                pkg = z.read("package.json")
                res = z.read(f"resources/{guid}.pbiviz.json")
                archives[guid] = (pkg, res)

    return archives


def _capture_screenshot(
    workspace_id: str,
    report_id: str,
    dataset_id: str,
    page_name: str,
    headers: dict,
    evidence_dir: Path,
) -> str:
    """Capture a screenshot using embed token + Playwright."""
    from pbi_gen.critic.screenshot import _get_embed_url

    # Get embed URL
    embed_url = None
    for _ in range(3):
        embed_url = _get_embed_url(workspace_id, report_id, headers)
        if embed_url:
            break
        time.sleep(2)

    if not embed_url:
        raise RuntimeError("Could not get embed URL")

    # Generate embed token
    embed_body = {"datasets": [{"id": dataset_id}], "reports": [{"id": report_id}]}
    er = requests.post(
        "https://api.powerbi.com/v1.0/myorg/GenerateToken",
        headers=headers, json=embed_body, timeout=30,
    )
    if er.status_code != 200:
        raise RuntimeError(f"Embed token failed: {er.status_code}")
    embed_token = er.json()["token"]

    # Render
    from playwright.sync_api import sync_playwright

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>PBI</title>'
        '<script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>'
        '<style>*{margin:0;padding:0}body{overflow:hidden;background:#0f1623}#r{width:1280px;height:720px}</style>'
        '</head><body><div id="r"></div><script>'
        'const m=window["powerbi-client"].models;'
        f'const c={{type:"report",tokenType:m.TokenType.Embed,accessToken:"{embed_token}",'
        f'embedUrl:"{embed_url}",id:"{report_id}",pageName:"{page_name}",'
        'settings:{navContentPaneEnabled:false,filterPaneEnabled:false,'
        'background:m.BackgroundType.Transparent,'
        'layoutType:m.LayoutType.Custom,customLayout:{displayOption:m.DisplayOption.FitToPage,'
        'pageSize:{type:m.PageSizeType.Custom,width:1280,height:720}}}};'
        'const r=powerbi.embed(document.getElementById("r"),c);'
        'r.on("rendered",()=>{document.title="RENDERED"});'
        'r.on("error",e=>{document.title="ERROR:"+JSON.stringify(e.detail)});'
        '</script></body></html>'
    )

    evidence_dir.mkdir(parents=True, exist_ok=True)
    html_path = evidence_dir / "_embed.html"
    html_path.write_text(html, encoding="utf-8")
    screenshot_path = evidence_dir / "dashboard.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"file:///{html_path.resolve()}")
        try:
            page.wait_for_function(
                'document.title.startsWith("RENDERED") || document.title.startsWith("ERROR")',
                timeout=45000,
            )
        except Exception:
            pass
        page.wait_for_timeout(4000)
        page.screenshot(path=str(screenshot_path))
        browser.close()

    html_path.unlink(missing_ok=True)
    return str(screenshot_path)


def deploy_model_update(
    workspace_id: str,
    model_id: str,
    parts: list[dict],
    headers: dict,
    fabric_api_base: str = "https://api.fabric.microsoft.com/v1",
) -> tuple[bool, str]:
    """Deploy a semantic model update via the Fabric REST API.

    Returns (success, message).
    """
    r = requests.post(
        f"{fabric_api_base}/workspaces/{workspace_id}/semanticModels/{model_id}/updateDefinition",
        headers=headers,
        json={"definition": {"parts": parts}},
        timeout=60,
    )

    if r.status_code == 202:
        loc = r.headers.get("Location", "")
        for _ in range(30):
            time.sleep(2)
            poll = requests.get(loc, headers=headers, timeout=30)
            data = poll.json()
            if data.get("status") == "Succeeded":
                return True, "Model updated successfully"
            elif data.get("status") == "Failed":
                msg = json.dumps(data.get("error", {}), indent=2)[:500]
                return False, f"Model update failed: {msg}"
        return False, "Model update timed out"
    elif r.status_code == 200:
        return True, "Model updated"
    else:
        return False, f"Error {r.status_code}: {r.text[:300]}"



# ─────────────────────────────────────────────────────────────────────────────
# Reference-to-Spec Mapping
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReferenceVisual:
    """Describes a visual element from a reference/mockup."""
    intent: str  # analytical intent (from INTENT_TO_TEMPLATE keys)
    title: str
    row: Literal["kpi", "hero", "bottom"]  # page region
    measures: list[str] = field(default_factory=list)  # required measure names
    dimensions: list[str] = field(default_factory=list)  # required dimension names
    needs_time_axis: bool = False
    prefer_horizontal: bool = False
    width_fraction: float = 0.5  # fraction of available row width


@dataclass
class ReferenceSpec:
    """Describes the full requirements inferred from a reference/mockup."""
    title: str
    subtitle: str = ""
    kpi_count: int = 4
    hero_count: int = 1
    bottom_count: int = 3
    visuals: list[ReferenceVisual] = field(default_factory=list)
    required_measures: list[str] = field(default_factory=list)
    required_dimensions: list[str] = field(default_factory=list)
    needs_date_relationship: bool = False
    nav_label: str = ""
    slicer_fields: list[str] = field(default_factory=list)


# Standard page layout grid (matches existing Executive/Financial/Customer pages)
STANDARD_LAYOUT = {
    "nav_width": 140,
    "content_x": 155,
    "content_width": 1115,  # 1280 - 140 - 15 margin - 10 right margin
    "kpi_y": 70,
    "kpi_h": 100,
    "hero_y": 180,
    "hero_h": 240,
    "bottom_y": 430,
    "bottom_h": 240,
    "gutter": 10,
}


def reference_to_page_spec(
    ref: ReferenceSpec,
    model: ModelMetadata,
    *,
    nav_items: list[tuple[str, str]] = None,
    active_nav: str = "",
    semantic_model_id: str = "",
    semantic_model_name: str = "",
    page_name: str = "",
) -> PageSpec:
    """Convert a ReferenceSpec + model metadata into a deployable PageSpec.

    Maps reference visual intents to existing templates and positions them
    on the standard page grid.
    """
    layout = STANDARD_LAYOUT
    cx = layout["content_x"]
    cw = layout["content_width"]
    gutter = layout["gutter"]

    visuals: list[VisualSpec] = []

    # Group reference visuals by row
    kpi_visuals = [v for v in ref.visuals if v.row == "kpi"]
    hero_visuals = [v for v in ref.visuals if v.row == "hero"]
    bottom_visuals = [v for v in ref.visuals if v.row == "bottom"]

    # ── KPI row ──
    if kpi_visuals:
        kpi_count = len(kpi_visuals)
        kpi_w = (cw - (kpi_count - 1) * gutter) // kpi_count
        for i, kv in enumerate(kpi_visuals):
            x = cx + i * (kpi_w + gutter)
            measure_field = _resolve_measure(kv.measures[0] if kv.measures else "", model)
            visuals.append(VisualSpec(
                template_id="premium_kpi",
                title=kv.title,
                bindings={"measure": [measure_field]},
                position=(x, layout["kpi_y"], kpi_w, layout["kpi_h"]),
            ))

    # ── Hero row ──
    if hero_visuals:
        if len(hero_visuals) == 1:
            # Single hero takes ~57% width; remaining space for composition
            hero_w = int(cw * 0.57)
            hv = hero_visuals[0]
            template_id = select_template(
                hv.intent,
                has_time_axis=hv.needs_time_axis,
                prefer_horizontal=hv.prefer_horizontal,
            )
            bindings = _resolve_visual_bindings(hv, model, template_id)
            visuals.append(VisualSpec(
                template_id=template_id,
                title=hv.title,
                bindings=bindings,
                position=(cx, layout["hero_y"], hero_w, layout["hero_h"]),
            ))
        else:
            # Multiple hero visuals split the row
            total_frac = sum(v.width_fraction for v in hero_visuals)
            x_offset = cx
            for hv in hero_visuals:
                w = int(cw * hv.width_fraction / total_frac) - gutter
                template_id = select_template(
                    hv.intent,
                    has_time_axis=hv.needs_time_axis,
                    prefer_horizontal=hv.prefer_horizontal,
                )
                bindings = _resolve_visual_bindings(hv, model, template_id)
                visuals.append(VisualSpec(
                    template_id=template_id,
                    title=hv.title,
                    bindings=bindings,
                    position=(x_offset, layout["hero_y"], w, layout["hero_h"]),
                ))
                x_offset += w + gutter

    # If there's a composition visual paired with the hero (like donut)
    # check for remaining hero-row space
    composition_visuals = [v for v in ref.visuals if v.intent == "composition_share" and v.row == "hero"]
    if composition_visuals and len(hero_visuals) == 1:
        hero_w = int(cw * 0.57)
        comp_x = cx + hero_w + gutter
        comp_w = cw - hero_w - gutter
        cv = composition_visuals[0]
        bindings = _resolve_visual_bindings(cv, model, "premium_donut")
        visuals.append(VisualSpec(
            template_id="premium_donut",
            title=cv.title,
            bindings=bindings,
            position=(comp_x, layout["hero_y"], comp_w, layout["hero_h"]),
        ))

    # ── Bottom row ──
    if bottom_visuals:
        n = len(bottom_visuals)
        bw = (cw - (n - 1) * gutter) // n
        for i, bv in enumerate(bottom_visuals):
            x = cx + i * (bw + gutter)
            template_id = select_template(
                bv.intent,
                has_time_axis=bv.needs_time_axis,
                prefer_horizontal=bv.prefer_horizontal,
            )
            bindings = _resolve_visual_bindings(bv, model, template_id)
            visuals.append(VisualSpec(
                template_id=template_id,
                title=bv.title,
                bindings=bindings,
                position=(x, layout["bottom_y"], bw, layout["bottom_h"]),
            ))

    # Slicers
    slicer_dicts = []
    for sf in ref.slicer_fields:
        resolved = _resolve_dimension(sf, model)
        if resolved:
            slicer_dicts.append(resolved)

    return PageSpec(
        page_name=page_name or ref.title.lower().replace(" ", "_"),
        display_name=ref.title,
        title=ref.title,
        subtitle=ref.subtitle,
        nav_items=nav_items or [
            ("\U0001f3e0 Overview", "overview"),
            ("\U0001f4b0 Financial", "financial"),
            ("\U0001f465 Customers", "customers"),
            ("\U0001f4e6 Products", "products"),
        ],
        active_nav=active_nav or page_name or ref.title.lower().replace(" ", "_"),
        slicers=slicer_dicts,
        visuals=visuals,
        semantic_model_id=semantic_model_id,
        semantic_model_name=semantic_model_name,
    )


def _resolve_measure(name: str, model: ModelMetadata) -> dict:
    """Find a measure in the model by name (fuzzy)."""
    all_measures = model.all_measures()

    # Exact match
    for m in all_measures:
        if m.name == name:
            return {"entity": m.table, "property": m.name, "is_measure": True}

    # Case-insensitive match
    for m in all_measures:
        if m.name.lower() == name.lower():
            return {"entity": m.table, "property": m.name, "is_measure": True}

    # Partial match
    for m in all_measures:
        if name.lower() in m.name.lower() or m.name.lower() in name.lower():
            return {"entity": m.table, "property": m.name, "is_measure": True}

    # Fallback: first measure
    if all_measures:
        m = all_measures[0]
        return {"entity": m.table, "property": m.name, "is_measure": True}

    return {"entity": "Unknown", "property": name, "is_measure": True}


def _resolve_dimension(name: str, model: ModelMetadata) -> Optional[dict]:
    """Find a dimension column in the model by name."""
    for table in model.tables:
        for col in table.categorical_columns:
            if col.name == name or col.name.lower() == name.lower():
                return {"entity": table.name, "property": col.name}
        for col in table.columns:
            if col.name == name:
                return {"entity": table.name, "property": col.name}
    return None


def _resolve_visual_bindings(
    rv: ReferenceVisual,
    model: ModelMetadata,
    template_id: str,
) -> dict[str, list[dict]]:
    """Resolve data bindings for a reference visual against the model."""
    registry = TemplateRegistry.default()
    template = registry.get(template_id)

    bindings: dict[str, list[dict]] = {}

    for role in template.data_roles:
        if role.kind == "Measure":
            # Use specified measures or find suitable ones
            measures = rv.measures if rv.measures else []
            field_refs = []
            for m_name in measures:
                field_refs.append(_resolve_measure(m_name, model))
            if not field_refs:
                # Pick a relevant measure
                all_m = model.all_measures()
                if all_m:
                    field_refs.append({
                        "entity": all_m[0].table,
                        "property": all_m[0].name,
                        "is_measure": True,
                    })
            if field_refs:
                bindings[role.name] = field_refs

        elif role.kind == "Grouping":
            # Use specified dimensions or find suitable ones
            dimensions = rv.dimensions if rv.dimensions else []
            field_refs = []
            for d_name in dimensions:
                resolved = _resolve_dimension(d_name, model)
                if resolved:
                    field_refs.append(resolved)
            if not field_refs:
                # Pick a categorical column
                for table in model.tables:
                    for col in table.categorical_columns:
                        field_refs.append({"entity": table.name, "property": col.name})
                        break
                    if field_refs:
                        break
            if field_refs:
                bindings[role.name] = field_refs

    return bindings
