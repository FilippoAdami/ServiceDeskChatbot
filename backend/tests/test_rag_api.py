from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.service import (
    KnowledgeRetrievalService,
    reset_rag_service_for_test,
)
from backend.app.rag.vector_store.chroma import ChromaVectorStore


@pytest.fixture
def rag_test_service(tmp_path: Path) -> KnowledgeRetrievalService:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    # Create approved sample doc
    sample_doc = kb_dir / "wifi.md"
    sample_doc.write_text(
        """---
id: KB-NET-002
title: Wi-Fi Aziendale
category: Rete
tags: [wifi, wireless]
status: approved
---
# Connessione Wi-Fi
Per collegarsi alla rete Azienda-Corporate usare credenziali di dominio.

## Errore DHCP
Se ricevi IP 169.254 esegui ipconfig renew.
""",
        encoding="utf-8",
    )

    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    service = KnowledgeRetrievalService(
        encoder=encoder,
        vector_store=store,
        base_kb_dir=kb_dir,
    )
    return service


def test_knowledge_api_unindexed_503(rag_test_service: KnowledgeRetrievalService) -> None:
    reset_rag_service_for_test(rag_test_service)
    app = create_app()
    client = TestClient(app)

    # Status before indexing
    res = client.get("/api/knowledge/status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_ready"] is False
    assert data["total_chunks"] == 0

    # Search should return 503 Service Unavailable when index is empty
    search_res = client.post("/api/knowledge/search", json={"query": "wifi problema"})
    assert search_res.status_code == 503
    assert "unindexed" in search_res.json()["detail"].lower()


def test_knowledge_api_search_and_reindex(rag_test_service: KnowledgeRetrievalService) -> None:
    reset_rag_service_for_test(rag_test_service)
    app = create_app()
    client = TestClient(app)

    # Trigger reindexing
    reindex_res = client.post("/api/knowledge/reindex")
    assert reindex_res.status_code == 200
    reindex_data = reindex_res.json()
    assert reindex_data["documents_approved"] == 1
    assert reindex_data["chunks_created"] == 2

    # Verify status is now ready
    status_res = client.get("/api/knowledge/status")
    assert status_res.status_code == 200
    assert status_res.json()["is_ready"] is True
    assert status_res.json()["total_chunks"] == 2

    # Perform valid search
    search_res = client.post(
        "/api/knowledge/search",
        json={
            "query": "come risolvo ip 169.254 dhcp wifi?",
            "top_k": 2,
            "sub_queries": ["errore ipconfig renew", "wifi non connesso"],
        },
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] >= 1
    assert search_data["results"][0]["doc_id"] == "KB-NET-002"
    assert search_data["elapsed_ms"] >= 0.0


def test_knowledge_api_invalid_query_validation(rag_test_service: KnowledgeRetrievalService) -> None:
    reset_rag_service_for_test(rag_test_service)
    app = create_app()
    client = TestClient(app)

    # Query too short (< 2 chars)
    res = client.post("/api/knowledge/search", json={"query": "a"})
    assert res.status_code == 422
