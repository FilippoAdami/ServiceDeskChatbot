from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from backend.app.agent.orchestrator import ConversationalAgentOrchestrator
from backend.app.agent.summarizer import _deterministic_fallback_summary
from backend.app.db.models import (
    Conversation,
    Message,
    MessageRole,
    SupportRequest,
    Ticket,
    TicketStatus,
)
from backend.app.llm.mock import MockLLMProvider
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore


@pytest.mark.asyncio
async def test_chatbot_escalation_creates_persistent_ticket(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Set up orchestrator with mock LLM and fake RAG service
    llm = MockLLMProvider()
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma1"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag = KnowledgeRetrievalService(encoder=encoder, vector_store=store)
    orchestrator = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag)

    # 1. Create conversation with initial issue
    conv = Conversation(title="Problema accesso")
    db_session.add(conv)
    db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Non riesco ad accedere alla mia casella di posta elettronica Outlook.",
    )
    db_session.add(msg1)
    db_session.commit()

    # First turn: triage/diagnosis
    res1 = await orchestrator.execute_turn(conv.id, db_session)
    assert not res1.escalation_requested
    assert res1.ticket_id is None

    # 2. User explicitly requests a technician / ticket escalation
    msg2 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Ho già provato ma non va, voglio parlare con un tecnico umano, puoi aprire un ticket?",
    )
    db_session.add(msg2)
    db_session.commit()

    # Second turn: triggers escalation and creates persistent ticket
    res2 = await orchestrator.execute_turn(conv.id, db_session)
    assert res2.escalation_requested is True
    assert res2.ticket_id is not None
    assert res2.ticket_id.startswith("tick_")

    # 3. Verify ticket in SQLite database
    ticket = db_session.query(Ticket).filter_by(id=res2.ticket_id).one_or_none()
    assert ticket is not None
    assert ticket.conversation_id == conv.id
    assert ticket.status == TicketStatus.OPEN.value
    assert ticket.summary_quality in ("llm", "fallback")
    assert ticket.title is not None
    assert len(ticket.symptoms) > 0

    # 4. Repeated escalation turn should be idempotent (reuses existing ticket, does not duplicate)
    msg3 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Qual è lo stato del mio ticket con il tecnico?",
    )
    db_session.add(msg3)
    db_session.commit()

    res3 = await orchestrator.execute_turn(conv.id, db_session)
    ticket_count = db_session.query(Ticket).filter_by(conversation_id=conv.id).count()
    assert ticket_count == 1
    assert res3.ticket_id == res2.ticket_id


@pytest.mark.asyncio
async def test_escalation_db_failure_does_not_fake_ticket(
    db_session: Session,
    tmp_path: Path,
) -> None:
    llm = MockLLMProvider()
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma2"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag = KnowledgeRetrievalService(encoder=encoder, vector_store=store)
    orchestrator = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag)

    conv = Conversation(title="Test fail")
    db_session.add(conv)
    db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Passami un operatore umano immediatamente.",
    )
    db_session.add(msg1)
    db_session.commit()

    # Simulate database error during ticket creation
    with patch(
        "backend.app.ticketing.adapter.LocalTicketingAdapter.create_ticket",
        side_effect=RuntimeError("Simulated SQLite write failure"),
    ):
        res = await orchestrator.execute_turn(conv.id, db_session)

        # Invariant 1: never fake ticket ID if creation failed
        assert res.ticket_id is None
        assert (res.message.metadata_json or {}).get("ticket_id") is None
        # Conversation is still alive
        assert res.escalation_requested is True


def test_deterministic_fallback_summary() -> None:
    req = SupportRequest(
        conversation_id="conv_123",
        title="Problema VPN aziendale",
        description="Errore certificato",
    )
    messages = [
        Message(role=MessageRole.USER.value, content="La VPN non si connette mai"),
        Message(role=MessageRole.ASSISTANT.value, content="Verifica le credenziali di accesso"),
        Message(role=MessageRole.USER.value, content="Non funziona ancora, password=MySecretPassword1!"),
    ]
    summary_data = _deterministic_fallback_summary(req, messages, ["KB-VPN-001"])

    assert summary_data.summary_quality == "fallback"
    assert "MySecretPassword1!" not in summary_data.symptoms
    assert "[REDACTED_PASSWORD]" in summary_data.symptoms
    assert summary_data.source_refs == ["KB-VPN-001"]
    assert "VPN" in summary_data.title


@pytest.mark.asyncio
async def test_escalation_triggers_on_need_technician(
    db_session: Session,
    tmp_path: Path,
) -> None:
    llm = MockLLMProvider()
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_need_tech"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag = KnowledgeRetrievalService(encoder=encoder, vector_store=store)
    orchestrator = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag)

    conv = Conversation(title="Problema PC bloccato")
    db_session.add(conv)
    db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="si grazie, ho bisogno di un tecnico",
    )
    db_session.add(msg)
    db_session.commit()

    res = await orchestrator.execute_turn(conv.id, db_session)
    assert res.escalation_requested is True
    assert res.ticket_id is not None
    assert res.ticket_id.startswith("tick_")


@pytest.mark.asyncio
async def test_contextual_escalation_when_bot_proposes_and_user_affirms(
    db_session: Session,
    tmp_path: Path,
) -> None:
    llm = MockLLMProvider()
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_context_esc"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag = KnowledgeRetrievalService(encoder=encoder, vector_store=store)
    orchestrator = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag)

    conv = Conversation(title="Problema hardware senza KB")
    db_session.add(conv)
    db_session.flush()

    # User describes issue
    db_session.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            content="Lo schermo si blocca senza errore",
        )
    )
    # Assistant proposed escalation
    db_session.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT.value,
            content="Non abbiamo guide per questo problema. Se desideri posso inoltrare una segnalazione ai tecnici.",
        )
    )
    # User affirms with simple confirmation
    db_session.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            content="si grazie, procedi pure",
        )
    )
    db_session.commit()

    res = await orchestrator.execute_turn(conv.id, db_session)
    assert res.escalation_requested is True
    assert res.ticket_id is not None
    assert res.ticket_id.startswith("tick_")


@pytest.mark.asyncio
async def test_tool_calling_create_ticket_dispatch(
    db_session: Session,
    tmp_path: Path,
) -> None:
    # Set up MockLLMProvider that returns a create_ticket function call
    canned_calls = [
        [
            {
                "name": "create_ticket",
                "args": {
                    "title": "Guasto GPU e artefatti a video",
                    "symptoms": "Linee orizzontali e crash improvviso",
                    "reason": "Guasto hardware non risolvibile via software",
                },
            }
        ]
    ]
    llm = MockLLMProvider(canned_tool_calls=canned_calls)
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_tool_dispatch"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag = KnowledgeRetrievalService(encoder=encoder, vector_store=store)
    orchestrator = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag)

    conv = Conversation(title="Problema scheda video")
    db_session.add(conv)
    db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Vedo strane linee colorate e poi si spegne il monitor.",
    )
    db_session.add(msg)
    db_session.commit()

    res = await orchestrator.execute_turn(conv.id, db_session)

    # 1. Ticket created in database
    assert res.escalation_requested is True
    assert res.ticket_id is not None
    assert res.ticket_id.startswith("tick_")

    ticket = db_session.query(Ticket).filter_by(id=res.ticket_id).one_or_none()
    assert ticket is not None
    assert ticket.title == "Guasto GPU e artefatti a video"
    assert "Linee orizzontali" in ticket.symptoms
    assert ticket.status == TicketStatus.OPEN.value

    # 2. Assistant message contains the generated ticket ID
    assert res.ticket_id in res.message.content


@pytest.mark.asyncio
async def test_tool_calling_create_ticket_failure_handling(
    db_session: Session,
    tmp_path: Path,
) -> None:
    canned_calls = [
        [
            {
                "name": "create_ticket",
                "args": {
                    "title": "Guasto alimentatore",
                    "symptoms": "PC non si accende",
                    "reason": "Guasto alimentatore",
                },
            }
        ]
    ]
    llm = MockLLMProvider(canned_tool_calls=canned_calls)
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_tool_fail"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag = KnowledgeRetrievalService(encoder=encoder, vector_store=store)
    orchestrator = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag)

    conv = Conversation(title="PC spento")
    db_session.add(conv)
    db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Il PC non si accende più nemmeno premendo il pulsante.",
    )
    db_session.add(msg)
    db_session.commit()

    with patch(
        "backend.app.ticketing.adapter.LocalTicketingAdapter.create_ticket",
        side_effect=RuntimeError("Simulated DB ticket creation failure"),
    ):
        res = await orchestrator.execute_turn(conv.id, db_session)
        # Invariant 1: never fake ticket ID if creation failed
        assert res.ticket_id is None
        assert "tick_" not in res.message.content
        assert res.escalation_requested is True


