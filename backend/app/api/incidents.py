from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Incident, Ticket
from backend.app.db.session import get_db
from backend.app.schemas.incident import IncidentDetail, IncidentItem, IncidentListResponse
from backend.app.schemas.ticket import TicketItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtra per stato incidente"),
    service: Optional[str] = Query(None, description="Filtra per servizio interessato"),
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    """Restituisce l'elenco degli incidenti noti con il conteggio dei ticket collegati."""
    query = select(Incident)
    if status_filter:
        query = query.where(Incident.status == status_filter)
    if service:
        query = query.where(Incident.service == service)

    incidents = list(db.scalars(query.order_by(Incident.created_at.desc())).all())

    items: list[IncidentItem] = []
    for inc in incidents:
        ticket_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.incident_id == inc.id)) or 0
        item = IncidentItem(
            id=inc.id,
            service=inc.service,
            title=inc.title,
            symptoms=inc.symptoms,
            summary=inc.summary,
            status=inc.status,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            ticket_count=ticket_count,
        )
        items.append(item)

    return IncidentListResponse(items=items, total=len(items))


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
) -> IncidentDetail:
    """Restituisce il dettaglio dell'incidente e i ticket collegati."""
    incident = db.scalar(select(Incident).where(Incident.id == incident_id))
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incidente '{incident_id}' non trovato",
        )

    linked_tickets = list(
        db.scalars(select(Ticket).where(Ticket.incident_id == incident.id).order_by(Ticket.updated_at.desc())).all()
    )

    return IncidentDetail(
        id=incident.id,
        service=incident.service,
        title=incident.title,
        symptoms=incident.symptoms,
        summary=incident.summary,
        status=incident.status,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        ticket_count=len(linked_tickets),
        tickets=[TicketItem.model_validate(t) for t in linked_tickets],
    )
