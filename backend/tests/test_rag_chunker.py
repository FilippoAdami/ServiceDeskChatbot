from backend.app.rag.chunker import chunk_document, slugify
from backend.app.rag.models import KBDocument, KBFrontMatter


def test_slugify() -> None:
    assert slugify("Procedura di Reset Password") == "procedura-di-reset-password"
    assert slugify("Wi-Fi & Rete 100%") == "wi-fi-rete-100"
    assert slugify("---") == "section"


def test_chunk_document_headings() -> None:
    fm = KBFrontMatter(
        id="KB-NET-001",
        title="Guida VPN",
        category="Rete",
        tags=["vpn", "remoto"],
        status="approved",
        version="1.0",
    )
    content = """# Guida VPN Aziendale
Introduzione al servizio VPN.

## Prerequisiti
1. Notebook aziendale.
2. Certificato valido.

## Risoluzione Errori
Se ricevi errore timeout, riavvia il router.
"""
    doc = KBDocument(front_matter=fm, content=content, source_path="vpn.md", raw_text=content)

    chunks = chunk_document(doc)
    assert len(chunks) == 3

    # Check deterministic chunk ID formatting
    assert chunks[0].chunk_id == "KB-NET-001#guida-vpn-aziendale#0"
    assert chunks[0].heading == "Guida VPN Aziendale"
    assert "[Guida VPN > Guida VPN Aziendale]" in chunks[0].text
    assert chunks[0].doc_id == "KB-NET-001"
    assert chunks[0].category == "Rete"

    assert chunks[1].chunk_id == "KB-NET-001#prerequisiti#1"
    assert chunks[1].heading == "Prerequisiti"

    assert chunks[2].chunk_id == "KB-NET-001#risoluzione-errori#2"
    assert chunks[2].heading == "Risoluzione Errori"


def test_chunk_document_long_section_splitting() -> None:
    fm = KBFrontMatter(
        id="KB-BIG-001",
        title="Documento Lungo",
        category="Test",
        status="approved",
    )
    long_paragraphs = [
        (f"Paragrafo {i} con un contenuto descrittivo per verificare la suddivisione in sottochunk " * 10)
        for i in range(10)
    ]

    content = "## Sezione Gigante\n\n" + "\n\n".join(long_paragraphs)
    doc = KBDocument(front_matter=fm, content=content, source_path="big.md", raw_text=content)

    chunks = chunk_document(doc, max_chunk_chars=600, chunk_overlap_chars=100)
    assert len(chunks) > 1
    # Check that each chunk has sequential indices and deterministic ids
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert f"#{idx}" in c.chunk_id
        assert c.doc_id == "KB-BIG-001"
