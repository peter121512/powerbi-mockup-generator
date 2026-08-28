"""Provider-neutral data context for the conversational design workflow (Stage 13).

`DataContext` is the single structured artifact produced from any input mechanism
(spreadsheet upload, URL/file, or written description). The image-mockup prompt
and feasibility classifier consume this artifact — never raw datasets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FieldType(str, Enum):
    """Inferred logical type of a field."""

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class FieldRole(str, Enum):
    """Likely analytical role of a field."""

    MEASURE = "measure"
    DIMENSION = "dimension"
    DATE = "date"
    IDENTIFIER = "identifier"
    UNKNOWN = "unknown"


@dataclass
class FieldProfile:
    """Lightweight profile of a single column/field."""

    name: str
    entity: str = ""  # source table/sheet name
    field_type: FieldType = FieldType.UNKNOWN
    role: FieldRole = FieldRole.UNKNOWN
    sample_values: list[str] = field(default_factory=list)
    distinct_count: Optional[int] = None
    null_ratio: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entity": self.entity,
            "type": self.field_type.value,
            "role": self.role.value,
            "sample_values": self.sample_values[:5],
            "distinct_count": self.distinct_count,
            "null_ratio": self.null_ratio,
        }


@dataclass
class DataSource:
    """A source contributing fields to the context."""

    name: str
    kind: str  # "upload" | "url" | "description"
    location: str = ""  # path or URL (never secrets)
    row_count: Optional[int] = None
    sheet_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "location": self.location,
            "row_count": self.row_count,
            "sheet_names": self.sheet_names,
        }


@dataclass
class DataContext:
    """Structured, provider-neutral summary of the user's data for design.

    Produced from uploads, URLs, or descriptions. Deliberately lightweight — it
    is NOT a full semantic model.
    """

    sources: list[DataSource] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    fields: list[FieldProfile] = field(default_factory=list)
    candidate_measures: list[str] = field(default_factory=list)
    candidate_dimensions: list[str] = field(default_factory=list)
    date_fields: list[str] = field(default_factory=list)
    relationships: list[dict[str, str]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    context_id: str = ""

    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "sources": [s.to_dict() for s in self.sources],
            "entities": self.entities,
            "fields": [f.to_dict() for f in self.fields],
            "candidate_measures": self.candidate_measures,
            "candidate_dimensions": self.candidate_dimensions,
            "date_fields": self.date_fields,
            "relationships": self.relationships,
            "assumptions": self.assumptions,
            "confidence": self.confidence,
        }

    def summary_for_prompt(self) -> str:
        """Compact text summary for the image-generation prompt (no raw data)."""
        lines: list[str] = []
        if self.entities:
            lines.append(f"Entities: {', '.join(self.entities)}")
        if self.candidate_measures:
            lines.append(f"Measures: {', '.join(self.candidate_measures[:12])}")
        if self.candidate_dimensions:
            lines.append(f"Dimensions: {', '.join(self.candidate_dimensions[:12])}")
        if self.date_fields:
            lines.append(f"Date fields: {', '.join(self.date_fields[:4])}")
        if self.assumptions:
            lines.append(f"Assumptions: {'; '.join(self.assumptions[:6])}")
        lines.append(f"Data-context confidence: {self.confidence:.2f}")
        return "\n".join(lines)
