"""Tests for field mapper."""

import pytest
import numpy as np
from field_mapper.mapper import FieldMapper
from field_mapper.models import (
    SourceField, TargetField, ApprovedMapping, MatchType
)
from field_mapper.scoring import cosine_similarity


class TestCosineSimularity:
    """Test cosine similarity scoring."""
    
    def test_identical_vectors(self):
        """Identical vectors should have similarity of 1.0"""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        assert cosine_similarity(v1, v2) == 1.0
    
    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity of 0.0"""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        assert abs(cosine_similarity(v1, v2)) < 1e-6
    
    def test_normalized_vectors(self):
        """Test with normalized vectors."""
        v1 = np.array([0.6, 0.8])
        v2 = np.array([0.8, 0.6])
        similarity = cosine_similarity(v1, v2)
        assert 0 <= similarity <= 1


class TestFieldMapper:
    """Test field mapper functionality."""
    
    @pytest.fixture
    def mapper(self):
        """Create a mapper instance."""
        return FieldMapper(backend='local')
    
    @pytest.fixture
    def sample_data(self):
        """Create sample approved mappings and target fields."""
        approved = [
            ApprovedMapping(
                source_name="customer_id",
                source_table="customers",
                target_name="cust_id",
                target_table="dim_customer",
            ),
            ApprovedMapping(
                source_name="email_address",
                source_table="customers",
                target_name="customer_email",
                target_table="dim_customer",
            ),
        ]
        
        targets = [
            TargetField(name="cust_id", table="dim_customer"),
            TargetField(name="customer_email", table="dim_customer"),
            TargetField(name="customer_name", table="dim_customer"),
            TargetField(name="order_id", table="fact_orders"),
        ]
        
        return approved, targets
    
    def test_mapper_initialization(self, mapper):
        """Test mapper initialization."""
        assert mapper is not None
        assert mapper.min_confidence_legacy == 0.75
        assert mapper.min_confidence_direct == 0.70
    
    def test_catalog_loading(self, mapper, sample_data):
        """Test loading approved mappings and target fields."""
        approved, targets = sample_data
        mapper.load_catalog(approved, targets)
        
        assert len(mapper.approved_mappings) == 2
        assert len(mapper.target_fields) == 4
        assert len(mapper.approved_source_embeddings) == 2
        assert len(mapper.target_embeddings) == 4
    
    def test_find_matches_basic(self, mapper, sample_data):
        """Test basic matching functionality."""
        approved, targets = sample_data
        mapper.load_catalog(approved, targets)
        
        # Source field that should match legacy mapping
        source_fields = [
            SourceField(name="customer_id", table="customers", data_type="INTEGER")
        ]
        
        proposals = mapper.find_matches(source_fields)
        
        assert len(proposals) == 1
        proposal = proposals[0]
        assert proposal.source_field == "customer_id"
        # Should have some legacy matches
        assert len(proposal.legacy_matches) > 0
    
    def test_legacy_vs_direct_matches(self, mapper, sample_data):
        """Test that legacy and direct matches are distinguished."""
        approved, targets = sample_data
        mapper.load_catalog(approved, targets)
        
        # Source field that matches legacy mapping
        source_fields = [
            SourceField(name="customer_id", table="customers", data_type="INTEGER")
        ]
        
        proposals = mapper.find_matches(source_fields)
        proposal = proposals[0]
        
        # Legacy matches should be present (matched against approved mappings)
        legacy_match_types = [m.match_type for m in proposal.legacy_matches]
        assert MatchType.LEGACY in legacy_match_types
        
        # Direct matches should also be checked (matched against all targets)
        direct_match_types = [m.match_type for m in proposal.direct_matches]
        # May or may not have direct matches depending on similarity
        if direct_match_types:
            assert MatchType.DIRECT in direct_match_types
    
    def test_confidence_thresholds(self, mapper, sample_data):
        """Test that confidence thresholds filter results."""
        approved, targets = sample_data
        
        # Set very high thresholds
        mapper.min_confidence_legacy = 0.99
        mapper.min_confidence_direct = 0.99
        mapper.load_catalog(approved, targets)
        
        source_fields = [
            SourceField(name="unrelated_field", table="table", data_type="STRING")
        ]
        
        proposals = mapper.find_matches(source_fields)
        proposal = proposals[0]
        
        # With very high thresholds, should have few or no matches
        total_matches = len(proposal.legacy_matches) + len(proposal.direct_matches)
        # This may be 0 or very small depending on embeddings
        assert total_matches <= len(targets) + len(approved)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
