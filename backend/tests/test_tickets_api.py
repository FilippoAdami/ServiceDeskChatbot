from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db.models import (
    Conversation,
    Incident,
    IncidentStatus,
    SupportRequest,
    TicketPriority,
    TicketStatus,
)
from backend.app.db.session import get_session_factory
from backend.app.ticketing.adapter import LocalTicketingAdapter


def test_list_and_get_tickets(client: TestClient) -> None:
    # 1. Create a ticket in DB
    factory = get_session_factory()
    with factory() as db:
        conv = Conversation(title="Test conv for API")
        db.add(conv)
        db.flush()

        req = SupportRequest(
            conversation_id=conv.id,
            title="Problema stampante di rete",
            description="La stampante non risponde",
        )
        db.add(req)
        db.commit()

        ticket = LocalTicketingAdapter.create_ticket(
            db=db,
            support_request_id=req.id,
            conversation_id=conv.id,
            title="Problema stampante di rete",
            summary="Stampante bloccata in coda",
            symptoms="Spia rossa lampeggiante",
            attempted_steps="Riavvio stampante",
            diagnostic_findings="Spooler bloccato",
            source_refs=["KB-PRINT-001"],
            priority=TicketPriority.MEDIUM.value,
        )
        ticket_id = ticket.id

    # 2. List tickets via GET /api/tickets
    res = client.get("/api/tickets")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert ticket_id in ids

    # 3. Get ticket detail via GET /api/tickets/{id}
    res_detail = client.get(f"/api/tickets/{ticket_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == ticket_id
    assert detail["title"] == "Problema stampante di rete"
    assert detail["status"] == TicketStatus.OPEN.value
    assert len(detail["activities"]) >= 1


def test_update_ticket_status_api(client: TestClient) -> None:
    factory = get_session_factory()
    with factory() as db:
        conv = Conversation(title="Conv status API")
        db.add(conv)
        db.flush()
        req = SupportRequest(conversation_id=conv.id, title="Req", description="Desc")
        db.add(req)
        db.commit()

        ticket = LocalTicketingAdapter.create_ticket(
            db=db,
            support_request_id=req.id,
            conversation_id=conv.id,
            title="Status test",
            summary="Sum",
            symptoms="Sym",
            attempted_steps="Att",
            diagnostic_findings="Diag",
        )
        ticket_id = ticket.id

    # Invalid transition open -> resolved returns 409 Conflict
    res_invalid = client.post(
        f"/api/tickets/{ticket_id}/status",
        json={"status": "resolved", "author": "tech_mario"},
    )
    assert res_invalid.status_code == 409
    assert "Transizione di stato non consentita" in res_invalid.json()["detail"]

    # Valid transition open -> in_progress returns 200
    res_valid = client.post(
        f"/api/tickets/{ticket_id}/status",
        json={"status": "in_progress", "note": "Preso in carico dal tecnico", "author": "tech_mario"},
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["status"] == "in_progress"
    assert any(a["activity_type"] == "status_change" for a in data["activities"])


def test_add_ticket_note_api(client: TestClient) -> None:
    factory = get_session_factory()
    with factory() as db:
        conv = Conversation(title="Conv note API")
        db.add(conv)
        db.flush()
        req = SupportRequest(conversation_id=conv.id, title="Req", description="Desc")
        db.add(req)
        db.commit()

        ticket = LocalTicketingAdapter.create_ticket(
            db=db,
            support_request_id=req.id,
            conversation_id=conv.id,
            title="Note test",
            summary="Sum",
            symptoms="Sym",
            attempted_steps="Att",
            diagnostic_findings="Diag",
        )
        ticket_id = ticket.id

    # Empty note returns 422
    res_empty = client.post(f"/api/tickets/{ticket_id}/notes", json={"content": "  "})
    assert res_empty.status_code == 422

    # Note with secret has secret redacted
    res_note = client.post(
        f"/api/tickets/{ticket_id}/notes",
        json={
            "content": "Contattato utente. Inserita password temporanea password=TempPass999!",
            "author": "tech_luigi",
        },
    )
    assert res_note.status_code == 201
    act = res_note.json()
    assert act["activity_type"] == "note"
    assert "TempPass999!" not in act["content"]
    assert "[REDACTED_PASSWORD]" in act["content"]


def test_link_and_unlink_incident_api(client: TestClient) -> None:
    factory = get_session_factory()
    with factory() as db:
        inc = Incident(
            id="INC-API-001",
            service="VPN",
            title="Gateway Cisco down",
            symptoms="Timeout",
            summary="Disservizio Cisco",
            status=IncidentStatus.INVESTIGATING.value,
        )
        db.add(inc)

        conv = Conversation(title="Conv link API")
        db.add(conv)
        db.flush()
        req = SupportRequest(conversation_id=conv.id, title="Req", description="Desc")
        db.add(req)
        db.commit()

        ticket = LocalTicketingAdapter.create_ticket(
            db=db,
            support_request_id=req.id,
            conversation_id=conv.id,
            title="Link test",
            summary="Sum",
            symptoms="Sym",
            attempted_steps="Att",
            diagnostic_findings="Diag",
        )
        ticket_id = ticket.id

    # Link incident via POST /api/tickets/{id}/incident
    res_link = client.post(
        f"/api/tickets/{ticket_id}/incident",
        json={"incident_id": "INC-API-001", "author": "tech_admin"},
    )
    assert res_link.status_code == 200
    assert res_link.json()["incident_id"] == "INC-API-001"

    # Unlink incident via POST /api/tickets/{id}/incident with incident_id=None
    res_unlink = client.post(
        f"/api/tickets/{ticket_id}/incident",
        json={"incident_id": None, "author": "tech_admin"},
    )
    assert res_unlink.status_code == 200
    assert res_unlink.json()["incident_id"] is None
