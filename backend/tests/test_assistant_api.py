from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.agent import (
    ConversationalAgentOrchestrator,
    reset_agent_orchestrator_for_test,
)
from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.models import Message, MessageRole
from backend.app.db.session import get_engine, init_db, reset_db_session
from backend.app.llm.mock import MockLLMProvider
from backend.app.main import create_app
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore


@pytest.fixture
def mock_orchestrator(tmp_path: Path) -> ConversationalAgentOrchestrator:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    doc = kb_dir / "wifi.md"
    doc.write_text(
        """---
id: KB-NET-001
title: Connessione Wi-Fi Aziendale
category: Rete
status: approved
---
# Connessione Wi-Fi
Collegarsi alla rete aziendale 'Corporate-Secure' con certificato.
""",
        encoding="utf-8",
    )
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag_service = KnowledgeRetrievalService(encoder=encoder, vector_store=store, base_kb_dir=kb_dir)
    rag_service.index_documents(clean_obsolete=True)

    llm = MockLLMProvider()
    orch = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=rag_service)
    reset_agent_orchestrator_for_test(orch)
    return orch


@pytest.fixture
def test_client(
    tmp_path: Path,
    mock_orchestrator: ConversationalAgentOrchestrator,
) -> Generator[TestClient, None, None]:
    db_file = tmp_path / "test_api.db"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
        CORS_ORIGINS=["http://testserver"],
    )
    reset_settings_for_test(settings)
    reset_db_session()
    init_db()

    app = create_app(settings=settings)
    with TestClient(app) as client:
        yield client

    reset_agent_orchestrator_for_test(None)
    reset_db_session()
    reset_settings_for_test(None)


def test_assistant_turn_success(test_client: TestClient) -> None:
    # 1. Create thread
    conv_res = test_client.post("/api/conversations", json={"title": "Test Wi-Fi"})
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 2. Add user message
    msg_res = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Non riesco a collegarmi alla rete Wi-Fi"},
    )
    assert msg_res.status_code == 201

    # 3. Trigger assistant turn
    turn_res = test_client.post(f"/api/conversations/{conv_id}/assistant-turn")
    assert turn_res.status_code == 200
    turn_data = turn_res.json()

    assert turn_data["message"]["role"] == "assistant"
    assert len(turn_data["message"]["content"]) > 0
    assert turn_data["phase"] == "triage"
    assert turn_data["escalation_requested"] is False
    assert "tokens" in turn_data
    assert "latency_ms" in turn_data

    # 4. Check conversation detail contains both messages
    detail_res = test_client.get(f"/api/conversations/{conv_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"


def test_assistant_turn_404_not_found(test_client: TestClient) -> None:
    res = test_client.post("/api/conversations/conv_nonexistent_999/assistant-turn")
    assert res.status_code == 404


def test_assistant_turn_400_empty_conversation(test_client: TestClient) -> None:
    conv_res = test_client.post("/api/conversations", json={"title": "Empty Conv"})
    conv_id = conv_res.json()["id"]

    res = test_client.post(f"/api/conversations/{conv_id}/assistant-turn")
    assert res.status_code == 400
    assert "Nessun messaggio presente" in res.json()["detail"]


def test_assistant_turn_400_last_message_not_user(test_client: TestClient) -> None:
    conv_res = test_client.post("/api/conversations", json={"title": "Consecutive Turn"})
    conv_id = conv_res.json()["id"]

    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Primo messaggio"})
    test_client.post(f"/api/conversations/{conv_id}/assistant-turn")

    # Second assistant turn without intermediate user message
    res = test_client.post(f"/api/conversations/{conv_id}/assistant-turn")
    assert res.status_code == 400
    assert "L'ultimo messaggio non è dell'utente" in res.json()["detail"]


def test_assistant_turn_503_when_unconfigured(test_client: TestClient) -> None:
    # Set mock provider as unconfigured
    unconf_llm = MockLLMProvider()
    unconf_llm.is_configured = False
    orch = ConversationalAgentOrchestrator(llm_provider=unconf_llm, rag_service=None)  # type: ignore
    reset_agent_orchestrator_for_test(orch)

    conv_res = test_client.post("/api/conversations", json={"title": "Unconfigured LLM"})
    conv_id = conv_res.json()["id"]
    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Help me"})

    res = test_client.post(f"/api/conversations/{conv_id}/assistant-turn")
    assert res.status_code == 503
    assert "GEMINI_API_KEY mancante" in res.json()["detail"]


def test_assistant_turn_502_on_generation_failure(test_client: TestClient, tmp_path: Path) -> None:
    # Mock provider that simulates server error
    failing_llm = MockLLMProvider(simulate_server_error=True)
    orch = ConversationalAgentOrchestrator(llm_provider=failing_llm, rag_service=None)  # type: ignore
    reset_agent_orchestrator_for_test(orch)

    conv_res = test_client.post("/api/conversations", json={"title": "Failing LLM"})
    conv_id = conv_res.json()["id"]
    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Help me"})

    res = test_client.post(f"/api/conversations/{conv_id}/assistant-turn")
    assert res.status_code == 502

    # Invariant: NO assistant message saved to database
    engine = get_engine()
    factory = sessionmaker(bind=engine)
    with factory() as db:
        assistant_msgs = list(
            db.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.role == MessageRole.ASSISTANT.value,
                )
            ).all()
        )
        assert len(assistant_msgs) == 0


@pytest.mark.asyncio
async def test_assistant_turn_concurrency_lock_409(tmp_path: Path) -> None:
    # Direct orchestrator test to verify lock rejection
    llm = MockLLMProvider()
    orch = ConversationalAgentOrchestrator(llm_provider=llm, rag_service=None)  # type: ignore

    conv_id = "conv_lock_test"
    lock = orch._get_lock(conv_id)
    await lock.acquire()

    try:
        from fastapi import HTTPException

        engine = get_engine()
        factory = sessionmaker(bind=engine)
        with factory() as db:
            with pytest.raises(HTTPException) as exc_info:
                await orch.execute_turn(conv_id, db)
            assert exc_info.value.status_code == 409
            assert "già in elaborazione" in exc_info.value.detail
    finally:
        lock.release()
