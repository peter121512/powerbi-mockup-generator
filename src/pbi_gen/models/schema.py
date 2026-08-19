"""Data models for pbi_gen dashboard specifications."""

from dataclasses import dataclass, field


@dataclass
class ColumnSpec:
    """Specification for a table column."""

    name: str
    dtype: str  # TEXT, INTEGER, REAL, DATE
    description: str = ""
    is_key: bool = False


@dataclass
class TableSpec:
    """Specification for a database table."""

    name: str
    columns: list[ColumnSpec] = field(default_factory=list)


@dataclass
class FieldRef:
    """Reference to a table column for use in visual bindings."""

    table: str
    column: str
    aggregate: str = ""  # Sum, Count, Average, Min, Max, or empty for no aggregation


@dataclass
class VisualSpec:
    """Specification for a report visual."""

    visual_type: str  # barChart, lineChart, card, table, donutChart, slicer, funnel, treemap, map
    title: str
    description: str = ""
    category_fields: list[FieldRef] = field(default_factory=list)
    value_fields: list[FieldRef] = field(default_factory=list)
    series_field: FieldRef | None = None


@dataclass
class DashboardSpec:
    """Complete specification for a dashboard project."""

    title: str
    description: str
    tables: list[TableSpec]
    relationships: list[dict] = field(default_factory=list)
    measures: list[dict] = field(default_factory=list)
    visuals: list[VisualSpec] = field(default_factory=list)
    sample_rows: int = 20
