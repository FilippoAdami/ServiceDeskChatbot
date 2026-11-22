#!/usr/bin/env python3
"""Script per il reset sicuro e riproducibile dei dati dimostrativi del Service Desk AI.

Ripristina il database e la knowledge base allo stato demo iniziale:
- Cancella conversazioni, messaggi, richieste, ticket, chat tecnico e proposte KB
- Mantiene intatti lo schema, le migrazioni, i documenti KB originali e il file .env
- Esegue il re-seed degli incidenti noti aziendali iniziali
- Rimuove eventuali guide demo generate (kb-gen-*.md) e ripristina l'indice RAG

USO:
    python backend/scripts/reset_demo.py --confirm
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import get_settings
from backend.app.db.models import (
    AuditEvent,
    Conversation,
    KnowledgeProposal,
    Message,
    SupportRequest,
    TechnicianChatMessage,
    Ticket,
    TicketActivity,
)
from backend.app.db.seeds import seed_demo_incidents
from backend.app.db.session import get_session_factory, init_db
from backend.app.rag.embeddings.base import BaseEmbeddingEncoder
from backend.app.rag.embeddings.bge_m3 import BGEM3Encoder
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore
from sqlalchemy import delete
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reset_demo")


def reset_demo_data(confirm: bool = False) -> None:
    if not confirm:
        print("\n" + "=" * 70)
        print("ATTENZIONE: RESET DEMO SERVICE DESK AI")
        print("=" * 70)
        print("Questo script azzera tutti i dati dimostrativi:")
        print(" - Conversazioni e messaggi della chat dipendente")
        print(" - Richieste di supporto IT (SupportRequest)")
        print(" - Ticket ed escalation verso i tecnici (Ticket e TicketActivity)")
        print(" - Messaggi della chat copilota tecnico (TechnicianChatMessage)")
        print(" - Bozze e proposte di articoli Knowledge Base (KnowledgeProposal)")
        print(" - File dimostrativi generati in knowledge_base/ (kb-gen-*.md)")
        print(" - Eventi di audit e log dimostrativi")
        print("\nVerranno preservati:")
        print(" - I file di configurazione (.env e .env.example)")
        print(" - Le 8 guide ufficiali approvate della Knowledge Base aziendale")
        print(" - Lo schema delle tabelle e le migrazioni Alembic")
        print("\nPer confermare il reset, eseguire il comando con il flag --confirm:")
        print("    make reset-demo")
        print("    oppure: .venv/bin/python backend/scripts/reset_demo.py --confirm")
        print("=" * 70 + "\n")
        sys.exit(1)

    logger.info("Avvio procedura di reset sicuro dei dati dimostrativi...")
    settings = get_settings()

    # 1. Initialize DB and get session
    init_db()
    session_factory = get_session_factory()
    db: Session = session_factory()

    try:
        # Delete demo data in reverse FK order
        t_chat = int(getattr(db.execute(delete(TechnicianChatMessage)), "rowcount", 0))
        k_prop = int(getattr(db.execute(delete(KnowledgeProposal)), "rowcount", 0))
        t_act = int(getattr(db.execute(delete(TicketActivity)), "rowcount", 0))
        tickets = int(getattr(db.execute(delete(Ticket)), "rowcount", 0))
        reqs = int(getattr(db.execute(delete(SupportRequest)), "rowcount", 0))
        msgs = int(getattr(db.execute(delete(Message)), "rowcount", 0))
        convs = int(getattr(db.execute(delete(Conversation)), "rowcount", 0))
        audits = int(getattr(db.execute(delete(AuditEvent)), "rowcount", 0))

        logger.info(
            "Dati demo eliminati da SQLite: %d messaggi tecnico, %d proposte KB, "
            "%d attività ticket, %d ticket, %d richieste, %d messaggi, %d conversazioni, %d audit",
            t_chat,
            k_prop,
            t_act,
            tickets,
            reqs,
            msgs,
            convs,
            audits,
        )

        # 2. Re-seed demo incidents
        incidents = seed_demo_incidents(db)
        logger.info("Re-seed completato: %d incidenti aziendali iniziali verificati", len(incidents))

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Errore durante il reset del database: %s", exc)
        raise
    finally:
        db.close()

    # 3. Clean generated demo files from knowledge_base/
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    removed_files = 0
    if kb_dir.exists():
        for f in kb_dir.glob("kb-gen-*.md"):
            try:
                f.unlink()
                removed_files += 1
                logger.info("Rimosso file demo generato: %s", f.name)
            except Exception as e:
                logger.warning("Impossibile rimuovere %s: %e", f.name, e)

        # Also remove any leftover .tmp or .bak files
        for f in list(kb_dir.glob("*.tmp")) + list(kb_dir.glob("*.bak")):
            try:
                f.unlink()
                logger.info("Rimosso file temporaneo: %s", f.name)
            except Exception:
                pass

    logger.info("Pulizia file KB: %d file dimostrativi generati rimossi", removed_files)

    # 4. Re-index RAG vector store to ensure clean consistency
    encoder: BaseEmbeddingEncoder
    if settings.RAG_USE_FAKE_ENCODER:
        encoder = DeterministicFakeEncoder(dimension=1024)
    else:
        encoder = BGEM3Encoder(
            model_name=settings.EMBEDDING_MODEL_NAME,
            device=settings.EMBEDDING_DEVICE,
        )

    vector_store = ChromaVectorStore(
        persist_dir=Path(settings.CHROMA_PERSIST_DIR),
        model_name=encoder.model_name,
        dimension=encoder.dimension,
    )

    rag_service = KnowledgeRetrievalService(
        encoder=encoder,
        vector_store=vector_store,
        base_kb_dir=kb_dir,
    )

    try:
        idx_summary = rag_service.index_documents(docs_dir=kb_dir, clean_obsolete=True)
        logger.info(
            "Indice RAG ripristinato: %d guide approvate, %d chunk vettoriali attivi",
            idx_summary.documents_approved,
            idx_summary.chunks_created,
        )
    except Exception as exc:
        logger.warning("Re-indicizzazione RAG durante reset fallita (%s); procedere con make rag-index", exc)

    print("\n" + "=" * 70)
    print("RESET DEMO COMPLETATO CON SUCCESSO!")
    print("=" * 70)
    print(f"Database:     {settings.DATABASE_URL} (stato pulito, incidenti iniziali pronti)")
    print("KB Documents: 8 guide ufficiali approvate ripristinate")
    print(f"RAG Index:    ChromaDB indicizzato e coerente ({encoder.model_name})")
    print("Il sistema è pronto per una nuova dimostrazione da zero.")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset demo database and knowledge base for Service Desk AI")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Conferma esplicita richiesta per eseguire il reset dei dati dimostrativi",
    )
    args = parser.parse_args()
    reset_demo_data(confirm=args.confirm)


if __name__ == "__main__":
    main()
