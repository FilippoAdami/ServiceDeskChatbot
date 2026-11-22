from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db.models import Conversation, SupportRequest
from backend.app.db.session import get_session_factory
from backend.app.ticketing.adapter import LocalTicketingAdapter


def test_list_and_get_incidents_api(client: TestClient) -> None:
    # 1. Verify demo seeded incidents exist
    res = client.get("/api/incidents")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3
    inc_ids = [item["id"] for item in data["items"]]
    assert "INC-2026-001" in inc_ids
    assert "INC-2026-002" in inc_ids

    # 2. Get specific incident detail
    res_detail = client.get("/api/incidents/INC-2026-001")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == "INC-2026-001"
    assert detail["service"] == "Email"
    assert "tickets" in detail


def test_incident_linked_ticket_count(client: TestClient) -> None:
    factory = get_session_factory()
    with factory() as db:
        conv = Conversation(title="Conv incident count")
        db.add(conv)
        db.flush()
        req = SupportRequest(conversation_id=conv.id, title="Req", description="Desc")
        db.add(req)
        db.commit()

        ticket = LocalTicketingAdapter.create_ticket(
            db=db,
            support_request_id=req.id,
            conversation_id=conv.id,
            title="Ticket for incident count",
            summary="Sum",
            symptoms="Sym",
            attempted_steps="Att",
            diagnostic_findings="Diag",
        )
        LocalTicketingAdapter.link_incident(db, ticket.id, "INC-2026-002")

    res = client.get("/api/incidents/INC-2026-002")
    assert res.status_code == 200
    data = res.json()
    assert data["ticket_count"] >= 1
    linked_ids = [t["id"] for t in data["tickets"]]
    assert ticket.id in linked_ids
