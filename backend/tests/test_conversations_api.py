from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditEvent


def test_create_conversation(client: TestClient) -> None:
    response = client.post("/api/conversations", json={"title": "Problema connessione VPN"})
    assert response.status_code == 201
    data = response.json()

    assert data["id"].startswith("conv_")
    assert data["title"] == "Problema connessione VPN"
    assert data["user_id"] == "user_demo_01"
    assert data["status"] == "active"
    assert data["messages"] == []
    assert data["requests"] == []


def test_list_conversations_pagination(client: TestClient) -> None:
    # Create 3 conversations
    client.post("/api/conversations", json={"title": "Conv 1"})
    client.post("/api/conversations", json={"title": "Conv 2"})
    client.post("/api/conversations", json={"title": "Conv 3"})

    response = client.get("/api/conversations?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Test offset
    response_offset = client.get("/api/conversations?limit=2&offset=2")
    assert response_offset.status_code == 200
    data_offset = response_offset.json()
    assert len(data_offset["items"]) >= 1


def test_get_conversation_detail(client: TestClient) -> None:
    create_res = client.post("/api/conversations", json={"title": "Thread di test"})
    conv_id = create_res.json()["id"]

    # Add message
    client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Primo messaggio utente"},
    )

    # Add request
    client.post(
        f"/api/conversations/{conv_id}/requests",
        json={"title": "Richiesta 1", "description": "Descrizione del problema"},
    )

    detail_res = client.get(f"/api/conversations/{conv_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert detail["id"] == conv_id
    assert len(detail["messages"]) == 1
    assert detail["messages"][0]["content"] == "Primo messaggio utente"
    assert detail["messages"][0]["role"] == "user"
    assert len(detail["requests"]) == 1
    assert detail["requests"][0]["title"] == "Richiesta 1"


def test_get_nonexistent_conversation_404(client: TestClient) -> None:
    res = client.get("/api/conversations/nonexistent_conv_999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_add_message_with_secret_redaction_and_audit(client: TestClient) -> None:
    create_res = client.post("/api/conversations", json={"title": "Test Redazione"})
    conv_id = create_res.json()["id"]

    secret_message = (
        "Buongiorno, la mia password: MySecretPass123! e il mio token: Bearer eyJhbGciOiJIUzI1Ni.abc "
        "non funzionano più per accedere."
    )

    msg_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": secret_message},
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()

    # Verify secret is redacted in stored message
    assert "MySecretPass123!" not in msg_data["content"]
    assert "password: [REDACTED_PASSWORD]" in msg_data["content"]
    assert "Bearer [REDACTED_TOKEN]" in msg_data["content"]
    assert msg_data["role"] == "user"

    # Query DB to inspect the AuditEvent directly
    from backend.app.db.session import get_engine
    engine = get_engine()
    with Session(engine) as session:
        events = session.execute(
            select(AuditEvent)
            .where(AuditEvent.conversation_id == conv_id)
            .where(AuditEvent.event_type == "message_sent")
        ).scalars().all()

        assert len(events) == 1
        audit = events[0]
        # Payload must be minimal metadata, NO full message text, NO secrets
        assert "content" not in audit.payload
        assert "text" not in audit.payload
        assert "MySecretPass123!" not in str(audit.payload)
        assert audit.payload["role"] == "user"
        assert audit.payload["had_redacted_secrets"] is True


def test_add_empty_message_422(client: TestClient) -> None:
    create_res = client.post("/api/conversations", json={"title": "Test vuoto"})
    conv_id = create_res.json()["id"]

    res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "   "})
    assert res.status_code == 422


def test_add_multiple_requests_to_same_conversation(client: TestClient) -> None:
    create_res = client.post("/api/conversations", json={"title": "Multi-ticket thread"})
    conv_id = create_res.json()["id"]

    # Add 2 requests
    req1 = client.post(
        f"/api/conversations/{conv_id}/requests",
        json={"title": "Problema 1", "description": "Descrizione 1", "initial_category": "email"},
    )
    assert req1.status_code == 201

    req2 = client.post(
        f"/api/conversations/{conv_id}/requests",
        json={"title": "Problema 2", "description": "Descrizione 2", "initial_category": "network"},
    )
    assert req2.status_code == 201

    detail_res = client.get(f"/api/conversations/{conv_id}")
    assert detail_res.status_code == 200
    requests = detail_res.json()["requests"]
    assert len(requests) == 2
