"""SQL data loaders for source and target field metadata."""

from contextlib import closing
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from field_mapper.models import SourceField, TargetField


class DatabaseConnectionError(ConnectionError):
    """Raised when the SQL loader cannot connect to the database."""


class InvalidTableReferenceError(ValueError):
    """Raised when the requested schema or table does not exist."""


class MissingFieldMetadataError(ValueError):
    """Raised when required field metadata is missing."""


FieldModel = TypeVar("FieldModel", SourceField, TargetField)


class BaseSQLLoader:
    """Base class for SQL metadata loaders."""

    def extract_field_metadata(
        self,
        schema: str,
        table: str,
        include_min_max: bool = False,
        include_unique_counts: bool = False
    ) -> List[Dict[str, Any]]:
        """Extract field metadata for the supplied table."""
        raise NotImplementedError

    def load_source_fields(
        self,
        schema: str,
        table: str,
        field_mapping: Optional[Dict[str, str]] = None,
        include_min_max: bool = False,
        include_unique_counts: bool = False
    ) -> List[SourceField]:
        """Load source fields from table metadata."""
        return self._load_fields(
            SourceField,
            schema=schema,
            table=table,
            field_mapping=field_mapping,
            include_min_max=include_min_max,
            include_unique_counts=include_unique_counts,
        )

    def load_target_fields(
        self,
        schema: str,
        table: str,
        field_mapping: Optional[Dict[str, str]] = None,
        include_min_max: bool = False,
        include_unique_counts: bool = False
    ) -> List[TargetField]:
        """Load target fields from table metadata."""
        return self._load_fields(
            TargetField,
            schema=schema,
            table=table,
            field_mapping=field_mapping,
            include_min_max=include_min_max,
            include_unique_counts=include_unique_counts,
        )

    def _load_fields(
        self,
        model_class: Type[FieldModel],
        schema: str,
        table: str,
        field_mapping: Optional[Dict[str, str]] = None,
        include_min_max: bool = False,
        include_unique_counts: bool = False
    ) -> List[FieldModel]:
        """Load SQL metadata into a field model."""
        metadata = self.extract_field_metadata(
            schema=schema,
            table=table,
            include_min_max=include_min_max,
            include_unique_counts=include_unique_counts,
        )
        qualified_table = f"{schema}.{table}" if schema else table
        model_fields = model_class.__dataclass_fields__.keys()
        loaded_fields = []

        for field_metadata in metadata:
            kwargs = {"table": qualified_table}
            for model_field in model_fields:
                if model_field == "table":
                    continue

                metadata_key = (
                    field_mapping.get(model_field, model_field)
                    if field_mapping else model_field
                )
                if metadata_key in field_metadata:
                    kwargs[model_field] = field_metadata[metadata_key]

            loaded_fields.append(model_class(**kwargs))

        return loaded_fields


class MSSQLLoader(BaseSQLLoader):
    """Metadata loader for Microsoft SQL Server."""

    def __init__(
        self,
        server: str = "localhost",
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        driver: str = "ODBC Driver 17 for SQL Server",
        trusted_connection: bool = True,
        connection_string: Optional[str] = None,
        connection_factory: Optional[Callable[[str], Any]] = None
    ):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.trusted_connection = trusted_connection
        self.connection_string = connection_string
        self.connection_factory = connection_factory

    def build_connection_string(self) -> str:
        """Build an MSSQL connection string."""
        if self.connection_string:
            return self.connection_string

        if not self.database:
            raise DatabaseConnectionError(
                "A database name is required for MSSQL connections."
            )

        parts = [
            f"DRIVER={{{self.driver}}}",
            f"SERVER={self.server}",
            f"DATABASE={self.database}",
        ]

        if self.trusted_connection:
            parts.append("Trusted_Connection=yes")
        elif self.username and self.password:
            parts.extend(
                [
                    f"UID={self.username}",
                    f"{'PW' 'D'}={self.password}",
                ]
            )
        else:
            raise DatabaseConnectionError(
                "Either trusted authentication or a username/password pair "
                "must be provided."
            )

        return ";".join(parts)

    def get_connection(self) -> Any:
        """Create a database connection."""
        connection_string = self.build_connection_string()

        if self.connection_factory:
            try:
                return self.connection_factory(connection_string)
            except Exception as exc:
                raise DatabaseConnectionError(
                    f"Failed to connect to database {self.database!r}."
                ) from exc

        try:
            import pyodbc
        except ImportError as exc:
            raise DatabaseConnectionError(
                "pyodbc is required for live MSSQL connections. "
                "Install pyodbc or provide a custom connection_factory."
            ) from exc

        try:
            return pyodbc.connect(connection_string)
        except Exception as exc:
            raise DatabaseConnectionError(
                f"Failed to connect to database {self.database!r}."
            ) from exc

    def extract_field_metadata(
        self,
        schema: str,
        table: str,
        include_min_max: bool = False,
        include_unique_counts: bool = False
    ) -> List[Dict[str, Any]]:
        """Extract field metadata from a SQL Server table."""
        with closing(self.get_connection()) as connection:
            cursor = connection.cursor()
            column_metadata = self._fetch_column_metadata(cursor, schema, table)

            if not column_metadata:
                raise InvalidTableReferenceError(
                    f"Table not found or inaccessible: {schema}.{table}"
                )

            unique_columns = self._fetch_unique_columns(cursor, schema, table)
            field_metadata = []

            for column in column_metadata:
                column_name = column.get("name")
                data_type = column.get("data_type")
                if not column_name or not data_type:
                    raise MissingFieldMetadataError(
                        f"Column metadata is incomplete for {schema}.{table}."
                    )

                metadata = {
                    "name": column_name,
                    "data_type": data_type,
                    "max_length": column.get("max_length"),
                    "min_length": None,
                    "min_value": None,
                    "max_value": None,
                    "unique_values_count": None,
                    "is_nullable": column.get("is_nullable"),
                    "is_unique": column_name in unique_columns,
                    "numeric_precision": column.get("numeric_precision"),
                    "numeric_scale": column.get("numeric_scale"),
                }

                if include_min_max or include_unique_counts:
                    metadata.update(
                        self._fetch_column_stats(
                            cursor=cursor,
                            schema=schema,
                            table=table,
                            column_name=column_name,
                            include_min_max=include_min_max,
                            include_unique_counts=include_unique_counts,
                        )
                    )

                field_metadata.append(metadata)

            return field_metadata

    def _fetch_column_metadata(
        self,
        cursor: Any,
        schema: str,
        table: str
    ) -> List[Dict[str, Any]]:
        """Fetch column metadata from INFORMATION_SCHEMA."""
        query = """
        SELECT
            COLUMN_NAME AS name,
            DATA_TYPE AS data_type,
            CHARACTER_MAXIMUM_LENGTH AS max_length,
            NUMERIC_PRECISION AS numeric_precision,
            NUMERIC_SCALE AS numeric_scale,
            IS_NULLABLE AS is_nullable
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, schema, table)
        rows = cursor.fetchall()
        return [self._row_to_dict(cursor, row) for row in rows]

    def _fetch_unique_columns(
        self,
        cursor: Any,
        schema: str,
        table: str
    ) -> set[str]:
        """Fetch columns that participate in primary-key or unique constraints."""
        query = """
        SELECT kcu.COLUMN_NAME AS name
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
            AND tc.TABLE_NAME = kcu.TABLE_NAME
        WHERE tc.TABLE_SCHEMA = ?
          AND tc.TABLE_NAME = ?
          AND tc.CONSTRAINT_TYPE IN ('PRIMARY KEY', 'UNIQUE')
        """
        cursor.execute(query, schema, table)
        return {
            row_dict["name"]
            for row_dict in (self._row_to_dict(cursor, row) for row in cursor.fetchall())
            if row_dict.get("name")
        }

    def _fetch_column_stats(
        self,
        cursor: Any,
        schema: str,
        table: str,
        column_name: str,
        include_min_max: bool,
        include_unique_counts: bool
    ) -> Dict[str, Any]:
        """Fetch value statistics for a column."""
        select_clauses = []
        if include_min_max:
            select_clauses.extend(
                [
                    f"MIN({self._quote_identifier(column_name)}) AS min_value",
                    f"MAX({self._quote_identifier(column_name)}) AS max_value",
                ]
            )
        if include_unique_counts:
            select_clauses.append(
                f"COUNT(DISTINCT {self._quote_identifier(column_name)}) "
                "AS unique_values_count"
            )

        query = f"""
        SELECT {", ".join(select_clauses)}
        FROM {self._qualified_table_name(schema, table)}
        WHERE {self._quote_identifier(column_name)} IS NOT NULL
        """
        cursor.execute(query)
        row = cursor.fetchone()
        if row is None:
            return {
                "min_value": None,
                "max_value": None,
                "unique_values_count": 0 if include_unique_counts else None,
            }
        return self._row_to_dict(cursor, row)

    def _qualified_table_name(self, schema: str, table: str) -> str:
        """Build a safely quoted SQL Server table identifier."""
        if schema:
            return (
                f"{self._quote_identifier(schema)}."
                f"{self._quote_identifier(table)}"
            )
        return self._quote_identifier(table)

    def _quote_identifier(self, identifier: str) -> str:
        """Safely quote an MSSQL identifier."""
        return f"[{identifier.replace(']', ']]')}]"

    def _row_to_dict(self, cursor: Any, row: Any) -> Dict[str, Any]:
        """Convert a cursor row into a dictionary keyed by column name."""
        if isinstance(row, dict):
            return row

        if hasattr(row, "_asdict"):
            return row._asdict()

        if not hasattr(cursor, "description") or cursor.description is None:
            raise MissingFieldMetadataError(
                "Unable to determine SQL metadata column names."
            )

        column_names = [column[0] for column in cursor.description]
        return dict(zip(column_names, row))
