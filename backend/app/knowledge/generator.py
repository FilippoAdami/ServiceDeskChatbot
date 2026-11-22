from __future__ import annotations

import datetime
import logging
import re
from typing import Any, List, Optional, Tuple

from backend.app.config import get_settings
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import (
    Message,
    MessageRole,
    ProposalSourceType,
    RequestOutcome,
    SupportRequest,
    Ticket,
    TicketStatus,
)
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import LLMGenerationConfig, LLMMessage
from backend.app.rag.parser import parse_markdown_content

logger = logging.getLogger(__name__)


def generate_doc_id(category: str, source_id: str) -> str:
    """Generates a standardized KB Document ID (e.g. KB-NET-A1B2)."""
    prefix_map = {
        "network": "NET",
        "net": "NET",
        "account": "AUTH",
        "auth": "AUTH",
        "software": "APP",
        "hardware": "HW",
        "hw": "HW",
        "ops": "OPS",
        "email": "MAIL",
        "mail": "MAIL",
        "file": "FILE",
    }
    cat_prefix = prefix_map.get(category.lower(), "GEN")
    clean_id = re.sub(r"[^A-Za-z0-9]", "", source_id)[-4:].upper()
    if not clean_id or len(clean_id) < 2:
        clean_id = "001"
    return f"KB-{cat_prefix}-{clean_id}"


def generate_fallback_markdown(
    doc_id: str,
    title: str,
    category: str,
    symptoms: str,
    resolution_steps: str,
    cause: str,
    author: str = "Service Desk AI & Human Review",
) -> str:
    """Produces compliant Markdown with valid YAML front matter deterministically."""
    clean_title = redact_secrets(title).strip().replace('"', "'")
    today_str = datetime.date.today().isoformat()
    clean_symptoms = redact_secrets(symptoms).strip()
    clean_steps = redact_secrets(resolution_steps).strip()
    clean_cause = redact_secrets(cause).strip()

    markdown = f"""---
id: {doc_id}
title: "{clean_title}"
category: {category}
tags:
  - {category}
  - troubleshooting
  - procedura
status: draft
version: "1.0"
last_updated: "{today_str}"
author: "{author}"
summary: "Procedura operativa per la risoluzione di: {clean_title}"
---

# {clean_title}

## Descrizione e Sintomi Rilevati
{clean_symptoms}

## Cause Comuni Identificate
{clean_cause}

## Procedura di Risoluzione
{clean_steps}

## Verifiche di Ripristino
1. Verificare l'accesso e la corretta operatività del servizio interessato.
2. Controllare l'assenza di errori nei registri di sistema o nel client locale.
3. Se l'utente riscontra ancora anomalie, effettuare un nuovo riavvio e verificare la connettività.

## Quando Escalare al Supporto Specialistico
Se dopo aver completato tutti i passaggi sopra indicati l'anomalia persiste,
escalare al supporto di secondo livello allegando i log di diagnostica.
"""
    return markdown.strip()


async def generate_kb_proposal_markdown(
    source_type: str,
    source_obj: Any,
    messages: Optional[List[Message]] = None,
    llm_provider: Optional[BaseLLMProvider] = None,
) -> Tuple[str, str, str, str]:
    """Generates compliant Markdown, title, category, and summary_quality for a KnowledgeProposal.

    Returns:
        (content_markdown, title, category, summary_quality)
    """
    settings = get_settings()

    if source_type == ProposalSourceType.SUPPORT_REQUEST.value:
        req: SupportRequest = source_obj
        if req.outcome != RequestOutcome.RESOLVED_CONFIRMED.value:
            raise ValueError(
                f"Impossibile generare proposta da richiesta non confermata risolta (stato: {req.outcome})."
            )

        title = req.title or "Procedura di Risoluzione Richiesta IT"
        category = (req.final_category or req.initial_category or "general").lower()
        doc_id = generate_doc_id(category, req.id)

        user_msgs = [m.content for m in (messages or []) if m.role == MessageRole.USER.value]
        asst_msgs = [m.content for m in (messages or []) if m.role == MessageRole.ASSISTANT.value]

        symptoms = "\n".join(f"- {m}" for m in user_msgs) if user_msgs else req.description
        resolution_steps = (
            "\n".join(f"{idx+1}. {m}" for idx, m in enumerate(asst_msgs))
            if asst_msgs
            else "Procedura completata con successo tramite indicazioni dell'assistente."
        )
        cause = "Configurazione locale o credenziali non sincronizzate."

    elif source_type == ProposalSourceType.TICKET.value:
        ticket: Ticket = source_obj
        if ticket.status not in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
            # Also allow if there are confirmed technician notes
            has_notes = any(a.activity_type == "note" for a in (ticket.activities or []))
            if not has_notes:
                raise ValueError(
                    "Il ticket deve essere in stato 'resolved'/'closed' o avere note tecniche documentate."
                )

        title = ticket.title or "Procedura di Risoluzione Tecnica"
        category = "general"
        if ticket.source_refs:
            for ref in ticket.source_refs:
                if "AUTH" in ref or "MAIL" in ref or "NET" in ref or "FILE" in ref or "APP" in ref:
                    if "AUTH" in ref:
                        category = "account"
                    elif "MAIL" in ref:
                        category = "email"
                    elif "NET" in ref:
                        category = "network"
                    elif "FILE" in ref:
                        category = "file"
                    elif "APP" in ref:
                        category = "software"
                    break

        doc_id = generate_doc_id(category, ticket.id)
        symptoms = ticket.symptoms or ticket.summary
        notes = [a.content for a in (ticket.activities or []) if a.activity_type == "note"]
        resolution_steps = (
            "\n".join(f"- {note}" for note in notes)
            if notes
            else ticket.attempted_steps or "Intervento tecnico completato e verificato."
        )
        cause = ticket.diagnostic_findings or "Anomalia risolta tramite intervento tecnico specialistico."
    else:
        raise ValueError(f"source_type '{source_type}' non supportato.")

    # Try LLM generation if available
    if llm_provider and llm_provider.is_configured:
        prompt = f"""Genera una bozza di articolo per la Knowledge Base IT aziendale in formato Markdown.
Il documento deve descrivere una procedura tecnica GENERALIZZATA basata sui fatti documentati di seguito,
senza includere dati personali (nomi di utenti, ID ticket specifici o password).

=== DATI DELLA RISOLUZIONE ===
- Titolo Problema: {title}
- Categoria Suggerita: {category}
- Document ID Assegnato: {doc_id}
- Sintomi Riscontrati: {symptoms}
- Causa Diagnosticata: {cause}
- Passaggi Risolutivi Eseguiti: {resolution_steps}

=== REQUISITI DI FORMATO INDISPENSABILI ===
Devi iniziare TASSATIVAMENTE con il Front Matter YAML racchiuso tra tripli trattini:
---
id: {doc_id}
title: "{title}"
category: {category}
tags:
  - {category}
  - troubleshooting
status: draft
version: "1.0"
last_updated: "{datetime.date.today().isoformat()}"
author: "Service Desk AI & Human Review"
summary: "Riepilogo conciso della guida..."
---

Subito dopo il Front Matter, inserisci il corpo in Markdown strutturato con queste sezioni:
# {title}
## Descrizione e Sintomi Rilevati
## Cause Comuni Identificate
## Procedura di Risoluzione
## Verifiche di Ripristino
## Quando Escalare al Supporto Specialistico

Rispondi SOLO con il Markdown completo, senza racchiuderlo in ulteriori blocchi di codice.
"""
        try:
            model_name = settings.GEMINI_FINALIZATION_MODEL or "gemini-2.5-flash"
            gen_config = LLMGenerationConfig(
                temperature=0.2,
                max_output_tokens=1500,
            )
            res = await llm_provider.generate(
                messages=[LLMMessage(role="user", content=prompt)],
                config=gen_config,
                model=model_name,
            )
            raw_text = res.content.strip()
            # Clean possible markdown wrapping
            if raw_text.startswith("```markdown"):
                raw_text = raw_text[len("```markdown") :].strip()
            elif raw_text.startswith("```md"):
                raw_text = raw_text[len("```md") :].strip()
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

            # Validate that generated markdown has valid front matter
            fm, body = parse_markdown_content(raw_text, source_path=f"{doc_id}.md")
            if fm.id and fm.title and fm.category:
                cleaned_markdown = redact_secrets(raw_text)
                return cleaned_markdown, fm.title, fm.category, "llm"
        except Exception as llm_err:
            logger.warning(f"KB proposal LLM generation failed ({llm_err}); using fallback template.")

    # Fallback template
    fallback_md = generate_fallback_markdown(
        doc_id=doc_id,
        title=title,
        category=category,
        symptoms=symptoms,
        resolution_steps=resolution_steps,
        cause=cause,
    )
    return fallback_md, title, category, "fallback"
