from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.agent.orchestrator import (
    ConversationalAgentOrchestrator,
    SessionMetaData,
    extract_session_meta,
)
from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.models import (
    AgentPhase,
    AuditEvent,
    Conversation,
    Message,
    MessageRole,
    RequestOutcome,
    SupportRequest,
)
from backend.app.db.session import get_engine, init_db, reset_db_session
from backend.app.llm.mock import MockLLMProvider
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore


@pytest.fixture
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    db_file = tmp_path / "test_agent.db"
    settings = Settings(DATABASE_URL=f"sqlite:///{db_file}", ENVIRONMENT="test")
    reset_settings_for_test(settings)
    reset_db_session()
    init_db()

    engine = get_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        reset_db_session()
        reset_settings_for_test(None)


@pytest.fixture
def test_rag_service(tmp_path: Path) -> KnowledgeRetrievalService:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    doc = kb_dir / "mail.md"
    doc.write_text(
        """---
id: KB-MAIL-001
title: Accesso Outlook Webmail
category: Email
status: approved
---
# Accesso Outlook
Accedere all'indirizzo https://outlook.office.com con account aziendale.
Se l'accesso fallisce, verificare lo stato della rete e MFA.
""",
        encoding="utf-8",
    )

    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    service = KnowledgeRetrievalService(encoder=encoder, vector_store=store, base_kb_dir=kb_dir)
    service.index_documents(clean_obsolete=True)
    return service


@pytest.fixture
def orchestrator(test_rag_service: KnowledgeRetrievalService) -> ConversationalAgentOrchestrator:
    llm = MockLLMProvider()
    return ConversationalAgentOrchestrator(llm_provider=llm, rag_service=test_rag_service)


@pytest.mark.asyncio
async def test_orchestrator_initial_triage(
    orchestrator: ConversationalAgentOrchestrator,
    db_session: Session,
) -> None:
    db = db_session
    conv = Conversation(title="Problema generico", user_id="user_test")
    db.add(conv)
    db.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Il mio computer è lento da stamattina",
    )
    db.add(msg)
    db.commit()

    result = await orchestrator.execute_turn(conv.id, db)

    assert result.phase == AgentPhase.TRIAGE.value
    assert result.escalation_requested is False
    assert result.message.role == MessageRole.ASSISTANT.value
    assert len(result.message.content) > 0

    # Check DB SupportRequest
    req = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv.id))
    assert req is not None
    assert req.phase == AgentPhase.TRIAGE.value

    # Check AuditEvent
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.conversation_id == conv.id)).all())
    assert any(e.event_type == "assistant_turn_completed" for e in events)


@pytest.mark.asyncio
async def test_orchestrator_phase_progression_to_diagnosis(
    orchestrator: ConversationalAgentOrchestrator,
    db_session: Session,
) -> None:
    db = db_session
    conv = Conversation(title="Posta Outlook", user_id="user_test")
    db.add(conv)
    db.flush()

    # Turn 1: User problem
    db.add(Message(conversation_id=conv.id, role=MessageRole.USER.value, content="Non accedo alla posta"))
    db.add(Message(conversation_id=conv.id, role=MessageRole.ASSISTANT.value, content="Che errore ricevi?"))
    # Turn 2: User clarification -> should trigger diagnosis
    db.add(Message(conversation_id=conv.id, role=MessageRole.USER.value, content="Ricevo errore password su Outlook"))
    db.commit()

    result = await orchestrator.execute_turn(conv.id, db)

    assert result.phase == AgentPhase.DIAGNOSIS.value
    assert len(result.sources) >= 1
    assert any(s["doc_id"] == "KB-MAIL-001" for s in result.sources)

    req = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv.id))
    assert req is not None
    assert req.phase == AgentPhase.DIAGNOSIS.value


@pytest.mark.asyncio
async def test_orchestrator_resolution_confirmation(
    orchestrator: ConversationalAgentOrchestrator,
    db_session: Session,
) -> None:
    db = db_session
    conv = Conversation(title="Risoluzione", user_id="user_test")
    db.add(conv)
    db.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Outlook",
        description="Problema posta",
        phase=AgentPhase.DIAGNOSIS.value,
    )
    db.add(req)
    db.add(Message(conversation_id=conv.id, role=MessageRole.USER.value, content="Non va"))
    db.add(Message(conversation_id=conv.id, role=MessageRole.ASSISTANT.value, content="Prova questo passaggio"))
    # User confirms resolution
    db.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            content="Ha funzionato perfettamente, tutto a posto grazie!",
        )
    )
    db.commit()

    result = await orchestrator.execute_turn(conv.id, db)

    assert result.phase == AgentPhase.FINALIZATION.value
    assert req.outcome == RequestOutcome.RESOLVED_CONFIRMED.value


@pytest.mark.asyncio
async def test_orchestrator_human_technician_escalation(
    orchestrator: ConversationalAgentOrchestrator,
    db_session: Session,
) -> None:
    db = db_session
    conv = Conversation(title="Escalation", user_id="user_test")
    db.add(conv)
    db.flush()

    db.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            content="Vorrei parlare con un tecnico umano, per favore",
        )
    )
    db.commit()

    result = await orchestrator.execute_turn(conv.id, db)

    assert result.escalation_requested is True
    assert result.phase == AgentPhase.FINALIZATION.value

    req = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv.id))
    assert req is not None
    assert req.escalation_requested is True
    assert req.outcome == RequestOutcome.ESCALATED.value


@pytest.mark.asyncio
async def test_orchestrator_redacts_secrets_in_persisted_assistant_message(
    test_rag_service: KnowledgeRetrievalService,
    db_session: Session,
) -> None:
    # Provider that outputs a secret
    llm = MockLLMProvider(
        canned_responses=["Ecco la password: TempSecretPass123! e token: Bearer eyJhbGciOiJIUzI1NiJ9.abc"]
    )
    orch = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=test_rag_service)

    db = db_session
    conv = Conversation(title="Redaction Test", user_id="user_test")
    db.add(conv)
    db.flush()

    db.add(Message(conversation_id=conv.id, role=MessageRole.USER.value, content="Cosa faccio?"))
    db.commit()

    result = await orch.execute_turn(conv.id, db)

    # Message in DB must be redacted
    assert "TempSecretPass123!" not in result.message.content
    assert "[REDACTED" in result.message.content


@pytest.mark.asyncio
async def test_orchestrator_skips_rag_on_out_of_scope_query(
    orchestrator: ConversationalAgentOrchestrator,
    db_session: Session,
) -> None:
    db = db_session
    conv = Conversation(title="Tiramisu", user_id="user_test")
    db.add(conv)
    db.flush()

    db.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            content="puoi darmi la ricetta del tiramisu'?",
        )
    )
    db.commit()

    result = await orchestrator.execute_turn(conv.id, db)

    # RAG search must be bypassed completely: 0 sources
    assert len(result.sources) == 0
    assert result.phase == AgentPhase.TRIAGE.value
    assert result.escalation_requested is False


@pytest.mark.asyncio
async def test_orchestrator_skips_rag_on_simple_greeting(
    orchestrator: ConversationalAgentOrchestrator,
    db_session: Session,
) -> None:
    db = db_session
    conv = Conversation(title="Saluto", user_id="user_test")
    db.add(conv)
    db.flush()

    db.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            content="Buongiorno!",
        )
    )
    db.commit()

    result = await orchestrator.execute_turn(conv.id, db)

    # RAG search must be bypassed completely for simple greeting
    assert len(result.sources) == 0
    assert result.phase == AgentPhase.TRIAGE.value


def test_extract_session_meta_valid() -> None:
    text = (
        "Buongiorno, ti aiuto volentieri a verificare il problema di posta.\n\n"
        "```session_meta\n"
        "{\n"
        '  "proposed_title": "Mancato accesso Webmail Outlook",\n'
        '  "category": "Problemi Email",\n'
        '  "phase": "diagnosis"\n'
        "}\n"
        "```"
    )
    clean, meta = extract_session_meta(text)
    assert clean == "Buongiorno, ti aiuto volentieri a verificare il problema di posta."
    assert meta is not None
    assert isinstance(meta, SessionMetaData)
    assert meta.proposed_title == "Mancato accesso Webmail Outlook"
    assert meta.category == "Problemi Email"
    assert meta.phase == "diagnosis"


def test_extract_session_meta_fallback_on_invalid_or_missing() -> None:
    # Missing block
    clean, meta = extract_session_meta("Solo testo normale senza blocchi")
    assert clean == "Solo testo normale senza blocchi"
    assert meta is None

    # Malformed JSON
    clean_malformed, meta_malformed = extract_session_meta(
        "Messaggio\n```session_meta\n{proposed_title: no quotes}\n```"
    )
    assert "Messaggio" in clean_malformed
    assert meta_malformed is None


@pytest.mark.asyncio
async def test_orchestrator_turn_with_session_meta_immediate_diagnosis_and_title(
    test_rag_service: KnowledgeRetrievalService,
    db_session: Session,
) -> None:
    canned_llm_output = (
        "Ho individuato la causa del disservizio: procediamo con la verifica della casella.\n"
        "1. Apri https://outlook.office.com.\n\n"
        "```session_meta\n"
        "{\n"
        '  "proposed_title": "Errore credenziali Outlook Webmail",\n'
        '  "category": "Problemi Email",\n'
        '  "phase": "diagnosis"\n'
        "}\n"
        "```"
    )
    llm = MockLLMProvider(canned_responses=[canned_llm_output])
    orch = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=test_rag_service)

    db = db_session
    conv = Conversation(title="Nuova Richiesta IT", user_id="user_test")
    db.add(conv)
    db.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Non riesco ad accedere alla mia posta Outlook da stamattina, dice errore password",
    )
    db.add(msg)
    db.commit()

    # First turn: Gemini recognizes problem immediately and returns session_meta
    result = await orch.execute_turn(conv.id, db)

    # Content must NOT contain the technical session_meta block
    assert "```session_meta" not in result.message.content
    assert "Ho individuato la causa del disservizio" in result.message.content

    # State must transition immediately to DIAGNOSIS on turn 1
    assert result.phase == AgentPhase.DIAGNOSIS.value
    assert result.conversation_title == "Errore credenziali Outlook Webmail"
    assert result.category == "Problemi Email"

    # DB records must reflect the updated title and category
    db.refresh(conv)
    assert conv.title == "Errore credenziali Outlook Webmail"

    req = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv.id))
    assert req is not None
    assert req.title == "Errore credenziali Outlook Webmail"
    assert req.initial_category == "Problemi Email"
    assert req.phase == AgentPhase.DIAGNOSIS.value


@pytest.mark.asyncio
async def test_orchestrator_turn_with_session_meta_remains_in_triage(
    test_rag_service: KnowledgeRetrievalService,
    db_session: Session,
) -> None:
    canned_llm_output = (
        "Per aiutarti ho bisogno di maggiori dettagli. Quale programma o servizio non risponde?\n\n"
        "```session_meta\n"
        "{\n"
        '  "proposed_title": "Richiesta chiarimenti supporto generico",\n'
        '  "category": "Richiesta Generica",\n'
        '  "phase": "triage"\n'
        "}\n"
        "```"
    )
    llm = MockLLMProvider(canned_responses=[canned_llm_output])
    orch = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=test_rag_service)

    db = db_session
    conv = Conversation(title="Nuova Richiesta IT", user_id="user_test")
    db.add(conv)
    db.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="ciao, ho un problema con una cosa al pc",
    )
    db.add(msg)
    db.commit()

    result = await orch.execute_turn(conv.id, db)

    assert result.phase == AgentPhase.TRIAGE.value
    assert result.conversation_title == "Richiesta chiarimenti supporto generico"
    assert result.category == "Richiesta Generica"

    req = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv.id))
    assert req is not None
    assert req.phase == AgentPhase.TRIAGE.value
