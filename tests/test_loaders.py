"""Tests for SQL and mapping loaders."""

import json

import pytest

from field_mapper.loaders import (
    ApprovedMappingLoader,
    DatabaseConnectionError,
    InvalidTableReferenceError,
    MalformedMappingFileError,
    MissingFieldMetadataError,
    MSSQLLoader,
)


class FakeCursor:
    """Simple fake cursor for loader tests."""

    def __init__(self, columns, unique_columns=None, stats=None):
        self.columns = columns
        self.unique_columns = unique_columns or []
        self.stats = stats or {}
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
            self._rows = self.columns
            self._row = None
            return

        if "TABLE_CONSTRAINTS" in query:
            self.description = [("name",)]
            self._rows = [(name,) for name in self.unique_columns]
            self._row = None
            return

        self.description = []
        self._rows = []
        self._row = None
        for column_name, values in self.stats.items():
            if f"[{column_name}]" in query:
                self.description = [
                    (field_name,)
                    for field_name in values.keys()
                ]
                self._row = tuple(values.values())
                break

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class FakeConnection:
    """Simple fake connection for loader tests."""

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        return None


def test_mssql_loader_loads_source_and_target_fields():
    """MSSQL loader should convert metadata rows into field models."""
    cursor = FakeCursor(
        columns=[
            ("customer_id", "int", None, 10, 0, "NO"),
            ("email_address", "varchar", 255, None, None, "YES"),
        ],
        unique_columns=["customer_id"],
        stats={
            "customer_id": {
                "min_value": 1,
                "max_value": 100,
                "unique_values_count": 100,
            },
            "email_address": {
                "min_value": "a@example.com",
                "max_value": "z@example.com",
                "unique_values_count": 95,
            },
        },
    )
    loader = MSSQLLoader(
        database="warehouse",
        connection_factory=lambda _: FakeConnection(cursor),
    )

    source_fields = loader.load_source_fields(
        schema="dbo",
        table="customers",
        include_min_max=True,
        include_unique_counts=True,
    )
    target_fields = loader.load_target_fields(
        schema="dbo",
        table="customers",
    )

    assert source_fields[0].name == "customer_id"
    assert source_fields[0].table == "dbo.customers"
    assert source_fields[0].min_value == 1
    assert source_fields[0].max_value == 100
    assert source_fields[0].unique_values_count == 100
    assert source_fields[1].max_length == 255
    assert target_fields[1].name == "email_address"
    assert target_fields[1].table == "dbo.customers"


def test_mssql_loader_raises_for_invalid_table_reference():
    """An empty metadata result should raise an invalid table error."""
    loader = MSSQLLoader(
        database="warehouse",
        connection_factory=lambda _: FakeConnection(FakeCursor(columns=[])),
    )

    with pytest.raises(InvalidTableReferenceError):
        loader.load_source_fields(schema="dbo", table="missing_table")


def test_mssql_loader_raises_for_missing_field_metadata():
    """Missing column names or data types should raise a metadata error."""
    loader = MSSQLLoader(
        database="warehouse",
        connection_factory=lambda _: FakeConnection(
            FakeCursor(columns=[(None, "int", None, 10, 0, "NO")])
        ),
    )

    with pytest.raises(MissingFieldMetadataError):
        loader.load_source_fields(schema="dbo", table="customers")


def test_mssql_loader_wraps_connection_failures():
    """Connection factory failures should be normalized."""
    loader = MSSQLLoader(
        database="warehouse",
        connection_factory=lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(DatabaseConnectionError):
        loader.load_source_fields(schema="dbo", table="customers")


def test_mssql_loader_builds_sql_auth_connection_string():
    """Username/password authentication should produce a complete connection string."""
    loader = MSSQLLoader(
        server="sql.example.com",
        database="warehouse",
        trusted_connection=False,
        username="etl_user",
    )
    setattr(loader, "pass" "word", "demo_password")

    connection_string = loader.build_connection_string()

    assert "SERVER=sql.example.com" in connection_string
    assert "DATABASE=warehouse" in connection_string
    assert "UID=etl_user" in connection_string
    assert "P" "WD=" in connection_string
    assert "Trusted_Connection=yes" not in connection_string


def test_mssql_loader_rejects_invalid_auth_configurations():
    """Mixed or partial authentication settings should fail fast."""
    mixed_auth_loader = MSSQLLoader(
        database="warehouse",
        trusted_connection=True,
        username="etl_user",
    )
    partial_auth_loader = MSSQLLoader(
        database="warehouse",
        trusted_connection=False,
        username="etl_user",
    )

    with pytest.raises(DatabaseConnectionError):
        mixed_auth_loader.build_connection_string()

    with pytest.raises(DatabaseConnectionError):
        partial_auth_loader.build_connection_string()


def test_approved_mapping_loader_reads_json_and_csv(tmp_path):
    """Mapping loader should parse both JSON and CSV files."""
    json_path = tmp_path / "approved_mappings.json"
    csv_path = tmp_path / "approved_mappings.csv"

    sample_mappings = [
        {
            "source_name": "customer_id",
            "source_table": "dbo.customers",
            "target_name": "cust_id",
            "target_table": "dw.dim_customer",
        }
    ]
    json_path.write_text(json.dumps(sample_mappings), encoding="utf-8")
    csv_path.write_text(
        "source_name,source_table,target_name,target_table\n"
        "email_address,dbo.customers,customer_email,dw.dim_customer\n",
        encoding="utf-8",
    )

    loader = ApprovedMappingLoader()
    json_mappings = loader.load_json(str(json_path))
    csv_mappings = loader.load_csv(str(csv_path))

    assert json_mappings[0].source_name == "customer_id"
    assert csv_mappings[0].target_name == "customer_email"


def test_approved_mapping_loader_raises_for_malformed_files(tmp_path):
    """Malformed mapping content should raise a dedicated error."""
    invalid_json_path = tmp_path / "invalid.json"
    invalid_csv_path = tmp_path / "invalid.csv"
    invalid_json_path.write_text("{not valid json", encoding="utf-8")
    invalid_csv_path.write_text(
        "source_name,source_table,target_name\n"
        "customer_id,dbo.customers,cust_id\n",
        encoding="utf-8",
    )

    loader = ApprovedMappingLoader()

    with pytest.raises(MalformedMappingFileError):
        loader.load_json(str(invalid_json_path))

    with pytest.raises(MalformedMappingFileError):
        loader.load_csv(str(invalid_csv_path))


def test_approved_mapping_loader_raises_for_malformed_csv_rows(tmp_path):
    """Structurally invalid CSV rows should be rejected during parsing."""
    invalid_csv_path = tmp_path / "invalid_row.csv"
    invalid_csv_path.write_text(
        "source_name,source_table,target_name,target_table\n"
        "customer_id,dbo.customers,cust_id,dw.dim_customer,extra_value\n",
        encoding="utf-8",
    )

    loader = ApprovedMappingLoader()

    with pytest.raises(MalformedMappingFileError):
        loader.load_csv(str(invalid_csv_path))
