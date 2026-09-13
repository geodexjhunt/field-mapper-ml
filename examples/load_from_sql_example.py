"""Example for loading SQL metadata into source and target field models."""

import re
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
            self.description = [("constraint_name",), ("name",)]
            self._rows = [("PK_customers", "customer_id")]
            self._row = None
        else:
            aliases = re.findall(r"AS (col_\d+_[a-z_]+)", query)
            self.description = [(alias,) for alias in aliases]
            values = []
            for alias in aliases:
                if alias.startswith("col_0_"):
                    if alias.endswith("min_value"):
                        values.append(1)
                    elif alias.endswith("max_value"):
                        values.append(5000)
                    else:
                        values.append(5000)
                else:
                    if alias.endswith("min_value"):
                        values.append("a@example.com")
                    elif alias.endswith("max_value"):
                        values.append("z@example.com")
                    else:
                        values.append(4500)
            self._row = tuple(values)
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
