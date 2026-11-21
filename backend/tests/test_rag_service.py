from pathlib import Path

from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore


def test_rag_service_indexing_and_search(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    # Create approved document
    doc1 = kb_dir / "password.md"
    doc1.write_text(
        """---
id: KB-AUTH-001
title: Reset Password
category: Account
tags: [password, reset]
status: approved
---
# Reset Password
Per resettare la password vai al portale self-service.

## Account Bloccato
Attendi 30 minuti o contatta helpdesk.
""",
        encoding="utf-8",
    )

    # Create draft document (should be skipped)
    doc2 = kb_dir / "draft.md"
    doc2.write_text(
        """---
id: KB-DRAFT-001
title: Bozza
category: Test
status: draft
---
# Bozza Segreta
Non visibile.
""",
        encoding="utf-8",
    )

    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(persist_dir=":memory:", model_name=encoder.model_name, dimension=1024)
    service = KnowledgeRetrievalService(encoder=encoder, vector_store=store, base_kb_dir=kb_dir)

    # Index
    summary = service.index_documents(clean_obsolete=True)
    assert summary.documents_scanned == 2
    assert summary.documents_approved == 1
    assert summary.documents_skipped == 1
    assert summary.chunks_created == 2

    # Check status
    status = service.get_status()
    assert status.is_ready is True
    assert status.total_documents == 1
    assert status.total_chunks == 2

    # Search single query
    results = service.search("come sblocco il mio account bloccato?", top_k=2)
    assert len(results) >= 1
    assert results[0].doc_id == "KB-AUTH-001"
    assert "Account Bloccato" in results[0].heading

    # Search multi query
    mq_results = service.search(
        query="problema password",
        sub_queries=["reset account", "account bloccato"],
        top_k=2,
    )
    assert len(mq_results) >= 1
    assert mq_results[0].doc_id == "KB-AUTH-001"


def test_rag_service_clean_obsolete_documents(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    doc1 = kb_dir / "doc1.md"
    doc1.write_text(
        """---
id: KB-001
title: Doc 1
category: Cat1
status: approved
---
# Doc 1
Contenuto primo documento.
""",
        encoding="utf-8",
    )

    doc2 = kb_dir / "doc2.md"
    doc2.write_text(
        """---
id: KB-002
title: Doc 2
category: Cat2
status: approved
---
# Doc 2
Contenuto secondo documento.
""",
        encoding="utf-8",
    )

    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(persist_dir=":memory:", model_name=encoder.model_name, dimension=1024)
    service = KnowledgeRetrievalService(encoder=encoder, vector_store=store, base_kb_dir=kb_dir)

    # First index: 2 docs
    service.index_documents()
    assert service.get_status().total_documents == 2

    # Delete doc2 from filesystem and re-index
    doc2.unlink()
    summary2 = service.index_documents(clean_obsolete=True)
    assert summary2.documents_approved == 1
    assert summary2.chunks_deleted == 1
    assert service.get_status().total_documents == 1
    assert "KB-002" not in service.vector_store.get_indexed_doc_ids()
