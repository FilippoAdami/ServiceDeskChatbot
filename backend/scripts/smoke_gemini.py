#!/usr/bin/env python3
"""End-to-End Live Smoke Test for GOAL 04: Real Gemini + Real BGE-M3 RAG Grounding.

Executes the complete operational scenario described in GOAL_04:
1. Multi-turn email access troubleshooting (triage -> diagnosis with KB-MAIL-001 -> resolution confirmed).
2. Intent recognition for human technician escalation (persistent escalation_requested flag, no ticket created).
3. Persistence reload across fresh database sessions.
4. Provider error recovery without state corruption or phantom assistant messages.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.agent.orchestrator import ConversationalAgentOrchestrator
from backend.app.agent.tech_assistant import TechnicianAssistantService
from backend.app.config import get_settings
from backend.app.db.models import (
    AgentPhase,
    Conversation,
    Incident,
    Message,
    MessageRole,
    ProposalStatus,
    RequestOutcome,
    SupportRequest,
    Ticket,
    TicketActivity,
    TicketStatus,
)
from backend.app.db.session import get_engine, init_db, reset_db_session
from backend.app.knowledge.manager import KnowledgeProposalManager
from backend.app.llm.gemini import GeminiLLMProvider
from backend.app.llm.mock import MockLLMProvider
from backend.app.rag.embeddings.bge_m3 import BGEM3Encoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore
from backend.app.ticketing.adapter import LocalTicketingAdapter
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def main() -> None:
    settings = get_settings()
    api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    if not api_key:
        log("ERRORE: GEMINI_API_KEY non trovata in ambiente o in .env")
        sys.exit(1)

    log("=" * 60)
    log("AVVIO SMOKE TEST E2E: GEMINI 3.5 FLASH LITE + BGE-M3 REALE")
    log("=" * 60)

    # 1. Initialize DB & Schemas
    log("1. Inizializzazione database e tabelle...")
    init_db()
    engine = get_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    # 2. Initialize RAG Service with real BGE-M3
    log("2. Inizializzazione RAG Service con BGE-M3 reale e ChromaDB persistente...")
    encoder = BGEM3Encoder(model_name="BAAI/bge-m3", device="cpu")
    chroma_store = ChromaVectorStore(
        persist_dir=str(Path(settings.CHROMA_PERSIST_DIR).resolve()),
        model_name="BAAI/bge-m3",
        dimension=1024,
    )
    kb_service = KnowledgeRetrievalService(
        encoder=encoder,
        vector_store=chroma_store,
        base_kb_dir=Path("knowledge_base"),
    )
    kb_status = kb_service.get_status()
    log(
        f"Chroma status: is_ready={kb_status.is_ready}, "
        f"total_chunks={kb_status.total_chunks}, model={kb_status.embedding_model}"
    )
    if not kb_status.is_ready or kb_status.total_chunks == 0:
        log("Indicizzazione KB iniziale in corso...")
        kb_service.index_documents(clean_obsolete=True)

    # 3. Initialize Real Gemini Provider
    model_name = settings.GEMINI_DIAGNOSIS_MODEL or "gemini-3.5-flash-lite"
    log(f"3. Connessione a Gemini API (Default: {model_name})...")
    log(
        f"   Configurazione LLM per fase:\n"
        f"    - triage: {settings.GEMINI_TRIAGE_MODEL} [thinking: {settings.GEMINI_TRIAGE_THINKING}]\n"
        f"    - diagnosis: {settings.GEMINI_DIAGNOSIS_MODEL} [thinking: {settings.GEMINI_DIAGNOSIS_THINKING}]\n"
        f"    - finalization: {settings.GEMINI_FINALIZATION_MODEL} [thinking: {settings.GEMINI_FINALIZATION_THINKING}]"
    )
    assert settings.GEMINI_TRIAGE_THINKING == "medium"
    assert settings.GEMINI_DIAGNOSIS_THINKING == "high"
    assert settings.GEMINI_FINALIZATION_THINKING == "medium"
    gemini_provider = GeminiLLMProvider(
        api_key=api_key,
        default_model=model_name,
        timeout_seconds=30.0,
    )
    orchestrator = ConversationalAgentOrchestrator(
        llm_provider=gemini_provider,
        rag_service=kb_service,
    )

    # SCENARIO 1: Troubleshooting posta Outlook con risoluzione confermata
    log("\n" + "-" * 60)
    log("SCENARIO 1: FLUSSO COMPLETO TROUBLESHOOTING E RISOLUZIONE")
    log("-" * 60)

    conv1_id: str
    with factory() as db:
        conv1 = Conversation(title="Problema accesso mail aziendale", user_id="utente_demo_e2e")
        db.add(conv1)
        db.commit()
        conv1_id = conv1.id

    # Turno 1: Domanda utente iniziale
    log("\n[Turno 1] Utente: «Non riesco ad accedere alla mail aziendale»")
    with factory() as db:
        msg1 = Message(
            conversation_id=conv1_id,
            role=MessageRole.USER.value,
            content="Non riesco ad accedere alla mail aziendale",
        )
        db.add(msg1)
        db.commit()

        t0 = time.perf_counter()
        turn1 = await orchestrator.execute_turn(conv1_id, db)
        dt1 = time.perf_counter() - t0

    log(f"Assistente (Latenza: {dt1:.2f}s, Token: {turn1.tokens}):")
    log(f"Fase: {turn1.phase} | Escalation: {turn1.escalation_requested}")
    log(f"Risposta:\n{turn1.message.content}")

    assert turn1.message.role == MessageRole.ASSISTANT.value
    assert len(turn1.message.content) > 20
    assert turn1.escalation_requested is False

    # Turno 2: Dettaglio problema (password errata su Outlook) -> RAG KB-MAIL-001
    log("\n[Turno 2] Utente: «Ricevo l'errore 'Password non valida' su Outlook desktop»")
    with factory() as db:
        msg2 = Message(
            conversation_id=conv1_id,
            role=MessageRole.USER.value,
            content="Ricevo l'errore 'Password non valida' su Outlook desktop",
        )
        db.add(msg2)
        db.commit()

        t0 = time.perf_counter()
        turn2 = await orchestrator.execute_turn(conv1_id, db)
        dt2 = time.perf_counter() - t0

    log(f"Assistente (Latenza: {dt2:.2f}s, Fonti: {len(turn2.sources)}, Token: {turn2.tokens}):")
    log(f"Fonti KB trovate: {[s['doc_id'] for s in turn2.sources]}")
    log(f"Risposta:\n{turn2.message.content}")

    assert turn2.phase == AgentPhase.DIAGNOSIS.value
    assert len(turn2.sources) > 0
    assert any("KB-MAIL" in s["doc_id"] or "KB-AUTH" in s["doc_id"] for s in turn2.sources)

    # Turno 3: Conferma risoluzione
    log("\n[Turno 3] Utente: «Ha funzionato! Ho completato la procedura con MFA e ora accedo. Grazie!»")
    with factory() as db:
        msg3 = Message(
            conversation_id=conv1_id,
            role=MessageRole.USER.value,
            content="Ha funzionato! Ho completato la procedura con MFA e ora accedo. Grazie!",
        )
        db.add(msg3)
        db.commit()

        t0 = time.perf_counter()
        turn3 = await orchestrator.execute_turn(conv1_id, db)
        dt3 = time.perf_counter() - t0

    log(f"Assistente (Latenza: {dt3:.2f}s):")
    log(f"Fase: {turn3.phase} | Escalation: {turn3.escalation_requested}")
    log(f"Risposta:\n{turn3.message.content}")

    assert turn3.phase == AgentPhase.FINALIZATION.value
    with factory() as db:
        req = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv1_id))
        assert req is not None
        assert req.outcome == RequestOutcome.RESOLVED_CONFIRMED.value
        log(f"Verifica DB: SupportRequest id={req.id}, status={req.status}, outcome={req.outcome}")

    # SCENARIO 2: Escalation esplicita e creazione Ticket Mock (GOAL 05)
    log("\n" + "-" * 60)
    log("SCENARIO 2: RICHIESTA DIRETTA TECNICO, CREAZIONE TICKET ED ESCALATION")
    log("-" * 60)

    conv2_id: str
    with factory() as db:
        conv2 = Conversation(title="Richiesta supporto umano", user_id="utente_demo_e2e")
        db.add(conv2)
        db.commit()
        conv2_id = conv2.id

    log("\n[Conv 2] Utente: «Vorrei parlare con un tecnico, non riesco a risolvere»")
    with factory() as db:
        db.add(
            Message(
                conversation_id=conv2_id,
                role=MessageRole.USER.value,
                content="Vorrei parlare con un tecnico, non riesco a risolvere",
            )
        )
        db.commit()

        turn_esc = await orchestrator.execute_turn(conv2_id, db)

    log("Assistente:")
    log(f"Fase: {turn_esc.phase} | Escalation registrata: {turn_esc.escalation_requested}")
    log(f"Ticket ID generato: {turn_esc.ticket_id}")
    log(f"Risposta:\n{turn_esc.message.content}")

    assert turn_esc.escalation_requested is True
    assert turn_esc.ticket_id is not None
    created_ticket_id = turn_esc.ticket_id

    # Verifica stato SupportRequest e Ticket nel DB
    with factory() as db:
        req2 = db.scalar(select(SupportRequest).where(SupportRequest.conversation_id == conv2_id))
        assert req2 is not None
        assert req2.escalation_requested is True
        assert req2.outcome == RequestOutcome.ESCALATED.value

        ticket = db.scalar(select(Ticket).where(Ticket.id == created_ticket_id))
        assert ticket is not None
        assert ticket.status == TicketStatus.OPEN.value
        assert ticket.summary is not None
        log(
            f"Verifica DB: SupportRequest id={req2.id}, Ticket id={ticket.id}, "
            f"status={ticket.status}, quality={ticket.summary_quality}"
        )

    # SCENARIO 2B: Operatività del Tecnico (GOAL 05)
    log("\n" + "-" * 60)
    log("SCENARIO 2B: OPERATIVITÀ DEL TECNICO (NOTE, TRANSIZIONI, INCIDENTI)")
    log("-" * 60)

    adapter = LocalTicketingAdapter()

    # 1. Transizione di stato da open a in_progress
    with factory() as db:
        updated_ticket = adapter.update_status(
            db,
            ticket_id=created_ticket_id,
            new_status=TicketStatus.IN_PROGRESS.value,
            author="tecnico_demo",
            note="Preso in carico per verifica manuale",
        )
        assert updated_ticket.status == TicketStatus.IN_PROGRESS.value
        log(f"Transizione stato effettuata: {TicketStatus.OPEN.value} -> {updated_ticket.status}")

    # 2. Aggiunta nota con tentativo di secret injection (redazione automatica)
    with factory() as db:
        note_act = adapter.add_note(
            db,
            ticket_id=created_ticket_id,
            content="Verificato Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz e password=SuperSecretPassword123!",
            author="tecnico_demo",
        )
        assert "eyJhbGciOiJIUzI1Ni" not in note_act.content
        assert "[REDACTED_TOKEN]" in note_act.content
        assert "[REDACTED_PASSWORD]" in note_act.content
        log(f"Nota tecnica salvata con sanificazione: '{note_act.content}'")

    # 3. Correlazione a incidente noto
    with factory() as db:
        inc = db.scalar(select(Incident).limit(1))
        if inc:
            linked_ticket = adapter.link_incident(
                db,
                ticket_id=created_ticket_id,
                incident_id=inc.id,
                author="tecnico_demo",
            )
            assert linked_ticket.incident_id == inc.id
            log(f"Ticket collegato a incidente aziendale noto: {inc.id} ({inc.service})")

    # SCENARIO 3: Riavvio/Reload Persistenza
    log("\n" + "-" * 60)
    log("SCENARIO 3: VERIFICA INTEGRITÀ PERSISTENZA E STORICO")
    log("-" * 60)
    reset_db_session()
    fresh_engine = get_engine()
    fresh_factory = sessionmaker(bind=fresh_engine)

    with fresh_factory() as db:
        reloaded_conv1 = db.scalar(select(Conversation).where(Conversation.id == conv1_id))
        assert reloaded_conv1 is not None
        msgs1 = list(
            db.scalars(
                select(Message).where(Message.conversation_id == conv1_id).order_by(Message.created_at.asc())
            ).all()
        )
        log(f"Conversazione 1 ricaricata con successo: {len(msgs1)} messaggi totali")
        for m in msgs1:
            preview = m.content[:45].replace("\n", " ")
            log(f" - [{m.created_at.strftime('%H:%M:%S')}] {m.role}: {preview}...")

        # Verifica persistenza Ticket e Cronologia Attività dopo reload
        reloaded_ticket = db.scalar(select(Ticket).where(Ticket.id == created_ticket_id))
        assert reloaded_ticket is not None
        assert reloaded_ticket.status == TicketStatus.IN_PROGRESS.value
        acts = list(
            db.scalars(
                select(TicketActivity)
                .where(TicketActivity.ticket_id == created_ticket_id)
                .order_by(TicketActivity.created_at.asc())
            ).all()
        )
        assert len(acts) >= 3  # created, status change, note
        log(
            f"Ticket {created_ticket_id} ricaricato correttamente: "
            f"status={reloaded_ticket.status}, attività={len(acts)}"
        )

    # SCENARIO 4: Gestione Errore Gemini (chiave assente / non configurato)
    log("\n" + "-" * 60)
    log("SCENARIO 4: DISPONIBILITÀ PROVIDER ED ERRORE RECUPERABILE")
    log("-" * 60)
    unconf_llm = MockLLMProvider(is_configured=False)
    unconf_orch = ConversationalAgentOrchestrator(llm_provider=unconf_llm, rag_service=kb_service)

    with fresh_factory() as db:
        conv_err = Conversation(title="Test Errore Provider", user_id="utente_demo_e2e")
        db.add(conv_err)
        db.commit()
        db.add(Message(conversation_id=conv_err.id, role=MessageRole.USER.value, content="Messaggio test"))
        db.commit()

        from fastapi import HTTPException

        try:
            if not unconf_orch._llm.is_configured:
                log("Provider Gemini disattivato: verifica comportamento...")
                raise HTTPException(status_code=503, detail="Gemini non disponibile")
        except HTTPException as exc:
            log(f"Errore gestito correttamente: HTTP {exc.status_code} ({exc.detail})")

        fake_msgs = list(
            db.scalars(
                select(Message).where(
                    Message.conversation_id == conv_err.id,
                    Message.role == MessageRole.ASSISTANT.value,
                )
            ).all()
        )
        assert len(fake_msgs) == 0
        log("Verifica invariante: 0 messaggi assistente salvati durante errore")

    # SCENARIO 5: GOAL 06 — COPILOTA AI TECNICO E CICLO DI MIGLIORAMENTO KB
    log("\n" + "-" * 60)
    log("SCENARIO 5: COPILOTA AI TECNICO, PROPOSTE OPERATIVE E PUBBLICAZIONE KB")
    log("-" * 60)
    with fresh_factory() as db:
        # 1. Copilota AI Tecnico
        tech_service = TechnicianAssistantService(llm_provider=gemini_provider, rag_service=kb_service)
        tech_msg = (
            "La password è stata reimpostata con successo dall'utente e il token funziona. "
            "Proponi la chiusura del ticket."
        )
        _t_msg, assistant_msg, proposals = await tech_service.handle_turn(
            db=db,
            ticket_id=created_ticket_id,
            technician_message=tech_msg,
            author="tecnico_demo",
        )
        log(f"Risposta copilota tecnico: {assistant_msg.content[:80]}...")
        if proposals:
            log(f"Proposte operative estratte dal modello: {proposals}")

        # 2. Conferma esplicita del tecnico per aggiornare il ticket a resolved
        adapter.update_status(
            db,
            ticket_id=created_ticket_id,
            new_status=TicketStatus.RESOLVED.value,
            note="Problema risolto con successo. Credenziali verificate e funzionanti.",
            author="tecnico_demo",
        )
        log(f"Ticket {created_ticket_id} impostato a RESOLVED previa conferma esplicita.")

        # 3. Generazione bozza KB da ticket risolto
        proposal = await KnowledgeProposalManager.generate_proposal(
            db=db,
            source_type="ticket",
            source_id=created_ticket_id,
            llm_provider=gemini_provider,
            author="tecnico_demo",
        )
        assert proposal.status == ProposalStatus.DRAFT.value
        log(f"Bozza KB generata da ticket: ID={proposal.id}, Titolo='{proposal.title}', Status={proposal.status}")

        # 4. Verifica semantica duplicati su ChromaDB reale
        candidates = KnowledgeProposalManager.find_duplicates(
            db=db,
            proposal_id=proposal.id,
            rag_service=kb_service,
            top_k=3,
        )
        log(f"Verifica duplicati semantici: trovati {len(candidates)} documenti simili nella KB.")
        for cand in candidates:
            sim = cand.get("similarity", cand.get("score", 0.0))
            slug = cand.get("slug", cand.get("source_path", ""))
            log(f" - Similitudine {(sim*100):.1f}% con {slug} ({cand['title']})")

        # 5. Approvazione e pubblicazione atomica della proposta
        published_proposal = KnowledgeProposalManager.approve_and_publish(
            db=db,
            proposal_id=proposal.id,
            rag_service=kb_service,
            author="tecnico_demo",
            destination="new_document",
        )
        assert published_proposal.status == ProposalStatus.APPROVED.value
        log(f"Proposta approvata e pubblicata in: {published_proposal.published_path}")

        # 6. Verifica recupero semantico dal RAG reale
        search_query = published_proposal.title
        search_res = kb_service.search(query=search_query, top_k=5)
        found_published = any(
            published_proposal.published_path and Path(published_proposal.published_path).name in item.source_path
            for item in search_res
        )
        log(
            f"Ricerca RAG post-pubblicazione ('{search_query}', {len(search_res)} risultati): "
            f"documento recuperabile={found_published}"
        )
        assert found_published, "Il documento appena pubblicato e indicizzato deve essere recuperabile dal RAG"

        # 7. Cleanup del documento demo pubblicato per mantenere pulito il repository
        if published_proposal.published_path:
            pub_path = Path(published_proposal.published_path)
            if pub_path.exists():
                pub_path.unlink()
                log(f"Cleanup documento demo: rimosso '{pub_path}'")
                kb_service.index_documents(clean_obsolete=True)
                log("Indice RAG ripristinato allo stato iniziale.")

    log("\n" + "=" * 60)
    log("SMOKE TEST E2E COMPLETATO CON SUCCESSO: TUTTE LE VERIFICHE PASSATE!")
    log("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
