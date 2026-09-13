"""Example for loading approved mappings from JSON, CSV, and SQL sources."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from field_mapper.loaders import ApprovedMappingLoader, MSSQLMappingLoader


class DemoCursor:
    """Simple demo cursor for loading approved mappings from SQL."""

    def __init__(self):
        self.description = None
        self._rows = []

    def execute(self, query, *params):
        if "SELECT * FROM [config].[approved_mappings]" in query:
            self.description = None
            self._rows = [
                {
                    "src_field": "phone_number",
                    "src_table_name": "dbo.customers",
                    "dst_field": "customer_phone",
                    "dst_table_name": "dw.dim_customer",
                    "approver": "data-team",
                }
            ]
        else:
            self._rows = []

    def fetchall(self):
        return self._rows


class DemoConnection:
    """Simple demo connection for loading approved mappings from SQL."""

    def cursor(self):
        return DemoCursor()

    def close(self):
        return None


def main() -> None:
    """Create demo mapping files and load them."""
    loader = ApprovedMappingLoader()

    sample_mappings = [
        {
            "source_name": "customer_id",
            "source_table": "dbo.customers",
            "target_name": "cust_id",
            "target_table": "dw.dim_customer",
            "approved_by": "data-team",
        },
        {
            "source_name": "email_address",
            "source_table": "dbo.customers",
            "target_name": "customer_email",
            "target_table": "dw.dim_customer",
        },
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        json_path = temp_path / "approved_mappings.json"
        csv_path = temp_path / "approved_mappings.csv"

        json_path.write_text(json.dumps(sample_mappings, indent=2), encoding="utf-8")
        csv_path.write_text(
            (
                "source_name,source_table,target_name,target_table,approved_by\n"
                "customer_id,dbo.customers,cust_id,dw.dim_customer,data-team\n"
                "email_address,dbo.customers,customer_email,dw.dim_customer,\n"
            ),
            encoding="utf-8",
        )

        print("JSON mappings:")
        for mapping in loader.load_json(str(json_path)):
            print(mapping)

        print("\nCSV mappings:")
        for mapping in loader.load_csv(str(csv_path)):
            print(mapping)

        sql_loader = MSSQLMappingLoader(
            server="localhost",
            database="FieldMapperDemo",
            trusted_connection=True,
            connection_factory=lambda _: DemoConnection(),
        )
        print("\nSQL mappings:")
        for mapping in loader.load_sql(
            sql_loader,
            schema="config",
            table="approved_mappings",
            field_mapping={
                "source_name": "src_field",
                "source_table": "src_table_name",
                "target_name": "dst_field",
                "target_table": "dst_table_name",
                "approved_by": "approver",
            },
        ):
            print(mapping)


if __name__ == "__main__":
    main()
