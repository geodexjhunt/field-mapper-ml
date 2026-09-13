"""Embedding backends for semantic similarity."""

from abc import ABC, abstractmethod
import os
import numpy as np
from typing import List


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""
    
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple text strings."""
        pass


class LocalEmbeddingBackend(EmbeddingBackend):
    """Local embedding using Sentence Transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embedding backend.
        
        Args:
            model_name: Hugging Face model name (default: MiniLM for speed/accuracy)
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
    
    def embed(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        return self.model.encode(text, convert_to_numpy=True)
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple text strings."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [np.array(e) for e in embeddings]


class GoogleEmbeddingBackend(EmbeddingBackend):
    """Google Text Embedding API backend."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Google Embedding backend.
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY environment variable)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not provided. Set environment variable or pass api_key."
            )
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Install with: pip install google-generativeai"
            )
    
    def embed(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        result = self.client.embed_content(
            model="models/embedding-001",
            content=text
        )
        return np.array(result["embedding"])
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple text strings."""
        embeddings = []
        for text in texts:
            embedding = self.embed(text)
            embeddings.append(embedding)
        return embeddings


class CohereEmbeddingBackend(EmbeddingBackend):
    """Cohere Embed API backend."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Cohere Embedding backend.
        
        Args:
            api_key: Cohere API key (or set COHERE_API_KEY environment variable)
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "COHERE_API_KEY not provided. Set environment variable or pass api_key."
            )
        
        try:
            import cohere
            self.client = cohere.Client(self.api_key)
        except ImportError:
            raise ImportError(
                "cohere not installed. "
                "Install with: pip install cohere"
            )
    
    def embed(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        response = self.client.embed(
            texts=[text],
            model="embed-english-v3.0",
            input_type="search_document"
        )
        return np.array(response.embeddings[0])
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple text strings."""
        response = self.client.embed(
            texts=texts,
            model="embed-english-v3.0",
            input_type="search_document"
        )
        return [np.array(e) for e in response.embeddings]


def get_embedding_backend(backend_type: str = None) -> EmbeddingBackend:
    """
    Factory function to get the appropriate embedding backend.
    
    Args:
        backend_type: 'local', 'google', or 'cohere' (defaults to env var or 'local')
    
    Returns:
        Initialized embedding backend instance
    """
    backend_type = backend_type or os.getenv("EMBEDDING_BACKEND", "local")
    
    if backend_type == "local":
        return LocalEmbeddingBackend()
    elif backend_type == "google":
        return GoogleEmbeddingBackend()
    elif backend_type == "cohere":
        return CohereEmbeddingBackend()
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
