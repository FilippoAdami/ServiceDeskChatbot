from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.redaction import redact_secrets
from backend.app.rag.models import (
    IndexingSummary,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatusResponse,
)
from backend.app.rag.service import KnowledgeRetrievalService, get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.get(
    "/status",
    response_model=KnowledgeStatusResponse,
    summary="Get Knowledge Base Index Status",
    description="Returns indexing status, document/chunk counts, model info, and readiness.",
)
def get_knowledge_status(
    rag_service: Annotated[KnowledgeRetrievalService, Depends(get_rag_service)],
) -> KnowledgeStatusResponse:
    try:
        return rag_service.get_status()
    except Exception as e:
        logger.error("Failed to retrieve knowledge status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query knowledge base status",
        ) from e


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="Semantic Search in Knowledge Base",
    description="Retrieve relevant approved knowledge chunks given a user query and optional multi-query expansions.",
)
def search_knowledge_base(
    payload: KnowledgeSearchRequest,
    rag_service: Annotated[KnowledgeRetrievalService, Depends(get_rag_service)],
) -> KnowledgeSearchResponse:
    start_time = time.perf_counter()

    # Redact query for safe structured logging
    safe_query = redact_secrets(payload.query)
    logger.info(
        "Knowledge search requested: top_k=%d, sub_queries_count=%d, query_sample='%s'",
        payload.top_k,
        len(payload.sub_queries or []),
        safe_query[:50],
    )

    try:
        kb_status = rag_service.get_status()
        if not kb_status.is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge base index is unindexed or empty. Run reindexing first.",
            )

        results = rag_service.search(
            query=payload.query,
            top_k=payload.top_k,
            sub_queries=payload.sub_queries,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error executing semantic search: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic retrieval failed: {e}",
        ) from e

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return KnowledgeSearchResponse(
        query=payload.query,
        sub_queries=payload.sub_queries or [],
        results=results,
        total=len(results),
        elapsed_ms=elapsed_ms,
    )


@router.post(
    "/reindex",
    response_model=IndexingSummary,
    summary="Trigger Knowledge Base Reindexing",
    description="Idempotently re-scans knowledge_base directory and refreshes ChromaDB vectors.",
)
def trigger_reindexing(
    rag_service: Annotated[KnowledgeRetrievalService, Depends(get_rag_service)],
) -> IndexingSummary:
    try:
        logger.info("Manual knowledge base reindexing triggered via API")
        summary = rag_service.index_documents(clean_obsolete=True)
        return summary
    except Exception as e:
        logger.error("Knowledge base reindexing failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindexing failed: {e}",
        ) from e
