from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from backend.app.config import get_settings
from backend.app.rag.chunker import chunk_document
from backend.app.rag.embeddings.base import BaseEmbeddingEncoder
from backend.app.rag.embeddings.bge_m3 import BGEM3Encoder
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.models import (
    IndexingSummary,
    KBChunk,
    KnowledgeStatusResponse,
    SearchResultItem,
)
from backend.app.rag.parser import load_knowledge_base_directory
from backend.app.rag.vector_store.base import BaseVectorStore
from backend.app.rag.vector_store.chroma import ChromaVectorStore

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: List[List[SearchResultItem]],
    k: int = 60,
    top_k: int = 5,
) -> List[SearchResultItem]:
    """Fuse multiple ranked search result lists using Reciprocal Rank Fusion (RRF).

    Formula: RRF_score(d) = sum(1 / (k + rank_i)) for each list where d appears.
    Rank is 1-indexed (1st result has rank 1).
    """
    scores: Dict[str, float] = {}
    items_by_id: Dict[str, SearchResultItem] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            chunk_id = item.chunk_id
            rrf_val = 1.0 / (k + rank)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_val
            # Keep the item representation with highest individual score
            if chunk_id not in items_by_id or item.score > items_by_id[chunk_id].score:
                items_by_id[chunk_id] = item

    sorted_chunk_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

    fused_results: List[SearchResultItem] = []
    for cid in sorted_chunk_ids[:top_k]:
        base_item = items_by_id[cid]
        # Create new item with fused RRF score
        fused_item = SearchResultItem(
            chunk_id=base_item.chunk_id,
            doc_id=base_item.doc_id,
            doc_title=base_item.doc_title,
            category=base_item.category,
            heading=base_item.heading,
            text=base_item.text,
            score=round(scores[cid], 5),
            source_path=base_item.source_path,
            metadata=base_item.metadata,
        )
        fused_results.append(fused_item)

    return fused_results


class KnowledgeRetrievalService:
    """Service orchestrating knowledge base indexing, embedding, and semantic retrieval."""

    def __init__(
        self,
        encoder: Optional[BaseEmbeddingEncoder] = None,
        vector_store: Optional[BaseVectorStore] = None,
        base_kb_dir: Optional[Path] = None,
    ) -> None:
        settings = get_settings()

        if base_kb_dir is not None:
            self._kb_dir = Path(base_kb_dir)
        else:
            self._kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)

        # Set up encoder
        if encoder is not None:
            self._encoder = encoder
        elif settings.RAG_USE_FAKE_ENCODER:
            self._encoder = DeterministicFakeEncoder(dimension=1024)
        else:
            self._encoder = BGEM3Encoder(
                model_name=settings.EMBEDDING_MODEL_NAME,
                device=settings.EMBEDDING_DEVICE,
            )

        # Set up vector store
        if vector_store is not None:
            self._vector_store = vector_store
        else:
            self._vector_store = ChromaVectorStore(
                persist_dir=settings.CHROMA_PERSIST_DIR,
                model_name=self._encoder.model_name,
                dimension=self._encoder.dimension,
            )

        self._last_indexed_at: Optional[str] = None

    @property
    def encoder(self) -> BaseEmbeddingEncoder:
        return self._encoder

    @property
    def vector_store(self) -> BaseVectorStore:
        return self._vector_store

    def index_documents(
        self,
        docs_dir: Optional[Path] = None,
        clean_obsolete: bool = True,
    ) -> IndexingSummary:
        """Scan, parse, chunk, embed, and store approved knowledge base documents.

        Performs idempotent indexing and cleans up chunks from deleted/archived documents.
        """
        start_time = time.perf_counter()
        target_dir = docs_dir if docs_dir is not None else self._kb_dir

        approved_docs, skipped_paths = load_knowledge_base_directory(target_dir, only_approved=True)

        total_scanned = len(approved_docs) + len(skipped_paths)
        approved_count = len(approved_docs)
        skipped_count = len(skipped_paths)

        current_approved_doc_ids: Set[str] = {doc.front_matter.id for doc in approved_docs}
        deleted_chunks = 0

        # Obsolete chunk cleanup
        if clean_obsolete:
            existing_doc_ids = self._vector_store.get_indexed_doc_ids()
            obsolete_doc_ids = list(existing_doc_ids - current_approved_doc_ids)
            if obsolete_doc_ids:
                logger.info("Cleaning up obsolete document chunks for IDs: %s", obsolete_doc_ids)
                deleted_chunks = self._vector_store.delete_document_chunks(obsolete_doc_ids)

        all_chunks: List[KBChunk] = []
        for doc in approved_docs:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)

        if all_chunks:
            # Re-index all chunks for approved docs (idempotent upsert)
            logger.info("Computing embeddings for %d knowledge chunks...", len(all_chunks))
            chunk_texts = [c.text for c in all_chunks]
            embeddings = self._encoder.encode_documents(chunk_texts)
            self._vector_store.add_chunks(all_chunks, embeddings)

        elapsed = time.perf_counter() - start_time
        timestamp = datetime.now(timezone.utc).isoformat()
        self._last_indexed_at = timestamp

        summary = IndexingSummary(
            documents_scanned=total_scanned,
            documents_approved=approved_count,
            documents_skipped=skipped_count,
            chunks_created=len(all_chunks),
            chunks_deleted=deleted_chunks,
            elapsed_seconds=round(elapsed, 3),
            timestamp=timestamp,
        )
        logger.info(
            "Knowledge base indexing finished: %d approved docs, %d chunks in %.2fs",
            summary.documents_approved,
            summary.chunks_created,
            summary.elapsed_seconds,
        )
        return summary

    def search(
        self,
        query: str,
        top_k: int = 5,
        sub_queries: Optional[List[str]] = None,
    ) -> List[SearchResultItem]:
        """Perform semantic search across the knowledge base.

        Supports single-query search or multi-query search with Reciprocal Rank Fusion (RRF).
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        clean_sub_queries = [sq.strip() for sq in (sub_queries or []) if sq.strip()]

        if not clean_sub_queries:
            # Single-query search
            query_embeddings = self._encoder.encode_queries([clean_query])
            if not query_embeddings:
                return []
            return self._vector_store.query_similar(query_embeddings[0], top_k=top_k)

        # Multi-query search: search each query separately, then fuse with RRF
        all_queries = [clean_query] + clean_sub_queries
        query_embeddings = self._encoder.encode_queries(all_queries)

        ranked_lists: List[List[SearchResultItem]] = []
        for q_emb in query_embeddings:
            results = self._vector_store.query_similar(q_emb, top_k=top_k * 2)
            ranked_lists.append(results)

        return reciprocal_rank_fusion(ranked_lists, k=60, top_k=top_k)

    def get_status(self) -> KnowledgeStatusResponse:
        """Get the current operational status of the knowledge base index."""
        store_meta = self._vector_store.get_collection_metadata()
        total_chunks = self._vector_store.count_chunks()
        doc_ids = self._vector_store.get_indexed_doc_ids()

        return KnowledgeStatusResponse(
            is_ready=(total_chunks > 0),
            total_documents=len(doc_ids),
            total_chunks=total_chunks,
            collection_name=str(store_meta.get("collection_name", ChromaVectorStore.COLLECTION_NAME)),
            persist_dir=str(store_meta.get("persist_dir", "")),
            embedding_model=self._encoder.model_name,
            embedding_dimension=self._encoder.dimension,
            last_indexed_at=self._last_indexed_at,
        )


# Singleton factory for FastAPI dependency injection
_rag_service_instance: Optional[KnowledgeRetrievalService] = None


def get_rag_service() -> KnowledgeRetrievalService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = KnowledgeRetrievalService()
    return _rag_service_instance


def reset_rag_service_for_test(service: Optional[KnowledgeRetrievalService] = None) -> None:
    """Helper to inject custom/mock RAG service in test suites."""
    global _rag_service_instance
    _rag_service_instance = service
