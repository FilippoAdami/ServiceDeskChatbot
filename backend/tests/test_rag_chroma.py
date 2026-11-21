from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.models import KBChunk
from backend.app.rag.vector_store.chroma import ChromaVectorStore


def test_chroma_store_in_memory() -> None:
    encoder = DeterministicFakeEncoder(dimension=1024)
    store = ChromaVectorStore(
        persist_dir=":memory:",
        model_name=encoder.model_name,
        dimension=encoder.dimension,
        collection_name="test_chroma_store",
    )


    assert store.count_chunks() == 0
    assert store.get_indexed_doc_ids() == set()

    chunks = [
        KBChunk(
            chunk_id="KB-001#sec1#0",
            doc_id="KB-001",
            doc_title="Doc Uno",
            category="Cat1",
            heading="Sezione 1",
            chunk_index=0,
            text="Testo per la sezione uno relativa a password",
            source_path="kb/doc1.md",
            metadata={"doc_id": "KB-001"},
        ),
        KBChunk(
            chunk_id="KB-002#sec1#0",
            doc_id="KB-002",
            doc_title="Doc Due",
            category="Cat2",
            heading="Sezione VPN",
            chunk_index=0,
            text="Testo per la sezione vpn e connessione remota",
            source_path="kb/doc2.md",
            metadata={"doc_id": "KB-002"},
        ),
    ]

    embeddings = encoder.encode_documents([c.text for c in chunks])
    store.add_chunks(chunks, embeddings)

    assert store.count_chunks() == 2
    assert store.get_indexed_doc_ids() == {"KB-001", "KB-002"}

    # Query for password
    q_emb = encoder.encode_queries(["reset password"])[0]
    results = store.query_similar(q_emb, top_k=2)

    assert len(results) == 2
    assert results[0].doc_id == "KB-001"
    assert results[0].score > 0.0

    # Delete doc 1 chunks
    deleted = store.delete_document_chunks(["KB-001"])
    assert deleted == 1
    assert store.count_chunks() == 1
    assert store.get_indexed_doc_ids() == {"KB-002"}
