from __future__ import annotations

import datetime
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import (
    KnowledgeProposal,
    Message,
    ProposalDestination,
    ProposalSourceType,
    ProposalStatus,
    SupportRequest,
    Ticket,
    utc_now,
)
from backend.app.knowledge.generator import generate_kb_proposal_markdown
from backend.app.llm.base import BaseLLMProvider
from backend.app.rag.parser import KBParseException, parse_markdown_content
from backend.app.rag.service import KnowledgeRetrievalService

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Sanitizes a string to produce a safe filename ending with .md."""
    base_name = name[:-3] if name.lower().endswith(".md") else name
    clean = re.sub(r"[^A-Za-z0-9_.-]", "_", base_name).strip("._")
    if not clean:
        clean = "kb_doc"
    return f"{clean.lower()}.md"


class KnowledgeProposalManager:
    """Manages the full lifecycle of KB proposals: generation, review, duplicate detection,

    safe atomic publishing, and RAG re-indexing.
    """

    @staticmethod
    def list_proposals(
        db: Session,
        status_filter: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[KnowledgeProposal], int]:
        """Lists proposals with optional status/source_type filters and pagination."""
        query = select(KnowledgeProposal)
        if status_filter and status_filter != "all":
            query = query.where(KnowledgeProposal.status == status_filter)
        if source_type:
            query = query.where(KnowledgeProposal.source_type == source_type)

        count_query = select(KnowledgeProposal.id)
        if status_filter and status_filter != "all":
            count_query = count_query.where(KnowledgeProposal.status == status_filter)
        if source_type:
            count_query = count_query.where(KnowledgeProposal.source_type == source_type)

        total = len(list(db.scalars(count_query).all()))
        items = list(
            db.scalars(
                query.order_by(KnowledgeProposal.updated_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
        )
        return items, total

    @staticmethod
    def get_proposal(db: Session, proposal_id: str) -> KnowledgeProposal:
        """Retrieves a single proposal or raises 404."""
        prop = db.scalar(select(KnowledgeProposal).where(KnowledgeProposal.id == proposal_id))
        if not prop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proposta Knowledge Base '{proposal_id}' non trovata.",
            )
        return prop

    @staticmethod
    async def generate_proposal(
        db: Session,
        source_type: str,
        source_id: str,
        llm_provider: Optional[BaseLLMProvider] = None,
        author: str = "technician_demo",
    ) -> KnowledgeProposal:
        """Generates a new draft proposal or reuses existing active draft."""
        # Check for existing draft for this source to prevent unwanted duplication
        existing = db.scalar(
            select(KnowledgeProposal).where(
                KnowledgeProposal.source_type == source_type,
                KnowledgeProposal.source_id == source_id,
                KnowledgeProposal.status == ProposalStatus.DRAFT.value,
            )
        )
        if existing:
            logger.info(f"Reusing existing draft proposal {existing.id} for {source_type}:{source_id}")
            return existing

        source_obj: Any = None
        messages: List[Message] = []

        if source_type == ProposalSourceType.SUPPORT_REQUEST.value:
            req = db.scalar(select(SupportRequest).where(SupportRequest.id == source_id))
            if not req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Richiesta supporto '{source_id}' non trovata.",
                )
            source_obj = req
            messages = list(
                db.scalars(
                    select(Message)
                    .where(Message.conversation_id == req.conversation_id)
                    .order_by(Message.created_at.asc())
                ).all()
            )
        elif source_type == ProposalSourceType.TICKET.value:
            ticket = db.scalar(select(Ticket).where(Ticket.id == source_id))
            if not ticket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ticket '{source_id}' non trovato.",
                )
            source_obj = ticket
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"source_type '{source_type}' non valido. Usa 'support_request' o 'ticket'.",
            )

        try:
            markdown, title, category, quality = await generate_kb_proposal_markdown(
                source_type=source_type,
                source_obj=source_obj,
                messages=messages,
                llm_provider=llm_provider,
            )
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err),
            )

        proposal = KnowledgeProposal(
            source_type=source_type,
            source_id=source_id,
            status=ProposalStatus.DRAFT.value,
            title=title,
            category=category,
            content_markdown=markdown,
            destination=ProposalDestination.CREATE.value,
            version=1,
            summary_quality=quality,
            author=author,
        )
        db.add(proposal)
        db.commit()
        db.refresh(proposal)

        record_audit_event(
            db=db,
            event_type="kb_proposal_created",
            request_id=source_id if source_type == "support_request" else None,
            payload={
                "proposal_id": proposal.id,
                "source_type": source_type,
                "source_id": source_id,
                "title": proposal.title,
                "quality": quality,
            },
        )
        return proposal

    @staticmethod
    def update_proposal(
        db: Session,
        proposal_id: str,
        title: Optional[str] = None,
        content_markdown: Optional[str] = None,
        destination: Optional[str] = None,
        target_kb_slug: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> KnowledgeProposal:
        """Updates a draft or failed proposal before approval."""
        prop = KnowledgeProposalManager.get_proposal(db, proposal_id)
        if prop.status not in (ProposalStatus.DRAFT.value, ProposalStatus.PUBLISHING_FAILED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Impossibile modificare una proposta in stato '{prop.status}'. "
                    "Modifiche permesse solo su 'draft' o 'publishing_failed'."
                ),
            )

        if title is not None:
            prop.title = redact_secrets(title.strip())
        if content_markdown is not None:
            prop.content_markdown = redact_secrets(content_markdown)
        if destination is not None:
            if destination not in (ProposalDestination.CREATE.value, ProposalDestination.UPDATE.value):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"destination '{destination}' non valida. Usa 'create' o 'update'.",
                )
            prop.destination = destination
        if target_kb_slug is not None:
            prop.target_kb_slug = target_kb_slug.strip() or None

        prop.updated_at = utc_now()
        db.commit()
        db.refresh(prop)

        record_audit_event(
            db=db,
            event_type="kb_proposal_edited",
            payload={
                "proposal_id": prop.id,
                "title": prop.title,
                "destination": prop.destination,
                "notes": redact_secrets(notes) if notes else None,
            },
        )
        return prop

    @staticmethod
    def reject_proposal(
        db: Session,
        proposal_id: str,
        reason: Optional[str] = None,
        author: str = "technician_demo",
    ) -> KnowledgeProposal:
        """Rejects a draft proposal."""
        prop = KnowledgeProposalManager.get_proposal(db, proposal_id)
        if prop.status != ProposalStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Impossibile rifiutare una proposta in stato '{prop.status}'.",
            )

        prop.status = ProposalStatus.REJECTED.value
        prop.rejection_reason = redact_secrets(reason.strip()) if reason else "Rifiutata dal tecnico."
        prop.updated_at = utc_now()
        db.commit()
        db.refresh(prop)

        record_audit_event(
            db=db,
            event_type="kb_proposal_rejected",
            payload={"proposal_id": prop.id, "reason": prop.rejection_reason, "author": author},
        )
        return prop

    @staticmethod
    def find_duplicates(
        db: Session,
        proposal_id: str,
        rag_service: KnowledgeRetrievalService,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Searches existing approved KB documents via RAG to check for potential overlaps."""
        prop = KnowledgeProposalManager.get_proposal(db, proposal_id)
        candidates: List[Dict[str, Any]] = []

        try:
            search_res = rag_service.search(query=prop.title, top_k=top_k)
            for item in search_res:
                slug_val = Path(item.source_path).name if item.source_path else item.doc_id
                preview_val = item.text[:200] if item.text else ""
                candidates.append({
                    "doc_id": item.doc_id,
                    "title": item.doc_title,
                    "category": item.category,
                    "heading": item.heading,
                    "source_path": item.source_path,
                    "slug": slug_val,
                    "score": round(item.score, 4),
                    "similarity": round(item.score, 4),
                    "summary": preview_val,
                    "preview": preview_val,
                })
        except Exception as exc:
            logger.warning(f"Duplicate search in RAG failed ({exc}); returning empty candidates.")

        return candidates

    @staticmethod
    def approve_and_publish(
        db: Session,
        proposal_id: str,
        rag_service: KnowledgeRetrievalService,
        author: str = "technician_demo",
        destination: Optional[str] = None,
        target_kb_slug: Optional[str] = None,
        base_kb_dir: Optional[Path] = None,
    ) -> KnowledgeProposal:
        """Validates front matter, writes Markdown file atomically, and reindexes RAG."""
        prop = KnowledgeProposalManager.get_proposal(db, proposal_id)

        # Concurrency & state validation
        if prop.status not in (ProposalStatus.DRAFT.value, ProposalStatus.PUBLISHING_FAILED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La proposta è già in stato '{prop.status}'. Impossibile procedere alla pubblicazione.",
            )

        if destination is not None:
            prop.destination = destination
        if target_kb_slug is not None:
            prop.target_kb_slug = target_kb_slug

        kb_dir = (base_kb_dir or Path("knowledge_base")).resolve()
        if not kb_dir.exists():
            kb_dir.mkdir(parents=True, exist_ok=True)

        # 1. Parse and validate Front Matter
        try:
            fm, body = parse_markdown_content(prop.content_markdown, source_path=f"{prop.id}.md")
        except KBParseException as parse_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validazione Front Matter fallita: {parse_err}",
            )

        # 2. Determine target file path safely within kb_dir (Path Traversal Protection)
        today_str = datetime.date.today().isoformat()
        if prop.destination == ProposalDestination.UPDATE.value and prop.target_kb_slug:
            # Updating existing document
            target_slug = prop.target_kb_slug.strip()
            if ".." in target_slug or "/" in target_slug or "\\" in target_slug:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Path traversal non consentito nello slug del documento target.",
                )
            target_filename = sanitize_filename(target_slug)
            target_path = (kb_dir / target_filename).resolve()
        else:
            # Creating new document
            clean_title_slug = re.sub(r"[^A-Za-z0-9]", "_", fm.title.lower()).strip("_")
            target_filename = sanitize_filename(f"{fm.id.lower()}_{clean_title_slug}")
            target_path = (kb_dir / target_filename).resolve()

        if not target_path.is_relative_to(kb_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Path traversal non consentito: il file di destinazione "
                    "deve risiedere nella cartella knowledge_base."
                ),
            )

        # Increment version if updating existing
        new_version = prop.version
        if prop.destination == ProposalDestination.UPDATE.value and target_path.exists():
            new_version += 1

        # 3. Reconstruct canonical approved Markdown with status: approved
        tags_str = "\n".join(f"  - {t}" for t in fm.tags) if fm.tags else f"  - {fm.category}"
        author_val = fm.author or prop.author
        summary_val = (fm.summary or prop.title).replace('"', "'")

        approved_markdown = f"""---
id: {fm.id}
title: "{fm.title}"
category: {fm.category}
tags:
{tags_str}
status: approved
version: "{new_version}.0"
last_updated: "{today_str}"
author: "{author_val}"
summary: "{summary_val}"
---

{body.strip()}
"""

        # 4. Safe Atomic File Writing (.tmp -> rename)
        tmp_path = target_path.parent / f"{target_path.name}.tmp"
        try:
            # Backup original if updating
            if target_path.exists():
                bak_path = target_path.parent / f"{target_path.name}.bak"
                try:
                    target_path.replace(bak_path)
                except Exception as bak_err:
                    logger.warning(f"Could not create backup for {target_path}: {bak_err}")

            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(approved_markdown)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, target_path)
        except Exception as write_err:
            logger.error(f"Failed to write file {target_path}: {write_err}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            prop.status = ProposalStatus.PUBLISHING_FAILED.value
            prop.updated_at = utc_now()
            db.commit()

            record_audit_event(
                db=db,
                event_type="kb_publish_failed",
                payload={"proposal_id": prop.id, "error": str(write_err)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore scrittura file Markdown su disco: {write_err}",
            )

        # 5. Reindex RAG
        record_audit_event(
            db=db,
            event_type="kb_publish_started",
            payload={"proposal_id": prop.id, "file_path": str(target_path)},
        )

        try:
            reindex_res = rag_service.index_documents(clean_obsolete=True)
            logger.info(
                f"RAG re-indexing succeeded after KB proposal publish: "
                f"approved={reindex_res.documents_approved}, chunks={reindex_res.chunks_created}"
            )
        except Exception as idx_err:
            logger.error(f"RAG re-indexing failed after writing {target_path}: {idx_err}")
            prop.status = ProposalStatus.PUBLISHING_FAILED.value
            prop.updated_at = utc_now()
            db.commit()

            record_audit_event(
                db=db,
                event_type="kb_publish_failed",
                payload={"proposal_id": prop.id, "error": str(idx_err)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"File salvato con successo ({target_path.name}), ma re-indicizzazione RAG fallita. "
                    "La proposta è marcata come 'publishing_failed' per consentire il retry."
                ),
            )

        # 6. Succeeded: Update proposal record
        prop.status = ProposalStatus.APPROVED.value
        prop.version = new_version
        prop.content_markdown = approved_markdown
        prop.published_path = str(target_path.relative_to(kb_dir.parent))
        prop.published_at = utc_now()
        prop.updated_at = utc_now()
        db.commit()
        db.refresh(prop)

        record_audit_event(
            db=db,
            event_type="kb_publish_succeeded",
            payload={
                "proposal_id": prop.id,
                "doc_id": fm.id,
                "file_path": prop.published_path,
                "version": prop.version,
                "author": author,
            },
        )
        record_audit_event(
            db=db,
            event_type="kb_reindexed",
            payload={"documents_approved": reindex_res.documents_approved, "chunks": reindex_res.chunks_created},
        )
        return prop
