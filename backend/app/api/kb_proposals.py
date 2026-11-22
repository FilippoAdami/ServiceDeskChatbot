from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.knowledge.manager import KnowledgeProposalManager
from backend.app.llm import BaseLLMProvider, get_llm_provider
from backend.app.rag.service import KnowledgeRetrievalService, get_rag_service
from backend.app.schemas.kb_proposal import (
    DuplicateCandidateResponse,
    KnowledgeProposalApproveRequest,
    KnowledgeProposalGenerateRequest,
    KnowledgeProposalListResponse,
    KnowledgeProposalRejectRequest,
    KnowledgeProposalResponse,
    KnowledgeProposalUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb-proposals", tags=["Knowledge Proposals"])


@router.get("", response_model=KnowledgeProposalListResponse)
def list_proposals(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filtra per stato (draft, under_review, approved, rejected, publishing_failed)",
    ),
    source_type: Optional[str] = Query(None, description="Filtra per source_type (support_request, ticket)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> KnowledgeProposalListResponse:
    """Restituisce la lista paginata delle proposte di articoli per la Knowledge Base."""
    items, total = KnowledgeProposalManager.list_proposals(
        db=db,
        status_filter=status_filter,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )
    return KnowledgeProposalListResponse(
        items=[KnowledgeProposalResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/generate", response_model=KnowledgeProposalResponse, status_code=status.HTTP_201_CREATED)
async def generate_proposal(
    payload: KnowledgeProposalGenerateRequest,
    db: Session = Depends(get_db),
    llm: BaseLLMProvider = Depends(get_llm_provider),
) -> KnowledgeProposalResponse:
    """Genera una nuova bozza di articolo KB a partire da una richiesta risolta e confermata o da un ticket risolto."""
    try:
        proposal = await KnowledgeProposalManager.generate_proposal(
            db=db,
            source_type=payload.source_type,
            source_id=payload.source_id,
            author=payload.author,
            llm_provider=llm,
        )
        return KnowledgeProposalResponse.model_validate(proposal)
    except HTTPException:
        raise
    except ValueError as exc:
        msg = str(exc)
        if "non trovata" in msg or "non trovato" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as exc:
        logger.error(f"Errore nella generazione della proposta KB da {payload.source_type}:{payload.source_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno durante la generazione della proposta: {exc}",
        )


@router.get("/{proposal_id}", response_model=KnowledgeProposalResponse)
def get_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeProposalResponse:
    """Recupera il dettaglio di una specifica proposta KB."""
    try:
        proposal = KnowledgeProposalManager.get_proposal(db, proposal_id)
        return KnowledgeProposalResponse.model_validate(proposal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{proposal_id}", response_model=KnowledgeProposalResponse)
def update_proposal(
    proposal_id: str,
    payload: KnowledgeProposalUpdateRequest,
    db: Session = Depends(get_db),
) -> KnowledgeProposalResponse:
    """Aggiorna titolo, Markdown o destinazione di una proposta in stato di bozza."""
    try:
        proposal = KnowledgeProposalManager.update_proposal(
            db=db,
            proposal_id=proposal_id,
            title=payload.title,
            content_markdown=payload.content_markdown,
            destination=payload.destination,
            target_kb_slug=payload.target_kb_slug,
            notes=payload.notes,
        )
        return KnowledgeProposalResponse.model_validate(proposal)
    except ValueError as exc:
        msg = str(exc)
        if "non trovata" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "non modificabile" in msg or "stato" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/{proposal_id}/reject", response_model=KnowledgeProposalResponse)
def reject_proposal(
    proposal_id: str,
    payload: KnowledgeProposalRejectRequest,
    db: Session = Depends(get_db),
) -> KnowledgeProposalResponse:
    """Rifiuta esplicitamente una proposta KB."""
    try:
        proposal = KnowledgeProposalManager.reject_proposal(
            db=db,
            proposal_id=proposal_id,
            reason=payload.reason,
            author=payload.author,
        )
        return KnowledgeProposalResponse.model_validate(proposal)
    except ValueError as exc:
        msg = str(exc)
        if "non trovata" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "già approvata" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/{proposal_id}/publish", response_model=KnowledgeProposalResponse)
def publish_proposal(
    proposal_id: str,
    payload: KnowledgeProposalApproveRequest,
    db: Session = Depends(get_db),
    rag_service: KnowledgeRetrievalService = Depends(get_rag_service),
) -> KnowledgeProposalResponse:
    """Approva e pubblica la proposta: scrive il file Markdown in knowledge_base/ e reindicizza il RAG."""
    try:
        proposal = KnowledgeProposalManager.approve_and_publish(
            db=db,
            proposal_id=proposal_id,
            rag_service=rag_service,
            author=payload.author,
            destination=payload.destination,
            target_kb_slug=payload.target_kb_slug,
        )
        return KnowledgeProposalResponse.model_validate(proposal)
    except ValueError as exc:
        msg = str(exc)
        if "non trovata" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "già approvata" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        if "Front matter YAML" in msg or "front matter" in msg.lower():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except RuntimeError as exc:
        logger.error(f"Errore critico durante la pubblicazione/reindicizzazione della proposta {proposal_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante la pubblicazione e reindicizzazione: {exc}",
        )


@router.get("/{proposal_id}/duplicates", response_model=List[DuplicateCandidateResponse])
def find_duplicates(
    proposal_id: str,
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    rag_service: KnowledgeRetrievalService = Depends(get_rag_service),
) -> List[DuplicateCandidateResponse]:
    """Cerca documenti esistenti nella Knowledge Base semanticamente simili alla proposta."""
    try:
        candidates = KnowledgeProposalManager.find_duplicates(
            db=db,
            proposal_id=proposal_id,
            rag_service=rag_service,
            top_k=limit,
        )
        return [DuplicateCandidateResponse(**c) for c in candidates]
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Errore nella ricerca duplicati per proposta {proposal_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nella ricerca di duplicati semantici: {exc}",
        )
