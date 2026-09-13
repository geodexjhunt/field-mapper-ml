"""Field Mapper ML - Semantic field mapping for data migration."""

__version__ = "0.1.0"

from field_mapper.mapper import FieldMapper
from field_mapper.models import SourceField, TargetField, ApprovedMapping
from field_mapper.loaders import (
    ApprovedMappingLoader,
    MSSQLLoader,
    MSSQLMappingLoader,
    DatabaseConnectionError,
    InvalidTableReferenceError,
    MissingFieldMetadataError,
    MalformedMappingFileError,
)

__all__ = [
    "FieldMapper",
    "SourceField",
    "TargetField",
    "ApprovedMapping",
    "ApprovedMappingLoader",
    "MSSQLLoader",
    "MSSQLMappingLoader",
    "DatabaseConnectionError",
    "InvalidTableReferenceError",
    "MissingFieldMetadataError",
    "MalformedMappingFileError",
]
