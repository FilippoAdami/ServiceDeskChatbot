from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import (
    ActivityType,
    Conversation,
    Incident,
    IncidentStatus,
    SupportRequest,
    Ticket,
    TicketActivity,
    TicketPriority,
    TicketStatus,
)
from backend.app.ticketing.adapter import LocalTicketingAdapter


def test_create_ticket_persists_and_emits_audit(db_session: Session) -> None:
    conv = Conversation(title="Problema accesso Outlook")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Errore password Outlook",
        description="Non riesco ad accedere alla casella di posta",
    )
    db_session.add(req)
    db_session.commit()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Problema accesso Outlook",
        summary="L'utente non riesce ad accedere con password=SuperSecret123!",
        symptoms="Errore password errata",
        attempted_steps="Verifica password e riavvio",
        diagnostic_findings="Possibile blocco account AD",
        source_refs=["KB-AUTH-001"],
        summary_quality="llm",
        priority=TicketPriority.HIGH.value,
    )

    assert ticket.id.startswith("tick_")
    assert ticket.status == TicketStatus.OPEN.value
    assert ticket.priority == TicketPriority.HIGH.value
    assert ticket.summary_quality == "llm"
    assert "SuperSecret123!" not in ticket.summary
    assert "[REDACTED_PASSWORD]" in ticket.summary
    assert ticket.source_refs == ["KB-AUTH-001"]

    # Check creation activity
    activities = list(db_session.query(TicketActivity).filter_by(ticket_id=ticket.id).all())
    assert len(activities) == 1
    assert activities[0].activity_type == ActivityType.CREATED.value


def test_create_ticket_idempotency_prevents_duplicates(db_session: Session) -> None:
    conv = Conversation(title="Connessione VPN")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Disconnessione frequente VPN",
        description="La VPN cade ogni 10 minuti",
    )
    db_session.add(req)
    db_session.commit()

    # First creation call
    t1 = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="VPN drop",
        summary="Sintesi 1",
        symptoms="Disconnessione",
        attempted_steps="Reset adapter",
        diagnostic_findings="Timeout handshake",
    )

    # Second creation call (e.g. user retries or double click)
    t2 = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="VPN drop retry",
        summary="Sintesi 2",
        symptoms="Disconnessione",
        attempted_steps="Reset adapter",
        diagnostic_findings="Timeout handshake",
    )

    assert t1.id == t2.id

    # Verify only 1 ticket exists for this support request in DB
    count = db_session.query(Ticket).filter_by(support_request_id=req.id).count()
    assert count == 1


def test_ticket_state_machine_valid_transitions(db_session: Session) -> None:
    conv = Conversation(title="Test State Machine")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Test req",
        description="Test desc",
    )
    db_session.add(req)
    db_session.commit()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="State test",
        summary="Test",
        symptoms="Test",
        attempted_steps="Test",
        diagnostic_findings="Test",
    )
    assert ticket.status == TicketStatus.OPEN.value

    # open -> in_progress
    ticket = LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.IN_PROGRESS.value, author="tech_1")
    assert ticket.status == TicketStatus.IN_PROGRESS.value

    # in_progress -> resolved
    ticket = LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.RESOLVED.value, author="tech_1")
    assert ticket.status == TicketStatus.RESOLVED.value

    # resolved -> closed
    ticket = LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.CLOSED.value, author="tech_1")
    assert ticket.status == TicketStatus.CLOSED.value

    # closed -> open (controlled reopening)
    ticket = LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.OPEN.value, author="tech_1")
    assert ticket.status == TicketStatus.OPEN.value


def test_ticket_state_machine_invalid_transitions_409(db_session: Session) -> None:
    conv = Conversation(title="Test Invalid Transitions")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Test invalid",
        description="Test invalid",
    )
    db_session.add(req)
    db_session.commit()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="State test",
        summary="Test",
        symptoms="Test",
        attempted_steps="Test",
        diagnostic_findings="Test",
    )

    # open -> resolved is invalid (must go to in_progress first)
    with pytest.raises(HTTPException) as exc_info:
        LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.RESOLVED.value)
    assert exc_info.value.status_code == 409
    assert "Transizione di stato non consentita" in exc_info.value.detail


def test_add_note_redacts_secrets_and_records_activity(db_session: Session) -> None:
    conv = Conversation(title="Note test")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(conversation_id=conv.id, title="Note req", description="Note desc")
    db_session.add(req)
    db_session.commit()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Note test",
        summary="Test",
        symptoms="Test",
        attempted_steps="Test",
        diagnostic_findings="Test",
    )

    activity = LocalTicketingAdapter.add_note(
        db=db_session,
        ticket_id=ticket.id,
        content=(
            "Contattato l'utente al telefono. Token temporaneo fornito: "
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        ),
        author="technician_mario",
    )

    assert activity.activity_type == ActivityType.NOTE.value
    assert activity.author == "technician_mario"
    assert "Bearer eyJhbGci" not in activity.content
    assert "[REDACTED_TOKEN]" in activity.content


def test_link_and_unlink_incident(db_session: Session) -> None:
    incident = Incident(
        id="INC-TEST-001",
        service="Email",
        title="Degrado Exchange",
        symptoms="Ritardi posta",
        summary="Disservizio generale cluster posta",
        status=IncidentStatus.MONITORING.value,
    )
    db_session.add(incident)

    conv = Conversation(title="Incident test")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(conversation_id=conv.id, title="Test req", description="Test desc")
    db_session.add(req)
    db_session.commit()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Email ritardo",
        summary="Email lente",
        symptoms="Ricezione lenta",
        attempted_steps="Controllo webmail",
        diagnostic_findings="Correlabile a disservizio",
    )

    # Link incident
    updated_ticket = LocalTicketingAdapter.link_incident(db_session, ticket.id, "INC-TEST-001")
    assert updated_ticket.incident_id == "INC-TEST-001"

    # Unlink incident
    unlinked_ticket = LocalTicketingAdapter.unlink_incident(db_session, ticket.id)
    assert unlinked_ticket.incident_id is None
