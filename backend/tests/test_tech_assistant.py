from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.app.agent.tech_assistant import (
    TechnicianAssistantService,
    build_tech_assistant_prompt,
    extract_proposals,
)
from backend.app.db.models import (
    Conversation,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
    Ticket,
    TicketPriority,
    TicketStatus,
)
from backend.app.llm.mock import MockLLMProvider
from backend.app.ticketing.adapter import LocalTicketingAdapter


@pytest.fixture
def sample_ticket(db_session: Session) -> Ticket:
    """Fixture to create a sample ticket linked to conversation and support request."""
    conv = Conversation(title="Problema VPN Tecnico", user_id="user_test_01")
    db_session.add(conv)
    db_session.flush()

    req = SupportRequest(
        conversation_id=conv.id,
        title="VPN Fallita su Linux",
        description="Impossibile connettersi al gateway aziendale.",
        initial_category="network",
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
        title="VPN Fallita su Linux",
        summary="Errore TLS durante handshake su gateway VPN.",
        symptoms="Timeout su porta 443 gateway-vpn.corp.local",
        attempted_steps="Verificato certificato locale, riavviato servizio openvpn.",
        diagnostic_findings="Certificato client scaduto il 20/11.",
        source_refs=["KB-NET-001"],
        priority=TicketPriority.HIGH.value,
    )
    return ticket


def test_build_tech_assistant_prompt(db_session: Session, sample_ticket: Ticket) -> None:
    """Test that system prompt includes ticket context, diagnostics, transitions, and activities."""
    prompt = build_tech_assistant_prompt(ticket=sample_ticket)
    assert sample_ticket.id in prompt
    assert "VPN Fallita su Linux" in prompt
    assert "open" in prompt
    assert "in_progress" in prompt
    assert "Timeout su porta 443" in prompt
    assert "Certificato client scaduto" in prompt
    assert "Nessun incidente aziendale collegato" in prompt

    from backend.app.db.models import Incident, IncidentStatus

    incident = Incident(
        id="INC-VPN-001",
        service="VPN",
        title="Disservizio Gateway VPN Milano",
        symptoms="Timeout TLS",
        summary="Gateway sovraccarico.",
        status=IncidentStatus.INVESTIGATING.value,
    )
    db_session.add(incident)
    db_session.flush()

    LocalTicketingAdapter.link_incident(
        db=db_session,
        ticket_id=sample_ticket.id,
        incident_id=incident.id,
        author="technician_01",
    )
    db_session.refresh(sample_ticket)

    prompt_with_incident = build_tech_assistant_prompt(ticket=sample_ticket)
    assert incident.id in prompt_with_incident
    assert "Disservizio Gateway VPN Milano" in prompt_with_incident


def test_extract_proposals_valid_json() -> None:
    """Test proposal extraction from LLM response containing valid JSON block."""
    llm_output = """Ho analizzato il problema del certificato.
```json
{
  "proposed_status": "in_progress",
  "proposed_note": "Rigenerato certificato client su CA interna. In attesa di test.",
  "proposed_cause": "Certificato x509 scaduto.",
  "proposed_solution": "Emissione nuovo bundle di chiavi utente."
}
```
Puoi procedere con il test ora."""

    clean_text, proposals = extract_proposals(llm_output, current_status="open")
    assert "Ho analizzato il problema" in clean_text
    assert proposals is not None
    assert proposals["proposed_status"] == "in_progress"
    assert "Rigenerato certificato" in proposals["proposed_note"]
    assert proposals["proposed_cause"] == "Certificato x509 scaduto."


def test_extract_proposals_invalid_status_transition() -> None:
    """Test that proposed_status is rejected if transition is invalid according to state machine."""
    # From "open", direct jump to "resolved" is NOT allowed
    llm_output = """Operazione conclusa.
```json
{
  "proposed_status": "resolved",
  "proposed_note": "Risoluzione anticipata non consentita."
}
```"""
    clean_text, proposals = extract_proposals(llm_output, current_status="open")
    assert proposals is not None
    assert "proposed_status" not in proposals  # rejected because invalid transition from open to resolved
    assert proposals.get("proposed_note") == "Risoluzione anticipata non consentita."


def test_extract_proposals_malformed_json_fallback() -> None:
    """Test that malformed JSON does not crash and returns full content without proposals."""
    llm_output = "Ecco la proposta:\n```json\n{ not valid json }\n```"
    clean_text, proposals = extract_proposals(llm_output, current_status="open")
    assert proposals is None
    assert "Ecco la proposta" in clean_text


@pytest.mark.asyncio
async def test_tech_assistant_turn_offline_heuristic(db_session: Session, sample_ticket: Ticket) -> None:
    """Test tech assistant turn in offline mode (LLM unconfigured) with heuristic proposal."""
    # Move ticket to in_progress so resolved is a valid transition
    LocalTicketingAdapter.update_status(
        db=db_session,
        ticket_id=sample_ticket.id,
        new_status=TicketStatus.IN_PROGRESS.value,
        author="technician_01",
    )

    mock_provider = MockLLMProvider(is_configured=False)

    service = TechnicianAssistantService(llm_provider=mock_provider)

    tech_msg, asst_msg, proposals = await service.handle_turn(
        db=db_session,
        ticket_id=sample_ticket.id,
        technician_message="Ho rigenerato il certificato e ora la connessione VPN funziona perfettamente!",
        author="technician_01",
    )

    assert tech_msg.sender == "technician"
    assert "VPN funziona" in tech_msg.content
    assert asst_msg.sender == "assistant"
    assert "Modalità Offline" in asst_msg.content

    # In offline mode, heuristic detects resolution keyword
    assert proposals is not None
    assert proposals.get("proposed_status") == TicketStatus.RESOLVED.value

    # Check persistence and separation from employee chat
    history = service.get_chat_history(db=db_session, ticket_id=sample_ticket.id)
    assert len(history) == 2
    assert history[0].id == tech_msg.id
    assert history[1].id == asst_msg.id


@pytest.mark.asyncio
async def test_tech_assistant_turn_redacts_secrets(db_session: Session, sample_ticket: Ticket) -> None:
    """Test that technician messages containing passwords/tokens are redacted."""
    mock_provider = MockLLMProvider(is_configured=False)

    service = TechnicianAssistantService(llm_provider=mock_provider)

    tech_msg, asst_msg, _ = await service.handle_turn(
        db=db_session,
        ticket_id=sample_ticket.id,
        technician_message="Ho testato l'utenza con password=SecretPassw0rd! e Bearer eyJhbGciOiJIUzI1NiJ9.test",
        author="technician_01",
    )

    assert "SecretPassw0rd!" not in tech_msg.content
    assert "[REDACTED_PASSWORD]" in tech_msg.content
    assert "eyJhbGciOiJIUzI1NiJ9" not in tech_msg.content
    assert "[REDACTED_TOKEN]" in tech_msg.content
