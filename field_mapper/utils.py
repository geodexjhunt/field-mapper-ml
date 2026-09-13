"""Utility functions."""

import json
from typing import List, Dict, Any
from field_mapper.models import (
    SourceField, 
    TargetField, 
    ApprovedMapping,
    FieldMappingProposal
)


def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_json_file(data: Dict[str, Any], filepath: str) -> None:
    """Save data to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_source_fields(data: List[Dict[str, Any]]) -> List[SourceField]:
    """Convert list of dictionaries to SourceField objects."""
    return [SourceField(**field_dict) for field_dict in data]


def load_target_fields(data: List[Dict[str, Any]]) -> List[TargetField]:
    """Convert list of dictionaries to TargetField objects."""
    return [TargetField(**field_dict) for field_dict in data]


def load_approved_mappings(data: List[Dict[str, Any]]) -> List[ApprovedMapping]:
    """Convert list of dictionaries to ApprovedMapping objects."""
    return [ApprovedMapping(**mapping_dict) for mapping_dict in data]


def proposals_to_json(proposals: List[FieldMappingProposal]) -> str:
    """Convert proposals to JSON string."""
    proposal_dicts = [p.to_dict() for p in proposals]
    return json.dumps(proposal_dicts, indent=2)


def print_proposal(proposal: FieldMappingProposal) -> None:
    """Pretty print a single proposal."""
    print(f"\n{'='*80}")
    print(f"Source: {proposal.source_field} ({proposal.source_table})")
    if proposal.source_data_type:
        print(f"  Type: {proposal.source_data_type}")
    
    if proposal.legacy_matches:
        print(f"\n  Legacy Matches (from approved mappings):")
        for i, match in enumerate(proposal.legacy_matches, 1):
            print(f"    {i}. {match.target_field} ({match.target_table})")
            print(f"       Confidence: {match.confidence_score:.3f}")
            if match.target_data_type:
                print(f"       Type: {match.target_data_type}")
    
    if proposal.direct_matches:
        print(f"\n  Direct Matches (from target catalog):")
        for i, match in enumerate(proposal.direct_matches, 1):
            print(f"    {i}. {match.target_field} ({match.target_table})")
            print(f"       Confidence: {match.confidence_score:.3f}")
            if match.target_data_type:
                print(f"       Type: {match.target_data_type}")
    
    print()


def print_proposals(proposals: List[FieldMappingProposal]) -> None:
    """Pretty print multiple proposals."""
    for proposal in proposals:
        print_proposal(proposal)
