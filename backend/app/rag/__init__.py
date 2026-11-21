"""RAG (Retrieval-Augmented Generation) package for Service Desk Knowledge Base."""

from backend.app.rag.chunker import chunk_document, slugify
from backend.app.rag.embeddings.base import BaseEmbeddingEncoder
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.models import (
    IndexingSummary,
    KBChunk,
    KBDocument,
    KBFrontMatter,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatusResponse,
    SearchResultItem,
)
from backend.app.rag.parser import (
    KBParseException,
    load_knowledge_base_directory,
    parse_kb_file,
    parse_markdown_content,
)
from backend.app.rag.service import (
    KnowledgeRetrievalService,
    get_rag_service,
    reciprocal_rank_fusion,
    reset_rag_service_for_test,
)
from backend.app.rag.vector_store.base import BaseVectorStore
from backend.app.rag.vector_store.chroma import ChromaVectorStore

__all__ = [
    "BaseEmbeddingEncoder",
    "BaseVectorStore",
    "ChromaVectorStore",
    "DeterministicFakeEncoder",
    "IndexingSummary",
    "KBChunk",
    "KBDocument",
    "KBFrontMatter",
    "KBParseException",
    "KnowledgeRetrievalService",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "KnowledgeStatusResponse",
    "SearchResultItem",
    "chunk_document",
    "get_rag_service",
    "load_knowledge_base_directory",
    "parse_kb_file",
    "parse_markdown_content",
    "reciprocal_rank_fusion",
    "reset_rag_service_for_test",
    "slugify",
]
