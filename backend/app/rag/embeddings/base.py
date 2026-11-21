from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingEncoder(ABC):
    """Abstract interface for dense embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality of embeddings."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier/tag of the embedding model."""
        pass

    @abstractmethod
    def encode_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute dense vector representations for knowledge base documents/chunks."""
        pass

    @abstractmethod
    def encode_queries(self, queries: List[str]) -> List[List[float]]:
        """Compute dense vector representations for search queries."""
        pass
