from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.ticket import (
    TicketActivityItem,
    TicketDetail,
    TicketIncidentLinkRequest,
    TicketItem,
    TicketListResponse,
    TicketNoteCreateRequest,
    TicketStatusUpdateRequest,
)
from backend.app.ticketing.adapter import LocalTicketingAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtra per stato ticket"),
    category: Optional[str] = Query(None, description="Filtra per categoria ticket"),
    incident_id: Optional[str] = Query(None, description="Filtra per incidente collegato"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    """Restituisce l'elenco paginato dei ticket di supporto creati."""
    items, total = LocalTicketingAdapter.list_tickets(
        db=db,
        status_filter=status_filter,
        category_filter=category,
        incident_id=incident_id,
        limit=limit,
        offset=offset,
    )
    return TicketListResponse(
        items=[TicketItem.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
) -> TicketDetail:
    """Restituisce il dettaglio completo di un ticket, inclusa la cronologia attività."""
    ticket = LocalTicketingAdapter.get_ticket(db, ticket_id)
    return TicketDetail.model_validate(ticket)


@router.post("/{ticket_id}/status", response_model=TicketDetail)
def update_ticket_status(
    ticket_id: str,
    payload: TicketStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> TicketDetail:
    """Aggiorna lo stato del ticket validando la macchina a stati (409 Conflict se invalida)."""
    ticket = LocalTicketingAdapter.update_status(
        db=db,
        ticket_id=ticket_id,
        new_status=payload.status,
        author=payload.author,
        note=payload.note,
    )
    return TicketDetail.model_validate(ticket)


@router.post("/{ticket_id}/notes", response_model=TicketActivityItem, status_code=status.HTTP_201_CREATED)
def add_ticket_note(
    ticket_id: str,
    payload: TicketNoteCreateRequest,
    db: Session = Depends(get_db),
) -> TicketActivityItem:
    """Aggiunge una nota tecnica sanificata alla timeline del ticket."""
    activity = LocalTicketingAdapter.add_note(
        db=db,
        ticket_id=ticket_id,
        content=payload.content,
        author=payload.author,
    )
    return TicketActivityItem.model_validate(activity)


@router.post("/{ticket_id}/incident", response_model=TicketDetail)
def link_ticket_incident(
    ticket_id: str,
    payload: TicketIncidentLinkRequest,
    db: Session = Depends(get_db),
) -> TicketDetail:
    """Collega o scollega un incidente noto al ticket."""
    if payload.incident_id:
        ticket = LocalTicketingAdapter.link_incident(
            db=db,
            ticket_id=ticket_id,
            incident_id=payload.incident_id,
            author=payload.author,
        )
    else:
        ticket = LocalTicketingAdapter.unlink_incident(
            db=db,
            ticket_id=ticket_id,
            author=payload.author,
        )
    return TicketDetail.model_validate(ticket)
