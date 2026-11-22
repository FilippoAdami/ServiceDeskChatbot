from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import Settings, get_settings
from backend.app.core.audit import record_audit_event
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import TechnicianChatMessage, Ticket, TicketStatus
from backend.app.llm import get_llm_provider
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import LLMGenerationConfig, LLMMessage
from backend.app.rag.service import KnowledgeRetrievalService, get_rag_service
from backend.app.ticketing.adapter import (
    VALID_TICKET_TRANSITIONS,
    LocalTicketingAdapter,
)

logger = logging.getLogger(__name__)


def build_tech_assistant_prompt(
    ticket: Ticket,
    kb_context: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Constructs the dedicated system prompt for the IT technician assistant."""
    incident_info = "Nessun incidente aziendale collegato."
    if ticket.incident:
        incident_info = (
            f"Incidente collegato: {ticket.incident.id} - {ticket.incident.service} "
            f"({ticket.incident.title}) | Stato: {ticket.incident.status}"
        )

    activities_summary = []
    for act in ticket.activities[-5:]:
        t_str = act.created_at.strftime("%H:%M:%S UTC")
        activities_summary.append(f"[{t_str}] {act.author} ({act.activity_type}): {act.content}")
    activities_str = "\n".join(activities_summary) if activities_summary else "Nessuna attività registrata."

    kb_str = "Nessuna fonte KB specifica."
    if kb_context:
        lines = []
        for doc in kb_context:
            doc_id = doc.get("doc_id", "KB-REF")
            heading = doc.get("heading", "")
            snippet = doc.get("content", "")[:300].strip()
            lines.append(f"[{doc_id} - {heading}]\n{snippet}")
        kb_str = "\n\n".join(lines)

    valid_targets = sorted(list(VALID_TICKET_TRANSITIONS.get(ticket.status, set())))

    prompt = f"""Sei l'Assistente AI Senior del Service Desk Tecnico IT. Il tuo ruolo è supportare
ESCLUSIVAMENTE il Tecnico IT nella diagnosi, risoluzione e documentazione dei ticket escalation.

=== CONTESTO DEL TICKET ATTUALE ===
- Ticket ID: {ticket.id}
- Titolo: {ticket.title}
- Stato Attuale: {ticket.status} (Transizioni valide consentite: {valid_targets})
- Priorità: {ticket.priority}
- Sintomi Rilevati: {ticket.symptoms}
- Verifiche Preliminari Tentate: {ticket.attempted_steps}
- Rilievi Diagnostici: {ticket.diagnostic_findings}
- Fonti KB Riferite: {ticket.source_refs or []}
- {incident_info}

=== CRONOLOGIA ATTIVITÀ / NOTE RECENTI ===
{activities_str}

=== DOCUMENTAZIONE KB CORRELATA ===
{kb_str}

=== REGOLE OPERATIVE FONDAMENTALI ===
1. Dialoghi con un collega tecnico IT: sii professionale, conciso e orientato alla causa radice.
2. Aiuta a interpretare errori di log, certificati, permessi Active Directory, VPN, ecc.
3. Se il tecnico descrive interventi effettuati o test con esito positivo
   (es. "ho verificato X, corretto Y e testato Z: ora funziona"), devi:
   a) Ringraziare e sintetizzare formalmente l'intervento tecnico eseguito.
   b) PROPORRE un aggiornamento strutturato del ticket includendo un blocco JSON alla fine.
4. Non puoi modificare direttamente il database né cambiare stato in autonomia.
   Qualsiasi proposta deve essere convalidata e confermata dal tecnico tramite l'interfaccia.
5. Se proponi un cambio di stato, scegli tra le transizioni consentite: {valid_targets}.
   Se il problema è risolto e lo stato attuale permette 'resolved', proponi 'resolved'.
6. Non includere mai credenziali reali (password, token) nelle note proposte.

=== FORMATO DELLA PROPOSTA STRUTTURATA (OPZIONALE) ===
Se il messaggio del tecnico giustifica un aggiornamento di stato o l'aggiunta di una nota riepilogativa,
includi alla fine della tua risposta ESATTAMENTE questo blocco JSON:
```json
{{
  "proposed_status": "resolved",
  "proposed_note": "Sintesi chiara dell'intervento tecnico eseguito per la chiusura...",
  "proposed_cause": "Causa radice identificata...",
  "proposed_solution": "Soluzione applicata..."
}}
```
Se il tecnico sta solo chiedendo informazioni o discutendo la diagnosi, NON inserire il blocco JSON.
"""
    return prompt.strip()


def extract_proposals(content: str, current_status: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Extracts and validates structured proposals from assistant response."""
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if not json_match:
        # Check without markdown block
        json_match = re.search(r"(\{\s*\"proposed_status\".*?\})", content, re.DOTALL)

    if not json_match:
        return content.strip(), None

    raw_json = json_match.group(1).strip()
    try:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            return content.strip(), None

        # Clean content removing the raw JSON code block for clean reading
        clean_content = content[: json_match.start()].strip()
        trailing = content[json_match.end() :].strip()
        if trailing:
            clean_content += f"\n\n{trailing}"

        proposals: Dict[str, Any] = {}
        proposed_status = data.get("proposed_status")
        valid_transitions = VALID_TICKET_TRANSITIONS.get(current_status, set())

        if proposed_status and isinstance(proposed_status, str):
            st_clean = proposed_status.strip().lower()
            if st_clean in valid_transitions:
                proposals["proposed_status"] = st_clean
            elif st_clean == current_status:
                proposals["proposed_status"] = None

        if "proposed_note" in data and isinstance(data["proposed_note"], str):
            proposals["proposed_note"] = redact_secrets(data["proposed_note"].strip())
        if "proposed_cause" in data and isinstance(data["proposed_cause"], str):
            proposals["proposed_cause"] = redact_secrets(data["proposed_cause"].strip())
        if "proposed_solution" in data and isinstance(data["proposed_solution"], str):
            proposals["proposed_solution"] = redact_secrets(data["proposed_solution"].strip())

        return clean_content.strip(), (proposals if proposals else None)
    except Exception as exc:
        logger.warning(f"Failed to parse technician assistant proposal JSON: {exc}")
        return content.strip(), None


class TechnicianAssistantService:
    """Coordinates contextual AI assistance for IT technicians working on tickets."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        rag_service: Optional[KnowledgeRetrievalService] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._llm = llm_provider
        self._rag = rag_service
        self._settings = settings or get_settings()

    @staticmethod
    def get_chat_history(db: Session, ticket_id: str) -> List[TechnicianChatMessage]:
        """Retrieves persistent chat messages between technician and assistant for a ticket."""
        LocalTicketingAdapter.get_ticket(db, ticket_id)
        return list(
            db.scalars(
                select(TechnicianChatMessage)
                .where(TechnicianChatMessage.ticket_id == ticket_id)
                .order_by(TechnicianChatMessage.created_at.asc())
            ).all()
        )

    async def handle_turn(
        self,
        db: Session,
        ticket_id: str,
        technician_message: str,
        author: str = "technician_demo",
    ) -> Tuple[TechnicianChatMessage, TechnicianChatMessage, Optional[Dict[str, Any]]]:
        """Retrieves ticket and executes an assistant conversational turn."""
        ticket = LocalTicketingAdapter.get_ticket(db, ticket_id)
        return await self.execute_turn(
            ticket=ticket,
            technician_content=technician_message,
            db=db,
            author=author,
        )

    async def execute_turn(
        self,
        ticket: Ticket,
        technician_content: str,
        db: Session,
        author: str = "technician_demo",
    ) -> Tuple[TechnicianChatMessage, TechnicianChatMessage, Optional[Dict[str, Any]]]:
        """Processes a technician message and generates a contextual assistant response."""
        sanitized_tech_content = redact_secrets(technician_content.strip())
        if not sanitized_tech_content:
            raise ValueError("Il messaggio del tecnico non può essere vuoto.")

        # 1. Persist technician message
        tech_msg = TechnicianChatMessage(
            ticket_id=ticket.id,
            sender="technician",
            content=sanitized_tech_content,
        )
        db.add(tech_msg)
        db.commit()
        db.refresh(tech_msg)

        record_audit_event(
            db=db,
            event_type="technician_message_sent",
            conversation_id=ticket.conversation_id,
            request_id=ticket.support_request_id,
            payload={
                "ticket_id": ticket.id,
                "message_id": tech_msg.id,
                "author": author,
                "content_length": len(sanitized_tech_content),
                "content": sanitized_tech_content,
            },
        )

        # 2. Retrieve optional KB context if technical question
        kb_context: List[Dict[str, Any]] = []
        if self._rag:
            try:
                # Query RAG for context
                rag_res = self._rag.search(
                    query=sanitized_tech_content,
                    top_k=2,
                )
                for item in rag_res:
                    if item.score >= 0.30:
                        kb_context.append({
                            "doc_id": item.doc_id,
                            "heading": item.heading,
                            "content": item.text,
                        })
            except Exception as rag_err:
                logger.warning(f"Technician assistant RAG retrieval skipped: {rag_err}")

        # 3. Build system prompt & message history
        system_prompt = build_tech_assistant_prompt(ticket=ticket, kb_context=kb_context)

        # Load recent tech chat messages (up to 10)
        recent_msgs = list(
            db.scalars(
                select(TechnicianChatMessage)
                .where(TechnicianChatMessage.ticket_id == ticket.id)
                .order_by(TechnicianChatMessage.created_at.asc())
            ).all()
        )[-10:]

        llm_messages: List[LLMMessage] = []
        for m in recent_msgs:
            role = "user" if m.sender == "technician" else "assistant"
            llm_messages.append(LLMMessage(role=role, content=m.content))

        # 4. Generate AI response
        proposals: Optional[Dict[str, Any]] = None
        assistant_content: str = ""
        llm_tokens: Optional[Dict[str, Any]] = None
        llm_latency_ms: Optional[int] = None
        llm_finish_reason: Optional[str] = None
        llm_is_truncated: bool = False

        if not self._llm.is_configured:
            # Deterministic fallback response when LLM not configured
            assistant_content = (
                "Assistente Tecnico (Modalità Offline): La chiamata LLM non è disponibile. "
                "Per questo ticket è possibile consultare i rilievi diagnostici e aggiornare manualmente "
                "lo stato o le note dal pannello operativo."
            )
            # Check for resolution heuristic in offline mode
            lower_msg = sanitized_tech_content.lower()
            if any(term in lower_msg for term in ["funziona", "risolto", "ripristinato", "test superato"]):
                if TicketStatus.RESOLVED.value in VALID_TICKET_TRANSITIONS.get(ticket.status, set()):
                    proposals = {
                        "proposed_status": TicketStatus.RESOLVED.value,
                        "proposed_note": f"Intervento tecnico completato: {sanitized_tech_content}",
                        "proposed_cause": "Verifica tecnica manuale completata con esito positivo.",
                        "proposed_solution": sanitized_tech_content,
                    }
        else:
            try:
                model_name = self._settings.GEMINI_DIAGNOSIS_MODEL or "gemini-2.5-flash"
                gen_config = LLMGenerationConfig(
                    temperature=0.2,
                    max_output_tokens=self._settings.GEMINI_MAX_OUTPUT_TOKENS,
                    thinking_level=self._settings.GEMINI_DIAGNOSIS_THINKING,
                )
                response = await self._llm.generate(
                    messages=llm_messages,
                    system_instruction=system_prompt,
                    config=gen_config,
                    model=model_name,
                )
                raw_content = response.content
                assistant_content, proposals = extract_proposals(raw_content, ticket.status)
                llm_tokens = response.token_usage.model_dump()
                llm_latency_ms = int(response.latency_ms)
                llm_finish_reason = response.finish_reason
                llm_is_truncated = (
                    response.finish_reason == "MAX_TOKENS"
                    or response.metadata.get("is_truncated", False)
                )
            except Exception as llm_err:
                logger.error(f"Error calling LLM for technician assistant: {llm_err}")
                assistant_content = (
                    "Si è verificato un errore temporaneo nella generazione della risposta dell'assistente tecnico. "
                    "I dati del ticket rimangono inalterati ed è possibile procedere con le operazioni manuali."
                )

        # 5. Persist assistant message
        asst_msg = TechnicianChatMessage(
            ticket_id=ticket.id,
            sender="assistant",
            content=redact_secrets(assistant_content),
            proposals_json=proposals,
        )
        db.add(asst_msg)
        db.commit()
        db.refresh(asst_msg)

        record_audit_event(
            db=db,
            event_type="technician_assistant_responded",
            conversation_id=ticket.conversation_id,
            request_id=ticket.support_request_id,
            payload={
                "ticket_id": ticket.id,
                "message_id": asst_msg.id,
                "has_proposals": proposals is not None,
                "proposed_status": proposals.get("proposed_status") if proposals else None,
                "content": redact_secrets(assistant_content),
                "tokens": llm_tokens,
                "latency_ms": llm_latency_ms,
                "finish_reason": llm_finish_reason,
                "is_truncated": llm_is_truncated,
            },
        )

        return tech_msg, asst_msg, proposals


# Singleton provider for FastAPI dependency injection
_tech_assistant_service_instance: Optional[TechnicianAssistantService] = None


def get_tech_assistant_service(
    llm: BaseLLMProvider = Depends(get_llm_provider),
    rag: KnowledgeRetrievalService = Depends(get_rag_service),
) -> TechnicianAssistantService:
    """Dependency provider for TechnicianAssistantService."""
    global _tech_assistant_service_instance
    if _tech_assistant_service_instance is None:
        _tech_assistant_service_instance = TechnicianAssistantService(
            llm_provider=llm,
            rag_service=rag,
        )
    return _tech_assistant_service_instance


def reset_tech_assistant_for_test(
    service: Optional[TechnicianAssistantService] = None,
) -> None:
    """Helper to inject custom technician assistant service in tests."""
    global _tech_assistant_service_instance
    _tech_assistant_service_instance = service
