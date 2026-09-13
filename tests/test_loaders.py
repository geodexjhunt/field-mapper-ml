"""Tests for SQL and mapping loaders."""

import json
import re

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
            self.description = [("constraint_name",), ("name",)]
            if self.unique_columns and isinstance(self.unique_columns[0], tuple):
                self._rows = self.unique_columns
            else:
                self._rows = [
                    (f"constraint_{index}", name)
                    for index, name in enumerate(self.unique_columns)
                ]
            self._row = None
            return

        aliases = re.findall(r"AS (col_\d+_[a-z_]+)", query)
        self.description = [(alias,) for alias in aliases]
        self._rows = []
        values = []
        for alias in aliases:
            match = re.match(r"col_(\d+)_(.+)", alias)
            if not match:
                continue
            column_index = int(match.group(1))
            stat_name = match.group(2)
            column_name = self.columns[column_index][0]
            values.append(self.stats.get(column_name, {}).get(stat_name))
        self._row = tuple(values) if values else None

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


def test_mssql_loader_marks_only_single_column_unique_constraints():
    """Composite unique constraints should not mark individual columns as unique."""
    cursor = FakeCursor(
        columns=[
            ("customer_id", "int", None, 10, 0, "NO"),
            ("email_address", "varchar", 255, None, None, "YES"),
            ("region_code", "varchar", 10, None, None, "YES"),
        ],
        unique_columns=[
            ("PK_customers", "customer_id"),
            ("UQ_email_region", "email_address"),
            ("UQ_email_region", "region_code"),
        ],
    )
    loader = MSSQLLoader(
        database="warehouse",
        connection_factory=lambda _: FakeConnection(cursor),
    )

    metadata = loader.extract_field_metadata(schema="dbo", table="customers")

    assert metadata[0]["is_unique"] is True
    assert metadata[1]["is_unique"] is False
    assert metadata[2]["is_unique"] is False


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
    loader.password = "demo_password"

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
    password_only_loader = MSSQLLoader(
        database="warehouse",
        trusted_connection=False,
    )
    password_only_loader.password = "demo_password"

    with pytest.raises(DatabaseConnectionError):
        mixed_auth_loader.build_connection_string()

    with pytest.raises(DatabaseConnectionError):
        partial_auth_loader.build_connection_string()

    with pytest.raises(DatabaseConnectionError):
        password_only_loader.build_connection_string()


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


def test_approved_mapping_loader_dispatches_by_extension_and_type(tmp_path):
    """The generic load entry point should dispatch by extension or override."""
    json_path = tmp_path / "approved_mappings.data"
    json_path.write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "source_name": "customer_id",
                        "source_table": "dbo.customers",
                        "target_name": "cust_id",
                        "target_table": "dw.dim_customer",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "approved_mappings.csv"
    csv_path.write_text(
        "source_name,source_table,target_name,target_table\n"
        "email_address,dbo.customers,customer_email,dw.dim_customer\n",
        encoding="utf-8",
    )

    loader = ApprovedMappingLoader()

    from_explicit_type = loader.load(str(json_path), file_type="json")
    from_extension = loader.load(str(csv_path))

    assert from_explicit_type[0].target_name == "cust_id"
    assert from_extension[0].source_name == "email_address"


def test_approved_mapping_loader_raises_for_malformed_files(tmp_path):
    """Malformed mapping content should raise a dedicated error."""
    invalid_json_path = tmp_path / "invalid.json"
    invalid_csv_path = tmp_path / "invalid.csv"
    invalid_object_json_path = tmp_path / "invalid_object.json"
    invalid_json_path.write_text("{not valid json", encoding="utf-8")
    invalid_object_json_path.write_text(
        json.dumps({"unexpected": []}),
        encoding="utf-8",
    )
    invalid_csv_path.write_text(
        "source_name,source_table,target_name\n"
        "customer_id,dbo.customers,cust_id\n",
        encoding="utf-8",
    )

    loader = ApprovedMappingLoader()

    with pytest.raises(MalformedMappingFileError):
        loader.load_json(str(invalid_json_path))

    with pytest.raises(MalformedMappingFileError):
        loader.load_json(str(invalid_object_json_path))

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
