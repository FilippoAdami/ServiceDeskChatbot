from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.agent.tech_assistant import TechnicianAssistantService
from backend.app.config import get_settings
from backend.app.db.models import Ticket, TicketPriority, TicketStatus
from backend.app.llm.models import LLMGenerationConfig, LLMResponse


def test_audit_events_listing_and_filtering(client: TestClient) -> None:
    # 1. Create a conversation (emits conversation_created)
    conv_res = client.post("/api/conversations", json={"title": "Test Audit Chat"})
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 2. Send user message (emits message_sent)
    msg_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Ho bisogno di aiuto con la VPN", "sender": "user"},
    )
    assert msg_res.status_code == 201

    # 3. Query all audit events
    all_events_res = client.get("/api/audit/events?limit=20")
    assert all_events_res.status_code == 200
    all_data = all_events_res.json()
    assert all_data["total"] >= 2
    items = all_data["items"]
    assert any(e["event_type"] == "conversation_created" for e in items)
    assert any(e["event_type"] == "message_sent" for e in items)

    # 4. Filter by category=employee
    emp_res = client.get("/api/audit/events?category=employee")
    assert emp_res.status_code == 200
    emp_data = emp_res.json()
    assert all(e["category"] == "employee" for e in emp_data["items"])
    assert any(e["conversation_id"] == conv_id for e in emp_data["items"])

    # 5. Filter by conversation_id
    conv_events_res = client.get(f"/api/audit/events?conversation_id={conv_id}")
    assert conv_events_res.status_code == 200
    conv_data = conv_events_res.json()
    assert len(conv_data["items"]) >= 2
    for item in conv_data["items"]:
        assert item["conversation_id"] == conv_id
        assert item["action_label"] is not None
        assert "payload" in item


def test_audit_conversations_listing(client: TestClient) -> None:
    res = client.post("/api/conversations", json={"title": "Conv for Audit Summary"})
    assert res.status_code == 201
    conv_id = res.json()["id"]

    convs_res = client.get("/api/audit/conversations")
    assert convs_res.status_code == 200
    convs_data = convs_res.json()
    assert convs_data["total"] >= 1

    matched = next((c for c in convs_data["items"] if c["conversation_id"] == conv_id), None)
    assert matched is not None
    assert matched["title"] == "Conv for Audit Summary"
    assert matched["event_count"] >= 1


@pytest.mark.asyncio
async def test_tech_assistant_uses_configured_max_tokens(db_session) -> None:
    settings = get_settings()
    mock_llm = MagicMock()
    mock_llm.is_configured = True
    captured_config: list[LLMGenerationConfig] = []

    from backend.app.llm.models import TokenUsage

    async def fake_generate(*args, **kwargs):
        cfg = kwargs.get("config")
        if cfg:
            captured_config.append(cfg)
        return LLMResponse(
            content="Risposta copilota tecnico: verificare i certificati di rete.",
            token_usage=TokenUsage(
                prompt_tokens=100,
                thoughts_tokens=200,
                completion_tokens=50,
                total_tokens=350,
            ),
            model="gemini-2.5-flash",
            latency_ms=120.0,
            finish_reason="STOP",
        )

    mock_llm.generate = AsyncMock(side_effect=fake_generate)
    mock_rag = MagicMock()
    mock_rag.retrieve = AsyncMock(return_value=[])

    service = TechnicianAssistantService(
        llm_provider=mock_llm,
        rag_service=mock_rag,
        settings=settings,
    )

    from backend.app.db.models import Conversation, SupportRequest

    conv = Conversation(title="Chat Tecnica", user_id="user_test")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema certificati",
        description="Errore handshake SSL",
        status="escalated",
    )
    db_session.add(req)
    db_session.flush()

    ticket = Ticket(
        conversation_id=conv.id,
        support_request_id=req.id,
        title="Problema certificati",
        summary="Errore handshake SSL",
        symptoms="Timeout connessione",
        attempted_steps="Verifica cavi e IP",
        diagnostic_findings="Certificato scaduto",
        status=TicketStatus.OPEN.value,
        priority=TicketPriority.MEDIUM.value,
        summary_quality="sufficient",
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    tech_msg, asst_msg, proposals = await service.handle_turn(
        db=db_session,
        ticket_id=ticket.id,
        technician_message="Ho controllato la configurazione, cosa suggerisci?",
    )

    assert len(captured_config) == 1
    # Check max_output_tokens matches settings (4096) and NOT hardcoded 1024
    assert captured_config[0].max_output_tokens == settings.GEMINI_MAX_OUTPUT_TOKENS
    assert captured_config[0].max_output_tokens == 4096
    assert asst_msg.content == "Risposta copilota tecnico: verificare i certificati di rete."
