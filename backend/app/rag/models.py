from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class KBFrontMatter(BaseModel):
    """Front matter metadata for a knowledge base Markdown document."""

    id: str = Field(..., description="Unique document ID (e.g., KB-AUTH-001)")
    title: str = Field(..., description="Document title")
    category: str = Field(..., description="Document category")
    tags: List[str] = Field(default_factory=list, description="Categorization and search tags")
    status: str = Field(..., description="Lifecycle status (approved, draft, archived)")
    version: str = Field(default="1.0", description="Document version string")
    last_updated: Optional[str] = Field(default=None, description="ISO date of last update")
    author: Optional[str] = Field(default=None, description="Authoring team or person")
    summary: Optional[str] = Field(default=None, description="Brief document summary")

    @field_validator("version", mode="before")
    @classmethod
    def coerce_version_to_str(cls, v: Any) -> str:
        if v is None:
            return "1.0"
        return str(v)

    @field_validator("last_updated", mode="before")
    @classmethod
    def coerce_last_updated_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)


@dataclass
class KBDocument:
    """Parsed knowledge base document."""

    front_matter: KBFrontMatter
    content: str
    source_path: str
    raw_text: str


@dataclass
class KBChunk:
    """A semantic chunk derived from a knowledge base document."""

    chunk_id: str
    doc_id: str
    doc_title: str
    category: str
    heading: str
    chunk_index: int
    text: str
    source_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SearchResultItem(BaseModel):
    """Single retrieval result with attribution and score."""

    chunk_id: str
    doc_id: str
    doc_title: str
    category: str
    heading: str
    text: str
    score: float = Field(..., description="Retrieval similarity or RRF score (higher is better)")
    source_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchRequest(BaseModel):
    """Request schema for knowledge search endpoint."""

    query: str = Field(..., min_length=2, max_length=1000, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to return")
    sub_queries: Optional[List[str]] = Field(
        default=None,
        max_length=5,
        description="Optional list of reformulations for multi-query retrieval",
    )


class KnowledgeSearchResponse(BaseModel):
    """Response schema for knowledge search endpoint."""

    query: str
    sub_queries: List[str] = Field(default_factory=list)
    results: List[SearchResultItem]
    total: int
    elapsed_ms: float


class KnowledgeStatusResponse(BaseModel):
    """Status information for the persistent knowledge base index."""

    is_ready: bool
    total_documents: int
    total_chunks: int
    collection_name: str
    persist_dir: str
    embedding_model: str
    embedding_dimension: int
    last_indexed_at: Optional[str] = None


@dataclass
class IndexingSummary:
    """Summary of a knowledge base re-indexing operation."""

    documents_scanned: int
    documents_approved: int
    documents_skipped: int
    chunks_created: int
    chunks_deleted: int
    elapsed_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
