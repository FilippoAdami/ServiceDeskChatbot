from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Conversation,
    Message,
    MessageRole,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
    TicketPriority,
    TicketStatus,
)
from backend.app.knowledge.generator import (
    generate_doc_id,
    generate_kb_proposal_markdown,
)
from backend.app.llm.mock import MockLLMProvider
from backend.app.rag.parser import parse_markdown_content
from backend.app.ticketing.adapter import LocalTicketingAdapter


def test_generate_doc_id() -> None:
    """Test standard document ID generation format."""
    doc_id = generate_doc_id("auth", "req_001")
    assert doc_id.startswith("KB-AUTH-")
    doc_id_net = generate_doc_id("network", "tick_999")
    assert doc_id_net.startswith("KB-NET-")


@pytest.mark.asyncio
async def test_bot_origin_resolved_confirmed(db_session: Session) -> None:
    """Test generating a KB draft from a bot resolution confirmed by the user."""
    conv = Conversation(title="Reset MFA Utenza", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema accesso app Authenticator",
        description="L'app Microsoft Authenticator non mostra la notifica push.",
        initial_category="auth",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.RESOLVED_CONFIRMED.value,
    )
    db_session.add(req)
    db_session.flush()

    # Add conversation messages
    m1 = Message(conversation_id=conv.id, role=MessageRole.USER.value, content="Non ricevo il push MFA.")
    m2 = Message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT.value,
        content="Verifica che la modalità risparmio batteria sia disattivata per Authenticator.",
    )
    m3 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="Fatto, ora il codice push arriva! Risolto, grazie!",
    )
    db_session.add_all([m1, m2, m3])
    db_session.commit()

    mock_llm = MockLLMProvider(is_configured=False)
    md_content, title, cat, quality = await generate_kb_proposal_markdown(
        source_type="support_request",
        source_obj=req,
        messages=[m1, m2, m3],
        llm_provider=mock_llm,
    )

    assert quality == "fallback"
    assert cat == "auth"
    assert "Authenticator" in title

    # Validate that generated markdown has valid front matter adhering to KBFrontMatter schema
    fm, body = parse_markdown_content(md_content, source_path="test.md")
    assert fm.id.startswith("KB-AUTH-")
    assert fm.status == "draft"
    assert fm.version == "1.0"
    assert "Procedura di Risoluzione" in body


@pytest.mark.asyncio
async def test_bot_origin_unconfirmed_rejected(db_session: Session) -> None:
    """Test that requests with unconfirmed resolution or abandonment cannot generate KB proposals."""
    conv = Conversation(title="Tentativo non confermato", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Password dimenticata",
        description="Password non funziona.",
        initial_category="auth",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.RESOLVED_UNCONFIRMED.value,  # NOT confirmed
    )
    db_session.add(req)
    db_session.commit()

    with pytest.raises(ValueError, match="richiesta non confermata"):
        await generate_kb_proposal_markdown(
            source_type="support_request",
            source_obj=req,
            messages=[],
            llm_provider=None,
        )


@pytest.mark.asyncio
async def test_ticket_origin_resolved(db_session: Session) -> None:
    """Test generating a KB draft from a technician-resolved ticket."""
    conv = Conversation(title="Stampante Reparto Vendite", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Stampante HP Bloccata",
        description="Spooler di stampa in errore su Windows.",
        initial_category="hardware",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.ESCALATED.value,
        escalation_requested=True,
    )
    db_session.add(req)
    db_session.flush()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Stampante HP Bloccata",
        summary="Coda spooler bloccata con job corrotto.",
        symptoms="Errore 0x000006ba RPC server unavailable.",
        attempted_steps="Riavviato PC utente.",
        diagnostic_findings="Servizio Spooler arrestato sul server di stampa.",
        priority=TicketPriority.MEDIUM.value,
    )

    # Move to in_progress then resolved with technical notes
    LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.IN_PROGRESS.value, "tech_01")
    LocalTicketingAdapter.add_note(
        db=db_session,
        ticket_id=ticket.id,
        content="Riavviato print spooler da PowerShell: Restart-Service Spooler. Eliminati file .shd e .spl corrotti.",
        author="tech_01",
    )
    LocalTicketingAdapter.update_status(
        db_session,
        ticket.id,
        TicketStatus.RESOLVED.value,
        "tech_01",
        note="Stampa di prova completata con successo.",
    )
    db_session.refresh(ticket)

    md_content, title, cat, quality = await generate_kb_proposal_markdown(
        source_type="ticket",
        source_obj=ticket,
        messages=[],
        llm_provider=None,
    )

    assert "Stampante" in title
    fm, body = parse_markdown_content(md_content, source_path="test.md")
    assert fm.status == "draft"
    assert "Procedura di Risoluzione" in body
    assert "Restart-Service Spooler" in body


@pytest.mark.asyncio
async def test_ticket_origin_open_rejected(db_session: Session) -> None:
    """Test that open or in-progress tickets cannot generate KB proposals."""
    conv = Conversation(title="Ticket Aperto", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Problema Generico",
        description="Desc",
        initial_category="general",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.ESCALATED.value,
    )
    db_session.add(req)
    db_session.flush()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Problema Generico",
        summary="Summary",
        symptoms="Symptoms",
        attempted_steps="Steps",
        diagnostic_findings="Findings",
        priority=TicketPriority.LOW.value,
    )

    with pytest.raises(ValueError, match="stato 'resolved'/'closed'"):
        await generate_kb_proposal_markdown(
            source_type="ticket",
            source_obj=ticket,
            messages=[],
            llm_provider=None,
        )


@pytest.mark.asyncio
async def test_kb_generator_redacts_secrets(db_session: Session) -> None:
    """Test that any passwords or tokens in resolution notes are redacted in generated Markdown."""
    conv = Conversation(title="Reset Password DB", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="Configurazione DB",
        description="Accesso DB.",
        initial_category="software",
        status=RequestStatus.CLOSED.value,
        outcome=RequestOutcome.ESCALATED.value,
    )
    db_session.add(req)
    db_session.flush()

    ticket = LocalTicketingAdapter.create_ticket(
        db=db_session,
        support_request_id=req.id,
        conversation_id=conv.id,
        title="Accesso DB Oracle",
        summary="Configurazione tnsnames.ora",
        symptoms="ORA-12154",
        attempted_steps="Verificato ping",
        diagnostic_findings="Password scaduta su schema",
        priority=TicketPriority.MEDIUM.value,
    )
    LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.IN_PROGRESS.value, "tech")
    LocalTicketingAdapter.add_note(
        db=db_session,
        ticket_id=ticket.id,
        content="Impostata nuova password temporanea: password=SuperSecretPassw0rd! su schema admin.",
        author="tech",
    )
    LocalTicketingAdapter.update_status(db_session, ticket.id, TicketStatus.RESOLVED.value, "tech")
    db_session.refresh(ticket)

    md_content, _, _, _ = await generate_kb_proposal_markdown(
        source_type="ticket",
        source_obj=ticket,
        messages=[],
        llm_provider=None,
    )

    assert "SuperSecretPassw0rd!" not in md_content
    assert "[REDACTED_PASSWORD]" in md_content
