from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.core.audit import record_audit_event
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import (
    ActivityType,
    Incident,
    SupportRequest,
    Ticket,
    TicketActivity,
    TicketPriority,
    TicketStatus,
    utc_now,
)
from backend.app.knowledge.categories import normalize_task_category

logger = logging.getLogger(__name__)

# Explicit, validated state machine for tickets
VALID_TICKET_TRANSITIONS: Dict[str, Set[str]] = {
    TicketStatus.OPEN.value: {TicketStatus.IN_PROGRESS.value, TicketStatus.CLOSED.value},
    TicketStatus.IN_PROGRESS.value: {
        TicketStatus.RESOLVED.value,
        TicketStatus.OPEN.value,
        TicketStatus.CLOSED.value,
    },
    TicketStatus.RESOLVED.value: {TicketStatus.IN_PROGRESS.value, TicketStatus.CLOSED.value},
    TicketStatus.CLOSED.value: {TicketStatus.OPEN.value},
}


class LocalTicketingAdapter:
    """Persistent local adapter simulating an enterprise ticketing service.

    Enforces state transitions, secret redaction, audit logging, and idempotency.
    """

    @staticmethod
    def create_ticket(
        db: Session,
        support_request_id: str,
        conversation_id: str,
        title: str,
        summary: str,
        symptoms: str,
        attempted_steps: str,
        diagnostic_findings: str,
        source_refs: Optional[List[str]] = None,
        summary_quality: str = "llm",
        priority: str = TicketPriority.MEDIUM.value,
        incident_id: Optional[str] = None,
    ) -> Ticket:
        """Create a new ticket or return existing non-closed ticket for the support request (idempotent)."""
        # 1. Idempotency check: reuse active ticket if already open/in_progress/resolved
        existing_ticket = db.scalar(
            select(Ticket)
            .where(
                Ticket.support_request_id == support_request_id,
                Ticket.status != TicketStatus.CLOSED.value,
            )
            .order_by(Ticket.created_at.desc())
        )
        if existing_ticket:
            logger.info(
                "Idempotent ticket lookup: active ticket %s already exists for request %s",
                existing_ticket.id,
                support_request_id,
            )
            return existing_ticket

        # 2. Sanitize and redact all fields
        clean_title = redact_secrets(title.strip())[:255]
        clean_summary = redact_secrets(summary.strip())
        clean_symptoms = redact_secrets(symptoms.strip())
        clean_attempted = redact_secrets(attempted_steps.strip())
        clean_findings = redact_secrets(diagnostic_findings.strip())

        # Validate priority
        valid_priorities = {p.value for p in TicketPriority}
        safe_priority = priority if priority in valid_priorities else TicketPriority.MEDIUM.value

        # 3. Create ticket instance
        ticket = Ticket(
            support_request_id=support_request_id,
            conversation_id=conversation_id,
            incident_id=incident_id,
            status=TicketStatus.OPEN.value,
            priority=safe_priority,
            title=clean_title,
            summary=clean_summary,
            symptoms=clean_symptoms,
            attempted_steps=clean_attempted,
            diagnostic_findings=clean_findings,
            source_refs=source_refs or [],
            summary_quality=summary_quality if summary_quality in ("llm", "fallback") else "fallback",
        )
        db.add(ticket)
        db.flush()

        # 4. Add initial creation activity
        creation_activity = TicketActivity(
            ticket_id=ticket.id,
            author="system",
            author_role="system",
            activity_type=ActivityType.CREATED.value,
            content="Ticket creato dal sistema a seguito di escalation dal chatbot assistente.",
            new_status=TicketStatus.OPEN.value,
        )
        db.add(creation_activity)

        # 5. Record structured audit event
        record_audit_event(
            db=db,
            event_type="ticket_created",
            conversation_id=conversation_id,
            request_id=support_request_id,
            payload={
                "ticket_id": ticket.id,
                "priority": safe_priority,
                "summary_quality": ticket.summary_quality,
                "sources_count": len(ticket.source_refs or []),
            },
        )

        db.commit()
        db.refresh(ticket)
        logger.info("Ticket %s successfully created and committed for request %s", ticket.id, support_request_id)
        return ticket

    @staticmethod
    def get_ticket(db: Session, ticket_id: str) -> Ticket:
        """Retrieve a ticket by ID or raise 404."""
        ticket = db.scalar(
            select(Ticket)
            .options(joinedload(Ticket.support_request))
            .where(Ticket.id == ticket_id)
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket '{ticket_id}' non trovato",
            )
        return ticket

    @staticmethod
    def list_tickets(
        db: Session,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        incident_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Ticket], int]:
        """List tickets with optional status, category, and incident filtering and pagination."""
        query = select(Ticket).options(joinedload(Ticket.support_request))
        if status_filter:
            query = query.where(Ticket.status == status_filter)
        if incident_id:
            query = query.where(Ticket.incident_id == incident_id)
        if category_filter and category_filter != "all":
            norm_cat = normalize_task_category(category_filter)
            query = query.join(SupportRequest, Ticket.support_request_id == SupportRequest.id).where(
                or_(
                    SupportRequest.final_category == norm_cat,
                    SupportRequest.initial_category == norm_cat,
                    SupportRequest.final_category == category_filter,
                    SupportRequest.initial_category == category_filter,
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        # Fetch items
        items = list(
            db.scalars(
                query.order_by(Ticket.updated_at.desc(), Ticket.created_at.desc()).limit(limit).offset(offset)
            )
            .unique()
            .all()
        )
        return items, total

    @staticmethod
    def update_status(
        db: Session,
        ticket_id: str,
        new_status: str,
        author: str = "technician_demo",
        author_role: str = "technician",
        note: Optional[str] = None,
    ) -> Ticket:
        """Update ticket status according to allowed transitions or raise 409 Conflict."""
        ticket = LocalTicketingAdapter.get_ticket(db, ticket_id)
        old_status = ticket.status

        # If identical status, treat as no-op or note-only
        if new_status == old_status:
            if note:
                LocalTicketingAdapter.add_note(db, ticket_id, note, author, author_role)
            return ticket

        # Validate transition
        allowed_transitions = VALID_TICKET_TRANSITIONS.get(old_status, set())
        if new_status not in allowed_transitions:
            allowed_list = ", ".join(sorted(allowed_transitions)) or "nessuna"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Transizione di stato non consentita da '{old_status}' a '{new_status}'. "
                    f"Transizioni permesse: [{allowed_list}]."
                ),
            )

        ticket.status = new_status
        ticket.updated_at = utc_now()

        # Clean note if provided
        content = (
            redact_secrets(note.strip())
            if note and note.strip()
            else f"Stato modificato da '{old_status}' a '{new_status}'."
        )

        activity = TicketActivity(
            ticket_id=ticket.id,
            author=author,
            author_role=author_role,
            activity_type=ActivityType.STATUS_CHANGE.value,
            content=content,
            old_status=old_status,
            new_status=new_status,
        )
        db.add(activity)

        record_audit_event(
            db=db,
            event_type="ticket_status_updated",
            conversation_id=ticket.conversation_id,
            request_id=ticket.support_request_id,
            payload={
                "ticket_id": ticket.id,
                "old_status": old_status,
                "new_status": new_status,
                "author": author,
            },
        )

        db.commit()
        db.refresh(ticket)
        logger.info("Ticket %s status updated: %s -> %s by %s", ticket.id, old_status, new_status, author)
        return ticket

    @staticmethod
    def add_note(
        db: Session,
        ticket_id: str,
        content: str,
        author: str = "technician_demo",
        author_role: str = "technician",
    ) -> TicketActivity:
        """Add a sanitized technical note to a ticket activity timeline."""
        ticket = LocalTicketingAdapter.get_ticket(db, ticket_id)

        clean_text = redact_secrets(content.strip())
        if not clean_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Il testo della nota non può essere vuoto.",
            )

        activity = TicketActivity(
            ticket_id=ticket.id,
            author=author,
            author_role=author_role,
            activity_type=ActivityType.NOTE.value,
            content=clean_text,
        )
        ticket.updated_at = utc_now()
        db.add(activity)

        record_audit_event(
            db=db,
            event_type="ticket_note_added",
            conversation_id=ticket.conversation_id,
            request_id=ticket.support_request_id,
            payload={
                "ticket_id": ticket.id,
                "author": author,
                "author_role": author_role,
                "content_length": len(clean_text),
            },
        )

        db.commit()
        db.refresh(activity)
        logger.info("Note added to ticket %s by %s", ticket.id, author)
        return activity

    @staticmethod
    def link_incident(
        db: Session,
        ticket_id: str,
        incident_id: str,
        author: str = "technician_demo",
    ) -> Ticket:
        """Correlate a ticket with a known shared incident."""
        ticket = LocalTicketingAdapter.get_ticket(db, ticket_id)
        incident = db.scalar(select(Incident).where(Incident.id == incident_id))
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incidente '{incident_id}' non trovato",
            )

        if ticket.incident_id == incident_id:
            return ticket

        ticket.incident_id = incident_id
        ticket.updated_at = utc_now()

        activity = TicketActivity(
            ticket_id=ticket.id,
            author=author,
            author_role="technician",
            activity_type=ActivityType.INCIDENT_LINKED.value,
            content=f"Ticket collegato all'incidente noto {incident.id} ({incident.title}).",
        )
        db.add(activity)

        record_audit_event(
            db=db,
            event_type="ticket_incident_linked",
            conversation_id=ticket.conversation_id,
            request_id=ticket.support_request_id,
            payload={
                "ticket_id": ticket.id,
                "incident_id": incident_id,
                "author": author,
            },
        )

        db.commit()
        db.refresh(ticket)
        logger.info("Ticket %s linked to incident %s", ticket.id, incident_id)
        return ticket

    @staticmethod
    def unlink_incident(
        db: Session,
        ticket_id: str,
        author: str = "technician_demo",
    ) -> Ticket:
        """Unlink a ticket from its currently associated incident."""
        ticket = LocalTicketingAdapter.get_ticket(db, ticket_id)
        if not ticket.incident_id:
            return ticket

        old_incident_id = ticket.incident_id
        ticket.incident_id = None
        ticket.updated_at = utc_now()

        activity = TicketActivity(
            ticket_id=ticket.id,
            author=author,
            author_role="technician",
            activity_type=ActivityType.INCIDENT_UNLINKED.value,
            content=f"Ticket scollegato dall'incidente noto {old_incident_id}.",
        )
        db.add(activity)

        record_audit_event(
            db=db,
            event_type="ticket_incident_unlinked",
            conversation_id=ticket.conversation_id,
            request_id=ticket.support_request_id,
            payload={
                "ticket_id": ticket.id,
                "incident_id": old_incident_id,
                "author": author,
            },
        )

        db.commit()
        db.refresh(ticket)
        logger.info("Ticket %s unlinked from incident %s", ticket.id, old_incident_id)
        return ticket
