"""
Example demonstrating field mapping with dual strategy:
1. Legacy-backed matches (approved mappings)
2. Direct semantic matches (target field catalog)
"""

import json
from field_mapper.mapper import FieldMapper
from field_mapper.models import SourceField, TargetField, ApprovedMapping
from field_mapper.utils import print_proposals


def load_example_data():
    """Load example data for demonstration."""
    
    # Previously approved mappings (legacy)
    approved_mappings = [
        ApprovedMapping(
            source_name="customer_id",
            source_table="source_customers",
            source_data_type="INTEGER",
            target_name="cust_id",
            target_table="dim_customer",
            target_data_type="INTEGER",
            approved_by="data_team",
            approved_at="2024-01-15",
            notes="Main customer ID"
        ),
        ApprovedMapping(
            source_name="email_address",
            source_table="source_customers",
            source_data_type="VARCHAR(255)",
            target_name="customer_email",
            target_table="dim_customer",
            target_data_type="VARCHAR(255)",
            approved_by="data_team",
            approved_at="2024-01-15",
            notes="Customer contact email"
        ),
        ApprovedMapping(
            source_name="phone_number",
            source_table="source_customers",
            source_data_type="VARCHAR(20)",
            target_name="phone",
            target_table="dim_customer",
            target_data_type="VARCHAR(20)",
            approved_by="data_team",
            approved_at="2024-01-20",
            notes="Customer phone"
        ),
    ]
    
    # All available target fields in the target database
    target_fields = [
        # Existing mappings (also appear in target via approved mappings)
        TargetField(name="cust_id", table="dim_customer", data_type="INTEGER"),
        TargetField(name="customer_email", table="dim_customer", data_type="VARCHAR(255)"),
        TargetField(name="phone", table="dim_customer", data_type="VARCHAR(20)"),
        TargetField(name="customer_name", table="dim_customer", data_type="VARCHAR(255)"),
        TargetField(name="registration_date", table="dim_customer", data_type="DATE"),
        
        # Order-related fields
        TargetField(name="order_id", table="fact_orders", data_type="INTEGER"),
        TargetField(name="order_date", table="fact_orders", data_type="DATE"),
        TargetField(name="order_amount", table="fact_orders", data_type="DECIMAL(10,2)"),
        TargetField(name="order_status", table="fact_orders", data_type="VARCHAR(50)"),
        TargetField(name="customer_ref", table="fact_orders", data_type="INTEGER"),
        
        # Product fields
        TargetField(name="product_code", table="dim_product", data_type="VARCHAR(100)"),
        TargetField(name="product_name", table="dim_product", data_type="VARCHAR(255)"),
        TargetField(name="product_price", table="dim_product", data_type="DECIMAL(10,2)"),
    ]
    
    return approved_mappings, target_fields


def main():
    """Run example field mapping."""
    
    print("=" * 80)
    print("Field Mapper ML - Example with Dual Matching Strategy")
    print("=" * 80)
    
    # Load example data
    approved_mappings, target_fields = load_example_data()
    
    # Initialize mapper with local backend (no API keys needed)
    print("\n[1] Initializing mapper with local embeddings...")
    mapper = FieldMapper(backend='local')
    
    # Load the catalogs
    print("[2] Loading approved mappings and target field catalog...")
    mapper.load_catalog(approved_mappings, target_fields)
    
    # Define source fields to map
    # Mix of fields that should match legacy mappings and direct matches
    source_fields = [
        SourceField(
            name="cust_id",  # Should match legacy mapping for "customer_id"
            table="customers",
            data_type="INT"
        ),
        SourceField(
            name="email",  # Should match legacy mapping for "email_address"
            table="customers",
            data_type="VARCHAR(250)"
        ),
        SourceField(
            name="phone_num",  # Should match legacy mapping for "phone_number"
            table="customers",
            data_type="VARCHAR(20)"
        ),
        SourceField(
            name="full_name",  # Should find direct match: "customer_name"
            table="customers",
            data_type="VARCHAR(255)"
        ),
        SourceField(
            name="order_date_time",  # Should find direct match: "order_date"
            table="orders",
            data_type="TIMESTAMP"
        ),
        SourceField(
            name="total_order_amount",  # Should find direct match: "order_amount"
            table="orders",
            data_type="DECIMAL(12,2)"
        ),
    ]
    
    # Get mapping proposals
    print("[3] Finding mapping proposals...")
    proposals = mapper.find_matches(source_fields)
    
    # Display results
    print("\n" + "=" * 80)
    print("MAPPING PROPOSALS")
    print("=" * 80)
    print_proposals(proposals)
    
    # Export to JSON for review/approval workflow
    print("\n" + "=" * 80)
    print("Exporting proposals to JSON...")
    print("=" * 80)
    
    proposals_json = [p.to_dict() for p in proposals]
    with open("mapping_proposals.json", "w") as f:
        json.dump(proposals_json, f, indent=2)
    print("✓ Saved to: mapping_proposals.json")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_legacy = sum(len(p.legacy_matches) for p in proposals)
    total_direct = sum(len(p.direct_matches) for p in proposals)
    print(f"Total source fields: {len(proposals)}")
    print(f"Total legacy matches (approved mappings): {total_legacy}")
    print(f"Total direct matches (target catalog): {total_direct}")
    print(f"Average confidence (legacy): {sum(sum(m.confidence_score for m in p.legacy_matches) for p in proposals) / (total_legacy or 1):.3f}")
    print(f"Average confidence (direct): {sum(sum(m.confidence_score for m in p.direct_matches) for p in proposals) / (total_direct or 1):.3f}")
    

if __name__ == "__main__":
    main()
