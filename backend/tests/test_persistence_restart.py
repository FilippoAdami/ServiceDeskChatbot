from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.models import AuditEvent
from backend.app.db.session import init_db, reset_db_session
from backend.app.main import create_app


def test_full_lifecycle_persistence_across_restart(tmp_path: Path) -> None:
    """Verify that conversation, messages, request and audit events survive full server restart."""
    db_file = tmp_path / "persistence_restart_lifecycle.db"

    # Step 1: Initialize first session of the application
    settings = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
    )
    reset_settings_for_test(settings)
    reset_db_session()
    init_db()

    app1 = create_app(settings=settings)
    with TestClient(app1) as client1:
        # Create conversation
        conv_res = client1.post("/api/conversations", json={"title": "Sessione prima del restart"})
        assert conv_res.status_code == 201
        conv_id = conv_res.json()["id"]

        # Add message 1
        msg1_res = client1.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "Messaggio numero uno"},
        )
        assert msg1_res.status_code == 201

        # Add message 2 with secret
        msg2_res = client1.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "Messaggio numero due con password: PlainPasswordSecret"},
        )
        assert msg2_res.status_code == 201

        # Create support request
        req_res = client1.post(
            f"/api/conversations/{conv_id}/requests",
            json={"title": "Richiesta IT pre-restart", "description": "Problema critico", "initial_category": "email"},
        )
        assert req_res.status_code == 201
        req_id = req_res.json()["id"]

    # Step 2: Simulate full shutdown and memory flush
    reset_db_session()
    reset_settings_for_test(None)

    # Step 3: Reopen application from the same SQLite file
    settings_reloaded = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
    )
    reset_settings_for_test(settings_reloaded)
    reset_db_session()

    app2 = create_app(settings=settings_reloaded)
    with TestClient(app2) as client2:
        # Fetch conversation details
        detail_res = client2.get(f"/api/conversations/{conv_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()

        assert detail["id"] == conv_id
        assert detail["title"] == "Sessione prima del restart"

        # Verify messages survived and maintained deterministic chronological ordering
        messages = detail["messages"]
        assert len(messages) == 2
        assert messages[0]["content"] == "Messaggio numero uno"
        assert messages[0]["role"] == "user"
        assert messages[1]["content"] == "Messaggio numero due con password: [REDACTED_PASSWORD]"

        # Verify support request survived
        requests = detail["requests"]
        assert len(requests) == 1
        assert requests[0]["id"] == req_id
        assert requests[0]["title"] == "Richiesta IT pre-restart"
        assert requests[0]["status"] == "open"

        # Verify technician endpoint reads the same request
        req_lookup = client2.get(f"/api/requests/{req_id}")
        assert req_lookup.status_code == 200
        assert req_lookup.json()["title"] == "Richiesta IT pre-restart"

    # Step 4: Verify audit events persisted at DB level
    engine = create_engine(f"sqlite:///{db_file}")
    with sessionmaker(bind=engine)() as session:
        events = session.execute(
            select(AuditEvent).where(AuditEvent.conversation_id == conv_id).order_by(AuditEvent.created_at.asc())
        ).scalars().all()

        assert len(events) >= 3
        event_types = [e.event_type for e in events]
        assert "conversation_created" in event_types
        assert "message_sent" in event_types
        assert "support_request_created" in event_types

    engine.dispose()
    reset_db_session()
    reset_settings_for_test(None)
