"""Approved mapping loaders for JSON and CSV sources."""

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from field_mapper.models import ApprovedMapping


class MalformedMappingFileError(ValueError):
    """Raised when a mapping file cannot be parsed into approved mappings."""


class ApprovedMappingLoader:
    """Load approved mappings from JSON or CSV files."""

    REQUIRED_FIELDS = (
        "source_name",
        "source_table",
        "target_name",
        "target_table",
    )

    def load(
        self,
        filepath: str,
        file_type: Optional[str] = None,
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[ApprovedMapping]:
        """Load approved mappings from a file."""
        path = Path(filepath)
        loader_type = (file_type or path.suffix.lstrip(".")).lower()

        if loader_type == "json":
            return self.load_json(str(path), field_mapping=field_mapping)
        if loader_type == "csv":
            return self.load_csv(str(path), field_mapping=field_mapping)

        raise MalformedMappingFileError(
            f"Unsupported mapping file type: {loader_type or 'unknown'}"
        )

    def load_json(
        self,
        filepath: str,
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[ApprovedMapping]:
        """Load approved mappings from a JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
        except FileNotFoundError as exc:
            raise MalformedMappingFileError(
                f"Mapping file not found: {filepath}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise MalformedMappingFileError(
                f"Malformed JSON mapping file: {filepath}"
            ) from exc
        except OSError as exc:
            raise MalformedMappingFileError(
                f"Unable to read mapping file: {filepath}"
            ) from exc

        if isinstance(data, dict):
            if "mappings" not in data:
                raise MalformedMappingFileError(
                    "JSON mapping files with object payloads must contain a "
                    "'mappings' array."
                )
            data = data["mappings"]

        if not isinstance(data, list):
            raise MalformedMappingFileError(
                "JSON mapping files must contain a list of mappings or a "
                "'mappings' array."
            )

        return self._records_to_mappings(data, field_mapping=field_mapping)

    def load_csv(
        self,
        filepath: str,
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[ApprovedMapping]:
        """Load approved mappings from a CSV file."""
        try:
            with open(filepath, "r", encoding="utf-8", newline="") as file_handle:
                reader = csv.DictReader(file_handle)
                if not reader.fieldnames:
                    raise MalformedMappingFileError(
                        f"CSV mapping file is missing headers: {filepath}"
                    )
                required_headers = [
                    field_mapping.get(field_name, field_name)
                    if field_mapping else field_name
                    for field_name in self.REQUIRED_FIELDS
                ]
                records = []
                for row_number, record in enumerate(reader, start=2):
                    if (
                        None in record
                        or any(record.get(header) is None for header in required_headers)
                    ):
                        raise MalformedMappingFileError(
                            f"Malformed CSV mapping row at line {row_number}: {filepath}"
                        )
                    records.append(record)
        except FileNotFoundError as exc:
            raise MalformedMappingFileError(
                f"Mapping file not found: {filepath}"
            ) from exc
        except csv.Error as exc:
            raise MalformedMappingFileError(
                f"Malformed CSV mapping file: {filepath}"
            ) from exc
        except OSError as exc:
            raise MalformedMappingFileError(
                f"Unable to read mapping file: {filepath}"
            ) from exc

        return self._records_to_mappings(records, field_mapping=field_mapping)

    def _records_to_mappings(
        self,
        records: Iterable[Dict[str, str]],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> List[ApprovedMapping]:
        """Convert dictionaries into ApprovedMapping models."""
        normalized_mappings = []
        for record in records:
            normalized_mappings.append(
                ApprovedMapping(**self._normalize_record(record, field_mapping))
            )
        return normalized_mappings

    def _normalize_record(
        self,
        record: Dict[str, str],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Normalize a file record into ApprovedMapping constructor fields."""
        normalized = {}
        model_fields = ApprovedMapping.__dataclass_fields__.keys()

        for model_field in model_fields:
            source_field = field_mapping.get(model_field, model_field) if field_mapping else model_field
            if source_field in record and record[source_field] not in (None, ""):
                normalized[model_field] = record[source_field]

        missing_fields = [
            field_name
            for field_name in self.REQUIRED_FIELDS
            if not normalized.get(field_name)
        ]
        if missing_fields:
            raise MalformedMappingFileError(
                "Mapping record is missing required fields: "
                + ", ".join(missing_fields)
            )

        return normalized
