from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditEvent, Conversation, Ticket
from backend.app.db.session import get_db
from backend.app.schemas.audit import (
    AuditConversationsResponse,
    AuditConversationSummary,
    AuditEventItem,
    AuditEventsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit & Debug"])

EVENT_CATEGORIES: Dict[str, str] = {
    "conversation_created": "employee",
    "message_sent": "employee",
    "support_request_created": "employee",
    "support_request_resolved_confirmed": "employee",
    "support_request_reopened": "employee",
    "assistant_turn_completed": "employee",
    "technician_message_sent": "technician",
    "technician_assistant_responded": "technician",
    "ticket_created": "technician",
    "ticket_status_updated": "technician",
    "ticket_note_added": "technician",
    "incident_linked": "technician",
    "incident_unlinked": "technician",
    "kb_proposal_generated": "technician",
    "kb_proposal_approved": "technician",
    "kb_proposal_rejected": "technician",
    "kb_proposal_published": "technician",
}

EVENT_LABELS: Dict[str, str] = {
    "conversation_created": "Apertura nuova chat",
    "message_sent": "Messaggio inviato dall'utente",
    "support_request_created": "Nuova richiesta di supporto IT creata",
    "support_request_resolved_confirmed": "Problema confermato risolto dall'utente",
    "support_request_reopened": "Richiesta di supporto riaperta",
    "assistant_turn_completed": "Risposta Assistente Dipendenti (AI)",
    "technician_message_sent": "Messaggio inviato dal Tecnico",
    "technician_assistant_responded": "Risposta Copilota Tecnico (AI)",
    "ticket_created": "Ticket IT creato (Escalation)",
    "ticket_status_updated": "Aggiornamento stato ticket",
    "ticket_note_added": "Nuova nota tecnica registrata",
    "incident_linked": "Incidente aziendale collegato",
    "incident_unlinked": "Incidente aziendale scollegato",
    "kb_proposal_generated": "Bozza KB generata da risoluzione",
    "kb_proposal_approved": "Bozza KB approvata dal tecnico",
    "kb_proposal_rejected": "Bozza KB respinta dal tecnico",
    "kb_proposal_published": "Nuovo articolo KB pubblicato",
}


@router.get("/events", response_model=AuditEventsResponse)
def list_audit_events(
    category: Optional[str] = Query(
        None,
        description="Filtra per categoria: employee, technician, system o all",
    ),
    conversation_id: Optional[str] = Query(
        None,
        description="Filtra per ID conversazione specifica",
    ),
    event_type: Optional[str] = Query(
        None,
        description="Filtra per tipo di evento specifico",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> AuditEventsResponse:
    """Restituisce il log cronologico strutturato degli eventi di audit per il debugging."""
    stmt = select(AuditEvent)
    count_stmt = select(func.count()).select_from(AuditEvent)

    if category and category != "all":
        if category == "employee":
            allowed_types = [k for k, v in EVENT_CATEGORIES.items() if v == "employee"]
            stmt = stmt.where(AuditEvent.event_type.in_(allowed_types))
            count_stmt = count_stmt.where(AuditEvent.event_type.in_(allowed_types))
        elif category == "technician":
            allowed_types = [k for k, v in EVENT_CATEGORIES.items() if v == "technician"]
            stmt = stmt.where(AuditEvent.event_type.in_(allowed_types))
            count_stmt = count_stmt.where(AuditEvent.event_type.in_(allowed_types))
        elif category == "system":
            known_types = list(EVENT_CATEGORIES.keys())
            stmt = stmt.where(AuditEvent.event_type.not_in(known_types))
            count_stmt = count_stmt.where(AuditEvent.event_type.not_in(known_types))

    if conversation_id:
        stmt = stmt.where(AuditEvent.conversation_id == conversation_id)
        count_stmt = count_stmt.where(AuditEvent.conversation_id == conversation_id)

    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
        count_stmt = count_stmt.where(AuditEvent.event_type == event_type)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(desc(AuditEvent.created_at)).offset(offset).limit(limit)
    events = db.execute(stmt).scalars().all()

    # Preload tickets for conversations in this event slice
    conv_ids: Set[str] = {e.conversation_id for e in events if e.conversation_id}
    tickets_map: Dict[str, str] = {}
    if conv_ids:
        t_stmt = select(Ticket.conversation_id, Ticket.id).where(Ticket.conversation_id.in_(conv_ids))
        for row_cid, row_tid in db.execute(t_stmt).all():
            if row_cid:
                tickets_map[row_cid] = str(row_tid)

    items: List[AuditEventItem] = []
    for e in events:
        cat = EVENT_CATEGORIES.get(e.event_type, "system")
        label = EVENT_LABELS.get(e.event_type, e.event_type.replace("_", " ").title())
        resolved_ticket_id: Optional[str] = None
        if isinstance(e.payload, dict) and "ticket_id" in e.payload and e.payload["ticket_id"]:
            resolved_ticket_id = str(e.payload["ticket_id"])
        if not resolved_ticket_id and e.conversation_id:
            resolved_ticket_id = tickets_map.get(e.conversation_id)

        items.append(
            AuditEventItem(
                id=e.id,
                event_type=e.event_type,
                category=cat,
                action_label=label,
                conversation_id=e.conversation_id,
                request_id=e.request_id,
                ticket_id=resolved_ticket_id,
                payload=e.payload or {},
                created_at=e.created_at,
            )
        )

    return AuditEventsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/conversations", response_model=AuditConversationsResponse)
def list_audit_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> AuditConversationsResponse:
    """Restituisce le conversazioni con statistiche eventi e ticket per il filtro thread."""
    total = db.scalar(select(func.count()).select_from(Conversation)) or 0
    conv_stmt = select(Conversation).order_by(desc(Conversation.updated_at)).offset(offset).limit(limit)
    conversations = db.execute(conv_stmt).scalars().all()

    conv_ids = [c.id for c in conversations]

    event_counts: Dict[str, int] = {}
    if conv_ids:
        evt_stmt = (
            select(AuditEvent.conversation_id, func.count(AuditEvent.id))
            .where(AuditEvent.conversation_id.in_(conv_ids))
            .group_by(AuditEvent.conversation_id)
        )
        for cid, cnt in db.execute(evt_stmt).all():
            if cid:
                event_counts[cid] = cnt

    ticket_map: Dict[str, Tuple[str, str]] = {}
    if conv_ids:
        t_stmt = select(Ticket.conversation_id, Ticket.id, Ticket.status).where(
            Ticket.conversation_id.in_(conv_ids)
        )
        for row_cid, row_tid, row_tstatus in db.execute(t_stmt).all():
            if row_cid:
                ticket_map[row_cid] = (str(row_tid), str(row_tstatus))

    items: List[AuditConversationSummary] = []
    for c in conversations:
        t_info = ticket_map.get(c.id)
        items.append(
            AuditConversationSummary(
                conversation_id=c.id,
                title=c.title or "Chat senza titolo",
                user_id=c.user_id,
                status=c.status,
                event_count=event_counts.get(c.id, 0),
                ticket_id=t_info[0] if t_info else None,
                ticket_status=t_info[1] if t_info else None,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return AuditConversationsResponse(items=items, total=total)
