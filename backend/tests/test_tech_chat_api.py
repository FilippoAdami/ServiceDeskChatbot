from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.agent.tech_assistant import (
    TechnicianAssistantService,
    reset_tech_assistant_for_test,
)
from backend.app.db.models import (
    Conversation,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
    Ticket,
    TicketPriority,
)
from backend.app.llm.mock import MockLLMProvider
from backend.app.ticketing.adapter import LocalTicketingAdapter


@pytest.fixture
def chat_ticket(db_session: Session) -> Ticket:
    """Fixture to create an active ticket for API testing."""
    conv = Conversation(title="Problema Rete Stampanti", user_id="user_api_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Rete Ufficio Amministrazione",
        description="Impossibile raggiungere stampante di rete.",
        initial_category="network",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.ESCALATED.value,
        escalation_requested=True,
    )
    db_session.add(req)
    db_session.flush()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Rete Ufficio Amministrazione",
        summary="Ping fallito verso IP stampante 192.168.10.50",
        symptoms="Host unreachable",
        attempted_steps="Verificato cavo ethernet.",
        diagnostic_findings="Porta switch in stato err-disabled.",
        priority=TicketPriority.MEDIUM.value,
    )
    return ticket


def test_get_ticket_chat_history_empty_and_404(client: TestClient, chat_ticket: Ticket) -> None:
    """Test retrieving chat history when empty and 404 for missing ticket."""
    resp = client.get(f"/api/tickets/{chat_ticket.id}/chat")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []

    resp_404 = client.get("/api/tickets/nonexistent_ticket/chat")
    assert resp_404.status_code == 404


def test_post_ticket_chat_message_turn_offline(client: TestClient, chat_ticket: Ticket) -> None:
    """Test posting a technician chat message and receiving assistant response."""
    mock_llm = MockLLMProvider(is_configured=False)
    service = TechnicianAssistantService(llm_provider=mock_llm)
    reset_tech_assistant_for_test(service)

    try:
        resp = client.post(
            f"/api/tickets/{chat_ticket.id}/chat",
            json={
                "content": "Ho verificato la porta dello switch e resettato lo stato err-disabled.",
                "author": "technician_demo",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["technician_message"]["content"].startswith("Ho verificato la porta")
        assert data["assistant_message"]["sender"] == "assistant"
        assert "Modalità Offline" in data["assistant_message"]["content"]

        # History now contains 2 messages
        hist_resp = client.get(f"/api/tickets/{chat_ticket.id}/chat")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["total"] == 2
    finally:
        reset_tech_assistant_for_test(None)


def test_post_ticket_chat_redaction(client: TestClient, chat_ticket: Ticket) -> None:
    """Test that secrets in technician chat payload are automatically redacted upon persistence."""
    mock_llm = MockLLMProvider(is_configured=False)
    service = TechnicianAssistantService(llm_provider=mock_llm)
    reset_tech_assistant_for_test(service)

    try:
        resp = client.post(
            f"/api/tickets/{chat_ticket.id}/chat",
            json={
                "content": "Ho fatto login con password: MySecretPass123! e token: Bearer eyJhbGciOiJIUzI1NiJ9.demo",
                "author": "technician_demo",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "MySecretPass123!" not in data["technician_message"]["content"]
        assert "[REDACTED_PASSWORD]" in data["technician_message"]["content"]
        assert "[REDACTED_TOKEN]" in data["technician_message"]["content"]
    finally:
        reset_tech_assistant_for_test(None)
