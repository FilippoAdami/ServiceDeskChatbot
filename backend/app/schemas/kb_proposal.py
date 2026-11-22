from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeProposalGenerateRequest(BaseModel):
    """Payload to request the generation of a KB draft proposal."""

    source_type: str = Field(..., description="Tipo sorgente: 'support_request' o 'ticket'")
    source_id: str = Field(..., description="ID della richiesta o del ticket sorgente")
    author: str = Field(default="technician_demo", description="Nome o ID del richiedente/tecnico")


class KnowledgeProposalUpdateRequest(BaseModel):
    """Payload to update/edit an existing KB proposal."""

    title: Optional[str] = Field(None, min_length=3, description="Titolo modificato")
    content_markdown: Optional[str] = Field(None, min_length=10, description="Contenuto Markdown con front matter")
    destination: Optional[str] = Field(None, description="'new_document' o 'update_existing'")
    target_kb_slug: Optional[str] = Field(None, description="Slug o filename del documento target se aggiornamento")
    notes: Optional[str] = Field(None, description="Note di revisione del tecnico")


class KnowledgeProposalRejectRequest(BaseModel):
    """Payload to reject a KB proposal."""

    reason: Optional[str] = Field(None, description="Motivo del rifiuto")
    author: str = Field(default="technician_demo", description="Nome o ID del tecnico")


class KnowledgeProposalApproveRequest(BaseModel):
    """Payload to approve and publish a KB proposal."""

    author: str = Field(default="technician_demo", description="Nome o ID del tecnico")
    destination: Optional[str] = Field(None, description="'new_document' o 'update_existing'")
    target_kb_slug: Optional[str] = Field(None, description="Slug del documento target se aggiornamento")


class KnowledgeProposalResponse(BaseModel):
    """Full representation of a KnowledgeProposal entity."""

    id: str
    source_type: str
    source_id: str
    status: str
    title: str
    category: str
    content_markdown: str
    destination: str
    target_kb_slug: Optional[str] = None
    version: int
    summary_quality: str
    author: str
    rejection_reason: Optional[str] = None
    published_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeProposalListResponse(BaseModel):
    """List response for KB proposals."""

    items: List[KnowledgeProposalResponse]
    total: int
    limit: int
    offset: int


class DuplicateCandidateResponse(BaseModel):
    """Candidate existing document that might be duplicate or relevant for update."""

    doc_id: str
    title: str
    category: str
    heading: str
    source_path: str
    score: float
    summary: Optional[str] = None
    slug: Optional[str] = None
    similarity: Optional[float] = None
    preview: Optional[str] = None
