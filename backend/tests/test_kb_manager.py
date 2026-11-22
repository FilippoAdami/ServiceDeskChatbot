from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Conversation,
    KnowledgeProposal,
    ProposalDestination,
    ProposalSourceType,
    ProposalStatus,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
)
from backend.app.knowledge.manager import KnowledgeProposalManager
from backend.app.rag.embeddings.fake import DeterministicFakeEncoder
from backend.app.rag.parser import parse_markdown_content
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.rag.vector_store.chroma import ChromaVectorStore


@pytest.fixture
def temp_kb_dir(tmp_path: Path) -> Path:
    """Fixture providing an isolated temporary knowledge base directory."""
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir


@pytest.fixture
def isolated_rag_service(temp_kb_dir: Path) -> KnowledgeRetrievalService:
    """Fixture providing a test KnowledgeRetrievalService with temporary directory and fake encoder."""
    encoder = DeterministicFakeEncoder(dimension=1024)
    vector_store = ChromaVectorStore(
        persist_dir=str(temp_kb_dir / "chroma"),
        model_name=encoder.model_name,
        dimension=1024,
    )
    service = KnowledgeRetrievalService(
        vector_store=vector_store,
        encoder=encoder,
        base_kb_dir=temp_kb_dir,
    )
    return service


@pytest.fixture
def sample_confirmed_request(db_session: Session) -> SupportRequest:
    """Fixture for a resolved and confirmed support request."""
    conv = Conversation(title="Reset MFA", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema Notifica MFA",
        description="Notifica push Authenticator non perviene sullo smartphone.",
        initial_category="auth",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.RESOLVED_CONFIRMED.value,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


@pytest.mark.asyncio
async def test_generate_and_list_proposals(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
) -> None:
    """Test generating a draft proposal and listing with filters."""
    prop1 = await KnowledgeProposalManager.generate_proposal(
        db=db_session,
        source_type="support_request",
        source_id=sample_confirmed_request.id,
        author="technician_01",
    )
    assert prop1.status == ProposalStatus.DRAFT.value
    assert prop1.source_id == sample_confirmed_request.id
    assert "MFA" in prop1.title

    # Idempotent: generating again returns existing active draft
    prop2 = await KnowledgeProposalManager.generate_proposal(
        db=db_session,
        source_type="support_request",
        source_id=sample_confirmed_request.id,
        author="technician_01",
    )
    assert prop1.id == prop2.id

    # List proposals
    items, total = KnowledgeProposalManager.list_proposals(
        db=db_session,
        status_filter=ProposalStatus.DRAFT.value,
    )
    assert total >= 1
    assert any(p.id == prop1.id for p in items)


def test_update_proposal_and_validation(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
) -> None:
    """Test editing a draft proposal and state transition constraints."""
    md_sample = (
        "---\nid: KB-AUTH-001\ntitle: Titolo\ncategory: auth\nstatus: draft\nversion: '1.0'\n---\n# Titolo"
    )
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=sample_confirmed_request.id,
        status=ProposalStatus.DRAFT.value,
        title="Titolo Bozza",
        category="auth",
        content_markdown=md_sample,
        author="technician_01",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    updated = KnowledgeProposalManager.update_proposal(
        db=db_session,
        proposal_id=prop.id,
        title="Titolo Modificato dal Tecnico",
        notes="Modificato per maggiore chiarezza.",
    )
    assert updated.title == "Titolo Modificato dal Tecnico"

    # Cannot edit approved proposal
    prop.status = ProposalStatus.APPROVED.value
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        KnowledgeProposalManager.update_proposal(
            db=db_session,
            proposal_id=prop.id,
            title="Altra Modifica",
        )
    assert exc_info.value.status_code == 409


def test_reject_proposal(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
) -> None:
    """Test rejecting a proposal."""
    md_sample = (
        "---\nid: KB-AUTH-999\ntitle: Titolo\ncategory: auth\nstatus: draft\nversion: '1.0'\n---\n# Titolo"
    )
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=sample_confirmed_request.id,
        status=ProposalStatus.DRAFT.value,
        title="Bozza da Rifiutare",
        category="auth",
        content_markdown=md_sample,
    )
    db_session.add(prop)
    db_session.commit()

    rejected = KnowledgeProposalManager.reject_proposal(
        db=db_session,
        proposal_id=prop.id,
        reason="Procedura già coperta da KB-AUTH-001.",
    )
    assert rejected.status == ProposalStatus.REJECTED.value
    assert "KB-AUTH-001" in (rejected.rejection_reason or "")


def test_approve_and_publish_atomic_success(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
    isolated_rag_service: KnowledgeRetrievalService,
    temp_kb_dir: Path,
) -> None:
    """Test approving and publishing a proposal with atomic file write and RAG indexing."""
    valid_markdown = """---
id: KB-AUTH-888
title: Guida Autenticazione Avanzata
category: account
status: draft
version: '1.0'
tags: [auth, mfa]
---
# Guida Autenticazione Avanzata
## Descrizione e Sintomi Rilevati
Descrizione
## Procedura di Risoluzione
Passo 1. Verifica impostazioni.
"""
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=sample_confirmed_request.id,
        status=ProposalStatus.DRAFT.value,
        title="Guida Autenticazione Avanzata",
        category="account",
        content_markdown=valid_markdown,
        destination=ProposalDestination.CREATE.value,
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    published = KnowledgeProposalManager.approve_and_publish(
        db=db_session,
        proposal_id=prop.id,
        rag_service=isolated_rag_service,
        base_kb_dir=temp_kb_dir,
    )

    assert published.status == ProposalStatus.APPROVED.value
    assert published.published_path is not None
    assert (temp_kb_dir.parent / published.published_path).exists()

    # Verify that the written file has status 'approved'
    written_content = (temp_kb_dir.parent / published.published_path).read_text(encoding="utf-8")
    fm, _ = parse_markdown_content(written_content, source_path=published.published_path)
    assert fm.status == "approved"

    # Verify that RAG indexed the document and it can be retrieved
    results = isolated_rag_service.search("Guida Autenticazione Avanzata", top_k=3)
    assert len(results) > 0
    assert results[0].doc_id == "KB-AUTH-888"


def test_approve_and_publish_invalid_front_matter_422(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
    isolated_rag_service: KnowledgeRetrievalService,
    temp_kb_dir: Path,
) -> None:
    """Test that invalid front matter is rejected with 422 before writing any file."""
    invalid_markdown = "# Nessun Front Matter Presente\nSolo testo Markdown."

    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=sample_confirmed_request.id,
        status=ProposalStatus.DRAFT.value,
        title="Bozza Errata",
        category="account",
        content_markdown=invalid_markdown,
    )
    db_session.add(prop)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        KnowledgeProposalManager.approve_and_publish(
            db=db_session,
            proposal_id=prop.id,
            rag_service=isolated_rag_service,
            base_kb_dir=temp_kb_dir,
        )
    assert exc_info.value.status_code == 422


def test_approve_and_publish_path_traversal_400(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
    isolated_rag_service: KnowledgeRetrievalService,
    temp_kb_dir: Path,
) -> None:
    """Test that malicious path traversal attempts are blocked."""
    valid_markdown = """---
id: KB-AUTH-999
title: Traversal Attack
category: account
status: draft
version: '1.0'
---
# Attack
"""
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=sample_confirmed_request.id,
        status=ProposalStatus.DRAFT.value,
        title="Traversal Attack",
        category="account",
        content_markdown=valid_markdown,
        destination=ProposalDestination.UPDATE.value,
        target_kb_slug="../../malicious_escape.md",
    )
    db_session.add(prop)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        KnowledgeProposalManager.approve_and_publish(
            db=db_session,
            proposal_id=prop.id,
            rag_service=isolated_rag_service,
            base_kb_dir=temp_kb_dir,
        )
    assert exc_info.value.status_code == 400


def test_approve_and_publish_update_increments_version(
    db_session: Session,
    sample_confirmed_request: SupportRequest,
    isolated_rag_service: KnowledgeRetrievalService,
    temp_kb_dir: Path,
) -> None:
    """Test updating existing document increments version and creates backup."""
    existing_file = temp_kb_dir / "kb_auth_001_policy.md"
    existing_file.write_text(
        """---
id: KB-AUTH-001
title: Policy Account Esistente
category: account
status: approved
version: '1.0'
---
# Original
""",
        encoding="utf-8",
    )

    update_markdown = """---
id: KB-AUTH-001
title: Policy Account Esistente
category: account
status: draft
version: '1.0'
---
# Aggiornamento Policy
Nuovi requisiti password e MFA.
"""
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=sample_confirmed_request.id,
        status=ProposalStatus.DRAFT.value,
        title="Policy Account Esistente",
        category="account",
        content_markdown=update_markdown,
        destination=ProposalDestination.UPDATE.value,
        target_kb_slug="kb_auth_001_policy.md",
        version=1,
    )
    db_session.add(prop)
    db_session.commit()

    published = KnowledgeProposalManager.approve_and_publish(
        db=db_session,
        proposal_id=prop.id,
        rag_service=isolated_rag_service,
        base_kb_dir=temp_kb_dir,
    )

    assert published.version == 2
    # Check that backup file was created
    backup_file = temp_kb_dir / "kb_auth_001_policy.md.bak"
    assert backup_file.exists()
    assert "Original" in backup_file.read_text(encoding="utf-8")
