from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent.orchestrator import RESOLUTION_CONFIRM_PATTERN
from backend.app.db.models import (
    AgentPhase,
    AuditEvent,
    Conversation,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
    Ticket,
    TicketStatus,
)


def test_resolution_confirm_pattern_matches_user_phrases() -> None:
    """Verify that various Italian resolution confirmation phrases match RESOLUTION_CONFIRM_PATTERN."""
    phrases = [
        "grazie mille, sono riuscito a resettarla e ad acccedere",
        "sono riuscita a reimpostare la password",
        "ora funziona perfettamente grazie",
        "tutto risolto, grazie dell'aiuto",
        "ho risolto il problema di accesso",
        "accesso riuscito!",
        "perfetto grazie mille!",
    ]
    for p in phrases:
        assert RESOLUTION_CONFIRM_PATTERN.search(p) is not None, f"Failed to match: {p}"


def test_confirm_resolution_endpoint_user_success(client: TestClient, db_session: Session) -> None:
    """Verify user explicit click on 'Sì, problema risolto' closes the SupportRequest."""
    conv = Conversation(title="Test Reset Password", user_id="user_demo_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="non ricordo la password del mio account",
        description="non ricordo la password del mio account",
        status=RequestStatus.OPEN.value,
        phase=AgentPhase.DIAGNOSIS.value,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    res = client.post(
        f"/api/requests/{req.id}/confirm-resolution",
        json={"confirmed_by_user": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == req.id
    assert data["status"] == RequestStatus.CLOSED.value
    assert data["outcome"] == RequestOutcome.RESOLVED_CONFIRMED.value
    assert data["phase"] == AgentPhase.FINALIZATION.value

    # Verify audit event
    audit = db_session.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.request_id == req.id,
            AuditEvent.event_type == "support_request_resolved_confirmed",
        )
        .order_by(AuditEvent.created_at.desc())
    )
    assert audit is not None
    assert audit.payload["confirmed_by_user"] is True
    assert audit.payload["status"] == "closed"


def test_confirm_resolution_endpoint_auto_timer(client: TestClient, db_session: Session) -> None:
    """Verify 2-minute timer expiry auto-close triggers closure with confirmed_by_user=False."""
    conv = Conversation(title="Test Auto Timer", user_id="user_demo_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema Wi-Fi risolto",
        description="Problema di connessione Wi-Fi",
        status=RequestStatus.OPEN.value,
        phase=AgentPhase.FINALIZATION.value,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    res = client.post(
        f"/api/requests/{req.id}/confirm-resolution",
        json={"confirmed_by_user": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == RequestStatus.CLOSED.value
    assert data["outcome"] == RequestOutcome.RESOLVED_CONFIRMED.value

    # Verify audit event payload
    audit = db_session.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.request_id == req.id,
            AuditEvent.event_type == "support_request_resolved_confirmed",
        )
        .order_by(AuditEvent.created_at.desc())
    )
    assert audit is not None
    assert audit.payload["confirmed_by_user"] is False


def test_confirm_resolution_rejected_if_open_ticket_exists(client: TestClient, db_session: Session) -> None:
    """Invariant: Open technician tickets CANNOT be closed by bot or user confirmation."""
    conv = Conversation(title="Test Ticket Guard", user_id="user_demo_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Guasto Monitor",
        description="Monitor rotto",
        status=RequestStatus.OPEN.value,
        phase=AgentPhase.FINALIZATION.value,
        escalation_requested=True,
    )
    db_session.add(req)
    db_session.flush()

    ticket = Ticket(
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Guasto Monitor - Escalation",
        summary="Monitor rotto",
        symptoms="Schermo nero",
        attempted_steps="Riavvio PC",
        diagnostic_findings="Nessun segnale video",
        status=TicketStatus.OPEN.value,
    )
    db_session.add(ticket)
    db_session.commit()


    res = client.post(
        f"/api/requests/{req.id}/confirm-resolution",
        json={"confirmed_by_user": True},
    )
    assert res.status_code == 400
    assert "tecnici non possono essere chiusi" in res.json()["detail"]

    # Verify request status remains open
    db_session.refresh(req)
    assert req.status == RequestStatus.OPEN.value


def test_reopen_support_request(client: TestClient, db_session: Session) -> None:
    """Verify reopening request keeps status open and reverts to diagnosis phase."""
    conv = Conversation(title="Test Reopen", user_id="user_demo_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Test Reopen",
        description="Richiesta da continuare",
        status=RequestStatus.CLOSED.value,
        phase=AgentPhase.FINALIZATION.value,
        outcome=RequestOutcome.RESOLVED_CONFIRMED.value,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    res = client.post(f"/api/requests/{req.id}/reopen")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == RequestStatus.OPEN.value
    assert data["phase"] == AgentPhase.DIAGNOSIS.value
    assert data["outcome"] is None


def test_message_sending_blocked_in_resolved_conversation(client: TestClient, db_session: Session) -> None:
    """Verify that once a support request is resolved, the conversation is archived and messages are blocked."""
    conv = Conversation(title="Test Resolved Conversation", user_id="user_demo_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema stampante",
        description="Riavviata e funzionante",
        status=RequestStatus.OPEN.value,
        phase=AgentPhase.FINALIZATION.value,
    )
    db_session.add(req)
    db_session.commit()

    # Confirm resolution
    res_confirm = client.post(
        f"/api/requests/{req.id}/confirm-resolution",
        json={"confirmed_by_user": True},
    )
    assert res_confirm.status_code == 200

    # Conversation should be archived
    db_session.refresh(conv)
    assert conv.status == "archived"

    # Attempt to send message in the closed conversation
    res_msg = client.post(
        f"/api/conversations/{conv.id}/messages",
        json={"content": "Ho ancora una domanda..."},
    )
    assert res_msg.status_code == 400
    assert "risolta" in res_msg.json()["detail"].lower()

