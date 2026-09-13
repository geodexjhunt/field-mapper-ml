"""Example for loading SQL metadata into source and target field models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from field_mapper.loaders import (
    DatabaseConnectionError,
    InvalidTableReferenceError,
    MissingFieldMetadataError,
    MSSQLLoader,
)


class DemoCursor:
    """Simple demo cursor used to exercise the loader without a live database."""

    def __init__(self):
        self.description = None
        self._rows = []
        self._row = None

    def execute(self, query, *params):
        if "INFORMATION_SCHEMA.COLUMNS" in query:
            self.description = [
                ("name",),
                ("data_type",),
                ("max_length",),
                ("numeric_precision",),
                ("numeric_scale",),
                ("is_nullable",),
            ]
            self._rows = [
                ("customer_id", "int", None, 10, 0, "NO"),
                ("email_address", "varchar", 255, None, None, "YES"),
            ]
            self._row = None
        elif "TABLE_CONSTRAINTS" in query:
            self.description = [("name",)]
            self._rows = [("customer_id",)]
            self._row = None
        else:
            self.description = [
                ("min_value",),
                ("max_value",),
                ("unique_values_count",),
            ]
            if "[customer_id]" in query:
                self._row = (1, 5000, 5000)
            else:
                self._row = ("a@example.com", "z@example.com", 4500)
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class DemoConnection:
    """Simple demo connection used to exercise the loader without a live database."""

    def cursor(self):
        return DemoCursor()

    def close(self):
        return None


def main() -> None:
    """Load sample source and target fields from a demo SQL loader."""
    loader = MSSQLLoader(
        server="localhost",
        database="FieldMapperDemo",
        trusted_connection=True,
        connection_factory=lambda _: DemoConnection(),
    )

    try:
        source_fields = loader.load_source_fields(
            schema="dbo",
            table="customers",
            include_min_max=True,
            include_unique_counts=True,
        )
        target_fields = loader.load_target_fields(
            schema="dw",
            table="dim_customer",
        )

        print("Source fields:")
        for field in source_fields:
            print(field)

        print("\nTarget fields:")
        for field in target_fields:
            print(field)

        print(
            "\nTo connect to a live Microsoft SQL Server, remove the "
            "connection_factory and ensure pyodbc is installed."
        )
    except (
        DatabaseConnectionError,
        InvalidTableReferenceError,
        MissingFieldMetadataError,
    ) as exc:
        print(f"SQL load failed: {exc}")


if __name__ == "__main__":
    main()
