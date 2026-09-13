"""Data models for field mapping."""

from typing import Optional, Any, Dict
from dataclasses import dataclass, asdict, field as dataclass_field
from enum import Enum


class MatchType(str, Enum):
    """Type of match found."""
    LEGACY = "legacy"  # Matched against approved historical mappings
    DIRECT = "direct"  # Matched directly against target field catalog


@dataclass
class SourceField:
    """A source field to be mapped."""
    name: str
    table: str
    data_type: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    unique_values_count: Optional[int] = None
    
    def to_embedding_text(self) -> str:
        """Convert to text for embedding."""
        parts = [f"Field: {self.name}", f"Table: {self.table}"]
        if self.data_type:
            parts.append(f"Type: {self.data_type}")
        if self.max_length:
            parts.append(f"MaxLen: {self.max_length}")
        if self.min_value is not None or self.max_value is not None:
            parts.append(f"Range: {self.min_value}-{self.max_value}")
        return ", ".join(parts)


@dataclass
class TargetField:
    """A target field available for mapping."""
    name: str
    table: str
    data_type: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    
    def to_embedding_text(self) -> str:
        """Convert to text for embedding."""
        parts = [f"Field: {self.name}", f"Table: {self.table}"]
        if self.data_type:
            parts.append(f"Type: {self.data_type}")
        if self.max_length:
            parts.append(f"MaxLen: {self.max_length}")
        if self.min_value is not None or self.max_value is not None:
            parts.append(f"Range: {self.min_value}-{self.max_value}")
        return ", ".join(parts)


@dataclass
class ApprovedMapping:
    """A previously approved mapping from source to target."""
    source_name: str
    source_table: str
    target_name: str
    target_table: str
    source_data_type: Optional[str] = None
    target_data_type: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    
    def to_source_field(self) -> SourceField:
        """Convert to SourceField for embedding."""
        return SourceField(
            name=self.source_name,
            table=self.source_table,
            data_type=self.source_data_type
        )
    
    def to_target_field(self) -> TargetField:
        """Convert to TargetField."""
        return TargetField(
            name=self.target_name,
            table=self.target_table,
            data_type=self.target_data_type
        )


@dataclass
class Match:
    """A proposed field match."""
    target_field: str
    target_table: str
    confidence_score: float
    match_type: MatchType
    target_data_type: Optional[str] = None
    supporting_metadata: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_field": self.target_field,
            "target_table": self.target_table,
            "confidence_score": self.confidence_score,
            "match_type": self.match_type.value,
            "target_data_type": self.target_data_type,
            "supporting_metadata": self.supporting_metadata,
        }


@dataclass
class FieldMappingProposal:
    """A complete mapping proposal for a source field."""
    source_field: str
    source_table: str
    source_data_type: Optional[str]
    legacy_matches: list[Match]
    direct_matches: list[Match]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_field": self.source_field,
            "source_table": self.source_table,
            "source_data_type": self.source_data_type,
            "legacy_matches": [m.to_dict() for m in self.legacy_matches],
            "direct_matches": [m.to_dict() for m in self.direct_matches],
        }
