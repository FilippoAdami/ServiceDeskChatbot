#!/usr/bin/env python3
"""CLI utility to index knowledge base Markdown documents into persistent ChromaDB."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import get_settings
from backend.app.rag.embeddings.base import BaseEmbeddingEncoder
from backend.app.rag.embeddings.bge_m3 import BGEM3Encoder
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("index_kb")



def main() -> None:
    parser = argparse.ArgumentParser(description="Index knowledge base documents into ChromaDB")
    parser.add_argument(
        "--kb-dir",
        type=str,
        default="knowledge_base",
        help="Directory containing Markdown KB documents",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="./data/chroma_db",
        help="Persistent storage path for ChromaDB",
    )
    parser.add_argument(
        "--fake-encoder",
        action="store_true",
        help="Use deterministic offline fake encoder (fast, no PyTorch / model weights required)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean obsolete chunks from deleted or unapproved documents",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Completely reset and rebuild the Chroma collection from scratch",
    )

    args = parser.parse_args()
    settings = get_settings()

    kb_dir = Path(args.kb_dir)
    persist_dir = Path(args.persist_dir)

    logger.info("Initializing Knowledge Base indexer...")
    logger.info("KB Directory: %s", kb_dir.resolve())
    logger.info("Chroma Persist Dir: %s", persist_dir.resolve())

    encoder: BaseEmbeddingEncoder
    if args.fake_encoder or settings.RAG_USE_FAKE_ENCODER:
        logger.info("Using DeterministicFakeEncoder (offline, 1024 dims)")
        encoder = DeterministicFakeEncoder(dimension=1024)
    else:
        logger.info("Using BGEM3Encoder (BGE-M3, device=%s)", settings.EMBEDDING_DEVICE)
        encoder = BGEM3Encoder(
            model_name=settings.EMBEDDING_MODEL_NAME,
            device=settings.EMBEDDING_DEVICE,
        )


    vector_store = ChromaVectorStore(
        persist_dir=persist_dir,
        model_name=encoder.model_name,
        dimension=encoder.dimension,
    )

    if args.reset:
        logger.info("Resetting Chroma collection...")
        vector_store.reset()

    service = KnowledgeRetrievalService(
        encoder=encoder,
        vector_store=vector_store,
        base_kb_dir=kb_dir,
    )

    summary = service.index_documents(docs_dir=kb_dir, clean_obsolete=args.clean or True)

    print("\n" + "=" * 60)
    print("KNOWLEDGE BASE INDEXING SUMMARY")
    print("=" * 60)
    print(f"Documents Scanned:  {summary.documents_scanned}")
    print(f"Documents Approved: {summary.documents_approved}")
    print(f"Documents Skipped:  {summary.documents_skipped}")
    print(f"Chunks Created:     {summary.chunks_created}")
    print(f"Chunks Deleted:     {summary.chunks_deleted}")
    print(f"Elapsed Time:       {summary.elapsed_seconds:.3f} s")
    print(f"Timestamp:          {summary.timestamp}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
