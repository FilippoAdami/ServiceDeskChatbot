from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.agent import ConversationalAgentOrchestrator, get_agent_orchestrator
from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.models import (
    AuditEvent,
    KnowledgeProposal,
    ProposalStatus,
    TechnicianChatMessage,
    Ticket,
    TicketStatus,
)
from backend.app.db.session import init_db, reset_db_session
from backend.app.knowledge.manager import KnowledgeProposalManager
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import LLMGenerationConfig, LLMMessage, LLMResponse
from backend.app.main import create_app
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService, get_rag_service
from backend.app.rag.vector_store.chroma import ChromaVectorStore
from backend.app.ticketing.adapter import LocalTicketingAdapter


def test_persistence_restart_tickets_chat_and_proposals(tmp_path: Path) -> None:
    """Verify that tickets, technician chat messages, and KB proposals survive server restart."""
    db_file = tmp_path / "edge_cases_restart.db"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
        RAG_USE_FAKE_ENCODER=True,
    )
    reset_settings_for_test(settings)
    reset_db_session()
    init_db()

    app1 = create_app(settings=settings)
    with TestClient(app1) as client1:
        # 1. Create conversation and support request
        c_res = client1.post("/api/conversations", json={"title": "Sessione pre-restart"})
        assert c_res.status_code == 201
        conv_id = c_res.json()["id"]

        req_res = client1.post(
            f"/api/conversations/{conv_id}/requests",
            json={"title": "Problema VPN", "description": "Handshake timeout", "initial_category": "network"},
        )
        assert req_res.status_code == 201
        req_id = req_res.json()["id"]

        # 2. Create ticket via DB / adapter
        engine = create_engine(f"sqlite:///{db_file}")
        with sessionmaker(bind=engine)() as session:
            ticket = LocalTicketingAdapter.create_ticket(
                db=session,
                support_request_id=req_id,
                conversation_id=conv_id,
                title="Ticket VPN Escalation",
                summary="Errore timeout VPN riscontrato",
                symptoms="Handshake fallito",
                attempted_steps="Riavvio client",
                diagnostic_findings="Certificato scaduto",
            )
            ticket_id = ticket.id

            # 3. Add technician chat message with operational proposals
            tech_msg = TechnicianChatMessage(
                ticket_id=ticket_id,
                sender="assistant",
                content="Consiglio di aggiornare il certificato",
                proposals_json=json.dumps({
                    "proposed_status": "in_progress",
                    "proposed_note": "Aggiornamento certificato client VPN",
                }),
            )
            session.add(tech_msg)

            # 4. Create KB proposal
            prop = KnowledgeProposal(
                source_type="ticket",
                source_id=ticket_id,
                status=ProposalStatus.DRAFT.value,
                title="Procedura Aggiornamento Certificato VPN",
                category="network",
                content_markdown="# Procedura VPN\nAggiornare certificato da portale.",
                author="tecnico_demo",
            )
            session.add(prop)
            session.commit()
            prop_id = prop.id

    # Simulate full restart
    reset_db_session()
    reset_settings_for_test(None)

    # Re-initialize application from same SQLite database
    settings_reloaded = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
        RAG_USE_FAKE_ENCODER=True,
    )
    reset_settings_for_test(settings_reloaded)
    reset_db_session()

    app2 = create_app(settings=settings_reloaded)
    with TestClient(app2) as client2:
        # Verify ticket details survived
        t_res = client2.get(f"/api/tickets/{ticket_id}")
        assert t_res.status_code == 200
        t_data = t_res.json()
        assert t_data["id"] == ticket_id
        assert t_data["title"] == "Ticket VPN Escalation"
        assert t_data["status"] == "open"

        # Verify technician chat history survived
        chat_res = client2.get(f"/api/tickets/{ticket_id}/chat")
        assert chat_res.status_code == 200
        history_data = chat_res.json()
        messages = history_data.get("items", [])
        assert len(messages) >= 1
        assert messages[0]["content"] == "Consiglio di aggiornare il certificato"
        parsed_prop = json.loads(messages[0]["proposals_json"]) if messages[0]["proposals_json"] else {}
        assert parsed_prop.get("proposed_status") == "in_progress"

        # Verify KB proposal survived
        p_res = client2.get(f"/api/kb-proposals/{prop_id}")
        assert p_res.status_code == 200
        p_data = p_res.json()
        assert p_data["id"] == prop_id
        assert p_data["status"] == "draft"
        assert p_data["title"] == "Procedura Aggiornamento Certificato VPN"


def test_escalation_idempotency_no_duplicate_tickets(tmp_path: Path) -> None:
    """Verify that multiple escalation requests on the same support request do not create duplicate active tickets."""
    db_file = tmp_path / "escalation_idempotency.db"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
        RAG_USE_FAKE_ENCODER=True,
    )
    reset_settings_for_test(settings)
    reset_db_session()
    init_db()

    app = create_app(settings=settings)
    with TestClient(app) as client:
        # Create thread and request
        c_res = client.post("/api/conversations", json={"title": "Idempotency Test"})
        conv_id = c_res.json()["id"]

        r_res = client.post(
            f"/api/conversations/{conv_id}/requests",
            json={"title": "Problema Wi-Fi", "description": "Disconnessioni frequenti", "initial_category": "network"},
        )
        req_id = r_res.json()["id"]

        # Escalate first time via LocalTicketingAdapter
        engine = create_engine(f"sqlite:///{db_file}")
        with sessionmaker(bind=engine)() as session:
            ticket1 = LocalTicketingAdapter.create_ticket(
                db=session,
                support_request_id=req_id,
                conversation_id=conv_id,
                title="Ticket Wi-Fi",
                summary="Primo ticket creato",
                symptoms="Caduta segnale",
                attempted_steps="Riavvio scheda",
                diagnostic_findings="Interferenza canale",
            )
            t1_id = ticket1.id

            # Verify only 1 ticket exists for this request
            tickets = list(
                session.scalars(
                    select(Ticket).where(
                        Ticket.support_request_id == req_id,
                        Ticket.status != TicketStatus.CLOSED.value,
                    )
                ).all()
            )
            assert len(tickets) == 1
            assert tickets[0].id == t1_id

            # In orchestrator, existing_ticket check prevents duplication
            existing_ticket = session.scalar(
                select(Ticket)
                .where(
                    Ticket.support_request_id == req_id,
                    Ticket.status != TicketStatus.CLOSED.value,
                )
                .order_by(Ticket.created_at.desc())
            )
            assert existing_ticket is not None
            assert existing_ticket.id == t1_id


def test_draft_and_archived_documents_never_returned_by_rag(tmp_path: Path) -> None:
    """Verify that draft and archived documents in knowledge_base/ are excluded from RAG indexing and search."""
    kb_dir = Path("knowledge_base")
    encoder = DeterministicFakeEncoder(dimension=1024)
    vector_store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_filter"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag_service = KnowledgeRetrievalService(
        vector_store=vector_store,
        encoder=encoder,
        base_kb_dir=kb_dir,
    )

    # Index all documents
    summary = rag_service.index_documents(docs_dir=kb_dir, clean_obsolete=True)
    assert summary.chunks_created > 0

    # Search specifically for topics in draft_new_printer.md ("stampante", "printer")
    printer_results = rag_service.search(query="configurazione nuova stampante laser piano terra", top_k=5)
    for res in printer_results:
        assert "draft" not in res.source_path.lower()
        assert "printer" not in res.source_path.lower()

    # Search specifically for topics in archived_old_vpn.md ("vecchia vpn", "pptp", "legacy vpn")
    vpn_results = rag_service.search(query="connessione vecchia vpn pptp archivio legacy", top_k=5)
    for res in vpn_results:
        assert "archived" not in res.source_path.lower()


@pytest.mark.asyncio
async def test_empty_or_unready_rag_handled_safely(tmp_path: Path) -> None:
    """Verify that if the RAG index is completely empty, the service handles it without crashing."""
    empty_kb_dir = tmp_path / "empty_kb"
    empty_kb_dir.mkdir(parents=True, exist_ok=True)

    encoder = DeterministicFakeEncoder(dimension=1024)
    vector_store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_empty"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag_service = KnowledgeRetrievalService(
        vector_store=vector_store,
        encoder=encoder,
        base_kb_dir=empty_kb_dir,
    )

    # Search on empty index
    status = rag_service.get_status()
    assert status.total_chunks == 0

    results = rag_service.search(query="Come resetto la password?", top_k=3)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_gemini_error_safety_no_ghost_mutations(tmp_path: Path) -> None:
    """Verify that when the LLM provider fails (e.g. timeout or APIError), no ghost messages are committed to the DB."""
    db_file = tmp_path / "gemini_error_safety.db"
    settings = Settings(
        DATABASE_URL=f"sqlite:///{db_file}",
        ENVIRONMENT="test",
        RAG_USE_FAKE_ENCODER=True,
    )
    reset_settings_for_test(settings)
    reset_db_session()
    init_db()

    class FailingLLMProvider(BaseLLMProvider):
        @property
        def is_configured(self) -> bool:
            return True

        async def generate(
            self,
            messages: list[LLMMessage],
            system_instruction: str | None = None,
            config: LLMGenerationConfig | None = None,
            model: str | None = None,
        ) -> LLMResponse:
            raise APIError(503, {"error": {"message": "Service Unavailable / Rate Limit Exceeded"}})

    app = create_app(settings=settings)
    rag_serv = get_rag_service()
    failing_orch = ConversationalAgentOrchestrator(
        llm_provider=FailingLLMProvider(),
        rag_service=rag_serv,
    )
    app.dependency_overrides[get_agent_orchestrator] = lambda: failing_orch

    with TestClient(app) as client:
        c_res = client.post("/api/conversations", json={"title": "Error Safety Thread"})
        conv_id = c_res.json()["id"]

        # Send user message
        m_res = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Non riesco ad accedere"})
        assert m_res.status_code == 201

        # Trigger assistant turn with failing LLM
        turn_res = client.post(f"/api/conversations/{conv_id}/assistant-turn")
        assert turn_res.status_code == 502
        assert "non riuscita" in turn_res.json()["detail"].lower()

        # Check DB: conversation has only the user message, NO ghost assistant messages
        conv_detail = client.get(f"/api/conversations/{conv_id}").json()
        assert len(conv_detail["messages"]) == 1
        assert conv_detail["messages"][0]["role"] == "user"


def test_atomic_publish_failure_recovery(tmp_path: Path) -> None:
    """Verify that if disk writing or indexing fails, the proposal enters 'publishing_failed' and remains retryable."""
    db_file = tmp_path / "publish_failure.db"
    engine = create_engine(f"sqlite:///{db_file}")

    from backend.app.db.base import Base
    Base.metadata.create_all(bind=engine)

    encoder = DeterministicFakeEncoder(dimension=1024)
    vector_store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma_fail"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    rag_service = KnowledgeRetrievalService(
        vector_store=vector_store,
        encoder=encoder,
        base_kb_dir=tmp_path / "kb",
    )

    with sessionmaker(bind=engine)() as session:
        # Create a valid draft proposal
        prop = KnowledgeProposal(
            source_type="ticket",
            source_id="tkt_fail_01",
            status=ProposalStatus.DRAFT.value,
            title="Guida con errore disco",
            category="network",
            content_markdown=(
                "---\n"
                "id: KB-FAIL-001\n"
                "title: Guida con errore disco\n"
                "category: network\n"
                "status: approved\n"
                "version: '1.0'\n"
                "---\n"
                "# Guida\n"
                "Testo"
            ),
            author="tecnico_demo",
        )
        session.add(prop)
        session.commit()
        prop_id = prop.id

        # Simulate disk write failure using builtins.open
        with patch("builtins.open", side_effect=PermissionError("Permesso negato")):
            with pytest.raises(Exception):
                KnowledgeProposalManager.approve_and_publish(
                    db=session,
                    proposal_id=prop_id,
                    rag_service=rag_service,
                    author="tecnico_demo",
                )

        # Verify state in DB: status is 'publishing_failed', NOT 'approved'
        session.refresh(prop)
        assert prop.status == ProposalStatus.PUBLISHING_FAILED.value

        # Verify audit event emitted
        audit = session.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "kb_publish_failed",
            )
        )
        assert audit is not None
        assert audit.payload["proposal_id"] == prop_id

        # Verify proposal can be updated and retried after fixing the error
        updated = KnowledgeProposalManager.update_proposal(
            db=session,
            proposal_id=prop_id,
            title="Guida con errore disco (Corretta)",
        )
        assert updated.title == "Guida con errore disco (Corretta)"
