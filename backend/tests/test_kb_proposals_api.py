from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Conversation,
    KnowledgeProposal,
    ProposalSourceType,
    ProposalStatus,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
)
from backend.app.llm import reset_llm_provider_for_test
from backend.app.llm.mock import MockLLMProvider


@pytest.fixture(autouse=True)
def mock_llm_for_kb_proposals():
    mock = MockLLMProvider()
    reset_llm_provider_for_test(mock)
    yield mock
    reset_llm_provider_for_test(None)


@pytest.fixture
def confirmed_request_api(db_session: Session) -> SupportRequest:
    """Fixture to create a confirmed support request for KB proposal API testing."""
    conv = Conversation(title="Reset MFA API", user_id="user_api_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema Notifica MFA Smartphone",
        description="Notifica push Authenticator non recapitata.",
        initial_category="auth",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.RESOLVED_CONFIRMED.value,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def test_list_kb_proposals_api(client: TestClient) -> None:
    """Test listing proposals endpoint with pagination."""
    resp = client.get("/api/kb-proposals?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_generate_kb_proposal_api_success_and_validation(
    client: TestClient,
    confirmed_request_api: SupportRequest,
) -> None:
    """Test generating KB proposal via API: 201 on confirmed, 404 on nonexistent."""
    resp = client.post(
        "/api/kb-proposals/generate",
        json={
            "source_type": "support_request",
            "source_id": confirmed_request_api.id,
            "author": "technician_demo",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == confirmed_request_api.id
    assert data["status"] == "draft"
    assert "content_markdown" in data

    # 404 for nonexistent source
    resp_404 = client.post(
        "/api/kb-proposals/generate",
        json={
            "source_type": "support_request",
            "source_id": "nonexistent_request_id",
            "author": "technician_demo",
        },
    )
    assert resp_404.status_code == 404


def test_get_and_update_kb_proposal_api(
    client: TestClient,
    db_session: Session,
    confirmed_request_api: SupportRequest,
) -> None:
    """Test retrieving detail and editing a draft proposal via API."""
    md_sample = (
        "---\nid: KB-AUTH-001\ntitle: Bozza Test API\ncategory: auth\nstatus: draft\nversion: '1.0'\n---\n# Bozza"
    )
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=confirmed_request_api.id,
        status=ProposalStatus.DRAFT.value,
        title="Bozza Test API",
        category="auth",
        content_markdown=md_sample,
        author="technician_demo",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    # GET detail
    resp = client.get(f"/api/kb-proposals/{prop.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == prop.id

    # PUT update
    update_resp = client.put(
        f"/api/kb-proposals/{prop.id}",
        json={
            "title": "Titolo Aggiornato via API",
            "notes": "Revisione completata con successo.",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Titolo Aggiornato via API"


def test_reject_kb_proposal_api(
    client: TestClient,
    db_session: Session,
    confirmed_request_api: SupportRequest,
) -> None:
    """Test rejecting a proposal via API."""
    md_sample = (
        "---\nid: KB-AUTH-002\ntitle: Bozza Rifiuto\ncategory: auth\nstatus: draft\nversion: '1.0'\n---\n# Content"
    )
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=confirmed_request_api.id,
        status=ProposalStatus.DRAFT.value,
        title="Bozza Rifiuto API",
        category="auth",
        content_markdown=md_sample,
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    resp = client.post(
        f"/api/kb-proposals/{prop.id}/reject",
        json={"reason": "Non necessaria.", "author": "technician_demo"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["rejection_reason"] == "Non necessaria."


def test_publish_invalid_front_matter_api_422(
    client: TestClient,
    db_session: Session,
    confirmed_request_api: SupportRequest,
) -> None:
    """Test publishing proposal with malformed front matter returns 422."""
    prop = KnowledgeProposal(
        source_type=ProposalSourceType.SUPPORT_REQUEST.value,
        source_id=confirmed_request_api.id,
        status=ProposalStatus.DRAFT.value,
        title="Bozza Invalida",
        category="auth",
        content_markdown="# No Front Matter At All",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    resp = client.post(
        f"/api/kb-proposals/{prop.id}/publish",
        json={"author": "technician_demo"},
    )
    assert resp.status_code == 422
