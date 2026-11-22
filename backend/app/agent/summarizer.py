from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.config import get_settings
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import Message, MessageRole, SupportRequest
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import LLMGenerationConfig, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class TicketSummaryData:
    """Structured diagnostic summary for ticket escalation."""

    title: str
    summary: str
    symptoms: str
    attempted_steps: str
    diagnostic_findings: str
    source_refs: List[str] = field(default_factory=list)
    summary_quality: str = "fallback"  # 'llm' or 'fallback'


def _extract_sources(messages: List[Message], explicit_sources: Optional[List[str]] = None) -> List[str]:
    """Collect unique KB document IDs referenced across conversation history."""
    sources: List[str] = []
    seen = set()

    if explicit_sources:
        for s in explicit_sources:
            if s and s not in seen:
                seen.add(s)
                sources.append(s)

    for m in messages:
        if m.metadata_json and isinstance(m.metadata_json, dict):
            raw_sources = m.metadata_json.get("sources")
            if isinstance(raw_sources, list):
                for item in raw_sources:
                    if isinstance(item, dict) and "doc_id" in item:
                        doc_id = item["doc_id"]
                        if doc_id and doc_id not in seen:
                            seen.add(doc_id)
                            sources.append(doc_id)
                    elif isinstance(item, str) and item not in seen:
                        seen.add(item)
                        sources.append(item)

    return sources


def _deterministic_fallback_summary(
    support_request: SupportRequest,
    messages: List[Message],
    source_refs: List[str],
) -> TicketSummaryData:
    """Generate a reliable, factual fallback summary without calling external LLM."""
    user_msgs = [m.content.strip() for m in messages if m.role == MessageRole.USER.value]
    assistant_msgs = [m.content.strip() for m in messages if m.role == MessageRole.ASSISTANT.value]

    title = support_request.title or (user_msgs[0][:80] if user_msgs else "Richiesta assistenza tecnica")
    symptoms = (
        "\n".join(f"- {msg}" for msg in user_msgs)
        if user_msgs
        else "Nessun sintomo dettagliato specificato dall'utente."
    )

    if assistant_msgs:
        attempted_steps = (
            "Fornite istruzioni preliminari di verifica e risoluzione da parte dell'assistente virtuale. "
            "L'utente ha comunicato esito negativo o ha richiesto l'intervento di un operatore."
        )
    else:
        attempted_steps = "Nessuna verifica preliminare completata prima della richiesta di escalation."

    diagnostic_findings = (
        "Problematica non risolta in autonomia dal dipendente; "
        "necessaria presa in carico e diagnosi da parte del supporto tecnico di secondo livello."
    )

    summary = (
        f"Ticket aperto a seguito di escalation per: {title}. "
        "Dettagli diagnostici estratti in modalità deterministica di fallback."
    )

    return TicketSummaryData(
        title=redact_secrets(title)[:255],
        summary=redact_secrets(summary),
        symptoms=redact_secrets(symptoms),
        attempted_steps=redact_secrets(attempted_steps),
        diagnostic_findings=redact_secrets(diagnostic_findings),
        source_refs=source_refs,
        summary_quality="fallback",
    )


async def generate_ticket_summary(
    support_request: SupportRequest,
    messages: List[Message],
    llm_provider: Optional[BaseLLMProvider] = None,
    explicit_sources: Optional[List[str]] = None,
) -> TicketSummaryData:
    """Produce a structured diagnostic summary for technician ticketing.

    Attempts structured LLM generation with fallback to deterministic extraction.
    """
    source_refs = _extract_sources(messages, explicit_sources)

    # If LLM is not provided, return deterministic fallback immediately
    if not llm_provider:
        return _deterministic_fallback_summary(support_request, messages, source_refs)

    settings = get_settings()

    # Build prompt for diagnostic summarization
    system_instruction = (
        "Sei il modulo diagnostico di backend del Service Desk aziendale. "
        "Il tuo compito è generare un riepilogo tecnico rigoroso e attendibile per il ticket "
        "destinato ai tecnici informatici.\n\n"
        "REGOLE ASSOLUTE:\n"
        "1. Estrai SOLO informazioni realmente presenti nei messaggi della conversazione.\n"
        "2. Se un dato non è stato fornito o non è noto, riporta esplicitamente 'Non noto' o 'Non specificato'. "
        "NON inventare diagnosi, configurazioni di rete o verifiche non avvenute.\n"
        "3. Distingui con chiarezza: problema riportato, verifiche effettivamente provate, esito e incertezze.\n"
        "4. Non includere MAI password, token, credenziali o dati sensibili.\n"
        "5. Rispondi ESCLUSIVAMENTE con un oggetto JSON valido con le seguenti chiavi stringa:\n"
        "   - 'title': titolo breve del problema (massimo 80 caratteri)\n"
        "   - 'summary': sintesi chiara del disservizio (2-3 frasi)\n"
        "   - 'symptoms': sintomi e messaggi di errore riscontrati dall'utente\n"
        "   - 'attempted_steps': passaggi di risoluzione effettivamente tentati in chat\n"
        "   - 'diagnostic_findings': rilievi diagnostici emersi e motivi dell'escalation\n"
    )

    history_text = "\n".join(
        f"[{m.role.upper()}]: {m.content}" for m in messages[-settings.AGENT_CONTEXT_WINDOW_TURNS :]
    )

    user_prompt = (
        f"Genera il riepilogo JSON per il seguente storico conversazione:\n\n"
        f"{history_text}\n\n"
        f"Fonti KB consultate durante il dialogo: {', '.join(source_refs) if source_refs else 'Nessuna'}"
    )

    try:
        gen_config = LLMGenerationConfig(
            temperature=0.1,  # Low temperature for factual extraction
            max_output_tokens=800,
        )

        response = await llm_provider.generate(
            messages=[LLMMessage(role=MessageRole.USER.value, content=user_prompt)],
            system_instruction=system_instruction,
            config=gen_config,
            model=settings.GEMINI_FINALIZATION_MODEL,
        )

        content = response.content.strip()

        # Extract JSON from potential markdown fencing
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        raw_json = json_match.group(1) if json_match else content

        parsed: Dict[str, Any] = json.loads(raw_json)

        title = str(parsed.get("title", support_request.title or "Assistenza Tecnica")).strip()
        summary = str(parsed.get("summary", "")).strip()
        symptoms = str(parsed.get("symptoms", "")).strip()
        attempted = str(parsed.get("attempted_steps", "")).strip()
        findings = str(parsed.get("diagnostic_findings", "")).strip()

        if not (summary and symptoms):
            logger.warning("LLM summary output missing required fields, using fallback")
            return _deterministic_fallback_summary(support_request, messages, source_refs)

        return TicketSummaryData(
            title=redact_secrets(title)[:255],
            summary=redact_secrets(summary),
            symptoms=redact_secrets(symptoms),
            attempted_steps=redact_secrets(attempted),
            diagnostic_findings=redact_secrets(findings),
            source_refs=source_refs,
            summary_quality="llm",
        )

    except Exception as exc:
        logger.warning("Structured LLM ticket summarization failed (%s), using fallback", exc)
        return _deterministic_fallback_summary(support_request, messages, source_refs)
