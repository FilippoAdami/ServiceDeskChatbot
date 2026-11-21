from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set

from backend.app.rag.models import KBChunk, SearchResultItem


class BaseVectorStore(ABC):
    """Abstract interface for knowledge chunk vector storage and retrieval."""

    @abstractmethod
    def add_chunks(self, chunks: List[KBChunk], embeddings: List[List[float]]) -> None:
        """Add or update chunks with their dense embeddings."""
        pass

    @abstractmethod
    def delete_document_chunks(self, doc_ids: List[str]) -> int:
        """Delete all chunks associated with the specified document IDs."""
        pass

    @abstractmethod
    def query_similar(self, query_embedding: List[float], top_k: int = 5) -> List[SearchResultItem]:
        """Query for top_k chunks closest to the query embedding."""
        pass

    @abstractmethod
    def count_chunks(self) -> int:
        """Return the total number of chunks currently stored in the index."""
        pass

    @abstractmethod
    def get_indexed_doc_ids(self) -> Set[str]:
        """Return the set of all document IDs currently present in the index."""
        pass

    @abstractmethod
    def get_collection_metadata(self) -> Dict[str, Any]:
        """Return collection-level metadata (model name, dimension, timestamp)."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Clear all chunks from the vector store."""
        pass
