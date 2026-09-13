"""Example for loading approved mappings from JSON and CSV files."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from field_mapper.loaders import ApprovedMappingLoader


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


if __name__ == "__main__":
    main()
