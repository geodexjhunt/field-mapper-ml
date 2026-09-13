"""Main field mapper with dual matching strategy."""

import os
from typing import List, Optional, Dict, Tuple
import numpy as np

from field_mapper.models import (
    SourceField,
    TargetField,
    ApprovedMapping,
    Match,
    MatchType,
    FieldMappingProposal
)
from field_mapper.embeddings import EmbeddingBackend, get_embedding_backend
from field_mapper.scoring import cosine_similarity, normalize_confidence


class FieldMapper:
    """
    Main field mapper using dual matching strategy:
    1. Legacy Approved Mappings - match against historically approved mappings
    2. Direct Target Catalog - match against all available target fields
    """
    
    def __init__(
        self,
        backend: str = None,
        min_confidence_legacy: float = None,
        min_confidence_direct: float = None,
        top_n_matches: int = None
    ):
        """
        Initialize FieldMapper.
        
        Args:
            backend: Embedding backend type ('local', 'google', 'cohere')
            min_confidence_legacy: Minimum confidence for legacy matches
            min_confidence_direct: Minimum confidence for direct matches
            top_n_matches: Number of top matches to return per source field
        """
        self.embedding_backend = get_embedding_backend(backend)
        
        # Confidence thresholds from env or defaults
        self.min_confidence_legacy = (
            min_confidence_legacy 
            or float(os.getenv("MIN_CONFIDENCE_LEGACY", 0.75))
        )
        self.min_confidence_direct = (
            min_confidence_direct 
            or float(os.getenv("MIN_CONFIDENCE_DIRECT", 0.70))
        )
        self.top_n_matches = (
            top_n_matches 
            or int(os.getenv("TOP_N_MATCHES", 3))
        )
        
        # Catalogs
        self.approved_mappings: List[ApprovedMapping] = []
        self.target_fields: List[TargetField] = []
        
        # Pre-computed embeddings for performance
        self.approved_source_embeddings: List[np.ndarray] = []
        self.target_embeddings: List[np.ndarray] = []
    
    def load_catalog(
        self,
        approved_mappings: List[ApprovedMapping],
        target_fields: List[TargetField]
    ) -> None:
        """
        Load approved mappings and target field catalog.
        
        Args:
            approved_mappings: List of previously approved mappings
            target_fields: All available target fields
        """
        self.approved_mappings = approved_mappings
        self.target_fields = target_fields
        
        # Pre-compute embeddings for faster matching
        self._precompute_embeddings()
    
    def _precompute_embeddings(self) -> None:
        """Pre-compute and cache embeddings for approved mappings and target fields."""
        # Approved mappings embeddings (source side)
        approved_texts = [
            m.to_source_field().to_embedding_text()
            for m in self.approved_mappings
        ]
        if approved_texts:
            self.approved_source_embeddings = self.embedding_backend.embed_batch(
                approved_texts
            )
        
        # Target fields embeddings
        target_texts = [
            t.to_embedding_text()
            for t in self.target_fields
        ]
        if target_texts:
            self.target_embeddings = self.embedding_backend.embed_batch(
                target_texts
            )
    
    def find_matches(self, source_fields: List[SourceField]) -> List[FieldMappingProposal]:
        """
        Find mapping proposals for source fields using dual strategy.
        
        Args:
            source_fields: List of source fields to map
        
        Returns:
            List of FieldMappingProposal objects with legacy and direct matches
        """
        proposals = []
        
        # Embed all source fields
        source_texts = [f.to_embedding_text() for f in source_fields]
        source_embeddings = self.embedding_backend.embed_batch(source_texts)
        
        # Process each source field
        for source_field, source_embedding in zip(source_fields, source_embeddings):
            legacy_matches = self._find_legacy_matches(source_field, source_embedding)
            direct_matches = self._find_direct_matches(source_field, source_embedding)
            
            proposal = FieldMappingProposal(
                source_field=source_field.name,
                source_table=source_field.table,
                source_data_type=source_field.data_type,
                legacy_matches=legacy_matches,
                direct_matches=direct_matches
            )
            proposals.append(proposal)
        
        return proposals
    
    def _find_legacy_matches(
        self,
        source_field: SourceField,
        source_embedding: np.ndarray
    ) -> List[Match]:
        """
        Find matches against approved historical mappings.
        
        Args:
            source_field: Source field to match
            source_embedding: Embedding of source field
        
        Returns:
            List of Match objects sorted by confidence score
        """
        matches = []
        
        if not self.approved_mappings or not self.approved_source_embeddings:
            return matches
        
        # Score against each approved mapping
        for idx, (approved_mapping, approved_embedding) in enumerate(
            zip(self.approved_mappings, self.approved_source_embeddings)
        ):
            similarity_score = cosine_similarity(source_embedding, approved_embedding)
            confidence = normalize_confidence(similarity_score)
            
            if confidence >= self.min_confidence_legacy:
                target_field = approved_mapping.to_target_field()
                match = Match(
                    target_field=target_field.name,
                    target_table=target_field.table,
                    target_data_type=target_field.data_type,
                    confidence_score=confidence,
                    match_type=MatchType.LEGACY,
                    supporting_metadata={
                        "source_approved": approved_mapping.source_name,
                        "approved_by": approved_mapping.approved_by,
                        "approved_at": approved_mapping.approved_at,
                        "notes": approved_mapping.notes
                    }
                )
                matches.append(match)
        
        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        
        return matches[:self.top_n_matches]
    
    def _find_direct_matches(
        self,
        source_field: SourceField,
        source_embedding: np.ndarray
    ) -> List[Match]:
        """
        Find matches directly against target field catalog.
        
        Args:
            source_field: Source field to match
            source_embedding: Embedding of source field
        
        Returns:
            List of Match objects sorted by confidence score
        """
        matches = []
        
        if not self.target_fields or not self.target_embeddings:
            return matches
        
        # Score against each target field
        for target_field, target_embedding in zip(
            self.target_fields, self.target_embeddings
        ):
            similarity_score = cosine_similarity(source_embedding, target_embedding)
            confidence = normalize_confidence(similarity_score)
            
            if confidence >= self.min_confidence_direct:
                match = Match(
                    target_field=target_field.name,
                    target_table=target_field.table,
                    target_data_type=target_field.data_type,
                    confidence_score=confidence,
                    match_type=MatchType.DIRECT,
                    supporting_metadata={
                        "source_type": source_field.data_type,
                        "target_type": target_field.data_type
                    }
                )
                matches.append(match)
        
        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        
        return matches[:self.top_n_matches]
