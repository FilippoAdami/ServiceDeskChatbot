from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.models import (
    AuditEvent,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
)
from backend.app.db.session import init_db, reset_db_session


@pytest.fixture
def db_session(tmp_path: Path):
    db_file = tmp_path / "test_models.db"
    settings = Settings(DATABASE_URL=f"sqlite:///{db_file}", ENVIRONMENT="test")
    reset_settings_for_test(settings)
    reset_db_session()

    init_db()

    # Create session with foreign keys enabled
    from backend.app.db.session import get_engine

    engine = get_engine()
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        reset_db_session()
        reset_settings_for_test(None)


def test_create_conversation_and_messages(db_session) -> None:
    conv = Conversation(
        title="Problema accesso email",
        user_id="user_demo_01",
        status=ConversationStatus.ACTIVE.value,
    )
    db_session.add(conv)
    db_session.commit()

    msg1 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Non riesco ad accedere alla casella di posta.",
    )
    msg2 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Ricevo un errore di credenziali non valide.",
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    reloaded = db_session.execute(select(Conversation).where(Conversation.id == conv.id)).scalar_one()

    assert len(reloaded.messages) == 2
    assert reloaded.messages[0].content == "Non riesco ad accedere alla casella di posta."
    assert reloaded.messages[1].content == "Ricevo un errore di credenziali non valide."


def test_sqlite_foreign_key_violation(db_session) -> None:
    """Verify that foreign keys are enforced by SQLite."""
    orphan_msg = Message(
        conversation_id="nonexistent_conv_id",
        role=MessageRole.USER.value,
        content="Messaggio orfano senza conversazione",
    )
    db_session.add(orphan_msg)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_multiple_support_requests_in_conversation(db_session) -> None:
    conv = Conversation(title="Thread multi-richiesta")
    db_session.add(conv)
    db_session.commit()

    req1 = SupportRequest(
        conversation_id=conv.id,
        title="Reset password",
        description="Richiesta di reset password",
        initial_category="account",
        status=RequestStatus.OPEN.value,
    )
    req2 = SupportRequest(
        conversation_id=conv.id,
        title="Configurazione Outlook",
        description="Impossibile configurare Outlook",
        initial_category="software",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.RESOLVED_CONFIRMED.value,
    )
    db_session.add_all([req1, req2])
    db_session.commit()

    reloaded = db_session.execute(select(Conversation).where(Conversation.id == conv.id)).scalar_one()
    assert len(reloaded.requests) == 2


def test_cascade_delete_conversation(db_session) -> None:
    conv = Conversation(title="Conversazione da eliminare")
    db_session.add(conv)
    db_session.commit()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Messaggio da eliminare",
    )
    req = SupportRequest(
        conversation_id=conv.id,
        title="Richiesta da eliminare",
        description="Test cascade",
    )
    db_session.add_all([msg, req])
    db_session.commit()

    # Delete conversation
    db_session.delete(conv)
    db_session.commit()

    # Verify messages and requests are deleted via cascade
    msgs = db_session.execute(select(Message).where(Message.conversation_id == conv.id)).scalars().all()
    reqs = db_session.execute(select(SupportRequest).where(SupportRequest.conversation_id == conv.id)).scalars().all()
    assert len(msgs) == 0
    assert len(reqs) == 0


def test_audit_event_creation(db_session) -> None:
    evt = AuditEvent(
        event_type="conversation_created",
        conversation_id="conv_123",
        payload={"user_id": "user_demo_01", "channel": "web_chat"},
    )
    db_session.add(evt)
    db_session.commit()

    reloaded = db_session.execute(select(AuditEvent).where(AuditEvent.id == evt.id)).scalar_one()
    assert reloaded.event_type == "conversation_created"
    assert reloaded.payload["user_id"] == "user_demo_01"
