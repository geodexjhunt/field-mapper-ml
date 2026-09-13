"""Similarity scoring functions."""

import numpy as np
from typing import List, Tuple


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embedding vectors.
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def score_matches(
    source_embedding: np.ndarray,
    target_embeddings: List[Tuple[np.ndarray, str, str]],
    top_n: int = 5
) -> List[Tuple[float, str, str]]:
    """
    Score a source embedding against multiple targets.
    
    Args:
        source_embedding: Embedding for the source field
        target_embeddings: List of (embedding, target_name, target_table) tuples
        top_n: Number of top matches to return
    
    Returns:
        List of (score, target_name, target_table) tuples, sorted by score descending
    """
    scores = []
    
    for target_emb, target_name, target_table in target_embeddings:
        score = cosine_similarity(source_embedding, target_emb)
        scores.append((score, target_name, target_table))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[0], reverse=True)
    
    return scores[:top_n]


def normalize_confidence(score: float) -> float:
    """
    Normalize raw similarity score to confidence (0.0 to 1.0).
    
    For cosine similarity, output is already in range [-1, 1], 
    but typically we work with positive similarities [0, 1].
    This ensures the score is in a reasonable confidence range.
    
    Args:
        score: Raw similarity score
    
    Returns:
        Normalized confidence score (0.0 to 1.0)
    """
    # Clamp to [0, 1] in case of floating point quirks
    return max(0.0, min(1.0, score))
