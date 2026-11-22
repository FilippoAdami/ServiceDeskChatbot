from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent.prompts import build_system_prompt
from backend.app.agent.summarizer import generate_ticket_summary
from backend.app.agent.tools import CREATE_TICKET_TOOL
from backend.app.config import get_settings
from backend.app.core.audit import record_audit_event
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import (
    AgentPhase,
    Conversation,
    Incident,
    IncidentStatus,
    Message,
    MessageRole,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
    Ticket,
    TicketStatus,
)
from backend.app.knowledge.categories import normalize_task_category
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import LLMGenerationConfig, LLMMessage
from backend.app.rag.models import SearchResultItem
from backend.app.rag.service import KnowledgeRetrievalService
from backend.app.schemas.message import MessageResponse
from backend.app.ticketing.adapter import LocalTicketingAdapter

logger = logging.getLogger(__name__)

# Patterns for intent recognition
HUMAN_ESCALATION_PATTERN = re.compile(
    r"(?i)\b("
    r"parla(?:re)?(?:\s+\w+)?\s+con\s+(?:un\s+)?(?:tecnico|operatore|persona|umano)|"
    r"contatta(?:re)?(?:\s+\w+)?\s+(?:un\s+)?(?:tecnico|operatore)|"
    r"passa(?:mi)?(?:\s+\w+)?\s+(?:un\s+)?(?:tecnico|operatore)|"
    r"(?:ho|abbiamo)\s+bisogno\s+di\s+(?:un\s+)?(?:tecnico|operatore|intervento|assistenza)|"
    r"(?:mi|ci)\s+serve\s+(?:un\s+)?(?:tecnico|operatore|intervento|assistenza)|"
    r"serve\s+(?:un\s+)?(?:tecnico|operatore|intervento|assistenza)|"
    r"voglio\s+(?:un\s+)?(?:tecnico|operatore)|"
    r"vorrei\s+(?:un\s+)?(?:tecnico|operatore)|"
    r"chiedo\s+(?:un\s+)?(?:tecnico|operatore)|"
    r"apri(?:re)?\s+(?:un\s+|la\s+|una\s+)?(?:ticket|segnalazione)|"
    r"inoltra(?:re)?\s+(?:un\s+|la\s+|una\s+)?(?:ticket|segnalazione)|"
    r"crea(?:re)?\s+(?:un\s+|la\s+|una\s+)?(?:ticket|segnalazione)|"
    r"tecnico\s+umano|operatore\s+umano|operatore|persona\s+reale|assistenza\s+umana|"
    r"intervento\s+(?:di\s+un\s+)?tecnico|supporto\s+specialistico|supporto\s+umano|secondo\s+livello"
    r")\b"
)
BOT_PROPOSED_ESCALATION_PATTERN = re.compile(
    r"(?i)\b("
    r"inoltra(?:re)?\s+(?:una|la)?\s*segnalazione|"
    r"contatta(?:re)?\s+(?:i|il|un)?\s*tecnic[oi]|"
    r"supporto\s+tecnico\s+specialistico|"
    r"operatore\s+ti\s+prenda\s+in\s+carico|"
    r"apri(?:re)?\s+un\s+ticket|"
    r"rivolgerti\s+direttamente\s+al\s+supporto"
    r")\b"
)
USER_AFFIRMATION_PATTERN = re.compile(
    r"(?i)\b("
    r"s[iì]|certo|volentieri|grazie|procedi|d'accordo|ok|perfetto|confermo|"
    r"inoltra|apri|fallo|fai\s+pure|vai\s+pure"
    r")\b"
)
RESOLUTION_CONFIRM_PATTERN = re.compile(
    r"(?i)\b("
    r"ha funzionato|risolto|ora funziona|ora va|tutto a posto|"
    r"grazie mille ha funzionato|funziona correttamente|"
    r"sono riuscit[oa]|riuscito ad accedere|riuscita ad accedere|"
    r"resettat[oa]|resettarla|password reimpostata|accesso riuscito|"
    r"tutto risolto|ho risolto|problema risolto|tutto ok|perfetto grazie|"
    r"risolto grazie|grazie ho risolto|grazie mille ho risolto"
    r")\b"
)
FAILURE_PATTERN = re.compile(r"(?i)\b(non funziona|non va|ancora errore|stesso errore|non ha funzionato|fallito)\b")
OUT_OF_SCOPE_PATTERN = re.compile(
    r"(?i)\b("
    r"ricett[ae]|tiramis[uù]|cucina(?:re)?|ingredient[ie]|pranz[io]|cen[ae]|colazione|dolc[ie]|torta|pasta|pizza|"
    r"barzellett[ae]|poesi[ae]|raccontami (?:una )?(?:storia|favola)|filastrocc[ae]|canzon[ie]|oroscopo|astrologi[ae]|"
    r"meteo|previsioni (?:del )?tempo|che tempo fa|temperatura esterna|"
    r"calcio|partit[ae]|campionato|serie a|champions|classifica sportiv[ae]|risultat[io] sportiv[io]|"
    r"giorni di ferie|prenotare ferie|richiesta ferie|busta paga|cedolino|stipendio|rimborso spese|maternità"
    r")\b"
)
GREETING_PATTERN = re.compile(r"(?i)^(?:ciao|buongiorno|buonasera|salve|ehi|hello|hi|hey|grazie|ok|perfetto)[.!?\s]*$")
RESOLUTION_PROMPT_PHRASE_PATTERN = re.compile(
    r"(?i)\b("
    r"la problematica è da considerarsi completamente risolta|"
    r"ti chiedo conferma:?\s*la problematica|"
    r"confermi che (?:la problematica|il problema)|"
    r"problematica sia stata risolta"
    r")\b"
)


@dataclass
class AssistantTurnResult:
    """Structured result of an assistant conversational turn."""

    message: MessageResponse
    sources: List[Dict[str, Any]] = field(default_factory=list)
    phase: str = "triage"
    escalation_requested: bool = False
    resolution_proposed: bool = False
    request_id: Optional[str] = None
    ticket_id: Optional[str] = None
    ticket_status: Optional[str] = None
    tokens: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    is_truncated: bool = False




class ConversationalAgentOrchestrator:
    """Orchestrates multi-phase conversation, RAG grounding, state transitions, and concurrency locks."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        rag_service: KnowledgeRetrievalService,
    ) -> None:
        self._llm = llm_provider
        self._rag = rag_service
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, conversation_id: str) -> asyncio.Lock:
        if conversation_id not in self._locks:
            self._locks[conversation_id] = asyncio.Lock()
        return self._locks[conversation_id]

    async def execute_turn(
        self,
        conversation_id: str,
        db: Session,
    ) -> AssistantTurnResult:
        """Execute a single assistant turn with concurrency control, state tracking, and persistence."""
        lock = self._get_lock(conversation_id)

        # Check concurrency lock: reject concurrent requests on same thread with 409 Conflict
        if lock.locked():
            logger.warning("Concurrent turn rejected for conversation %s", conversation_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Un turno dell'assistente è già in elaborazione per questa conversazione. "
                    "Attendere il completamento."
                ),
            )

        async with lock:
            # 1. Fetch conversation and history from DB
            conv = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
            if not conv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversazione {conversation_id} non trovata",
                )

            # Check for messages
            messages_query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc(), Message.id.asc())
            )
            all_messages = list(db.scalars(messages_query).all())

            if not all_messages:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nessun messaggio presente nella conversazione per avviare il turno dell'assistente",
                )

            # Ensure the last message is from the user
            last_msg = all_messages[-1]
            if last_msg.role != MessageRole.USER.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "L'ultimo messaggio non è dell'utente. "
                        "Inviare un messaggio prima di richiedere un turno assistente."
                    ),
                )

            last_user_text = last_msg.content.strip()

            # 2. Retrieve or create active SupportRequest
            req_query = (
                select(SupportRequest)
                .where(SupportRequest.conversation_id == conversation_id)
                .order_by(SupportRequest.created_at.desc())
            )
            support_req = db.scalar(req_query)

            if not support_req:
                # Initialize a SupportRequest for this issue
                clean_title = last_user_text.split("\n")[0].strip()
                if len(clean_title) > 60:
                    clean_title = clean_title[:57] + "..."
                initial_title = clean_title or "Richiesta IT"
                support_req = SupportRequest(
                    conversation_id=conversation_id,
                    title=initial_title,
                    description=last_user_text,
                    status=RequestStatus.OPEN.value,
                    phase=AgentPhase.TRIAGE.value,
                    escalation_requested=False,
                )
                db.add(support_req)
                db.flush()

            # Update generic conversation title with meaningful topic
            if not conv.title or conv.title.strip() in ["", "Nuova Richiesta IT", "Nuova Chat", "Richiesta IT"]:
                clean_title = last_user_text.split("\n")[0].strip()
                if len(clean_title) > 55:
                    clean_title = clean_title[:52] + "..."
                conv.title = clean_title

            # 3. Intent Detection: Human Technician Escalation, Resolution, Out-of-scope, Greeting
            is_escalation = bool(HUMAN_ESCALATION_PATTERN.search(last_user_text))
            is_resolution = bool(RESOLUTION_CONFIRM_PATTERN.search(last_user_text))
            is_failure = bool(FAILURE_PATTERN.search(last_user_text))
            is_out_of_scope = bool(OUT_OF_SCOPE_PATTERN.search(last_user_text))
            is_greeting = bool(GREETING_PATTERN.search(last_user_text))

            # Contextual escalation: if previous bot turn offered escalation and user affirmed
            if not is_escalation and not is_resolution and len(all_messages) >= 2:
                prior_assistant_msg = all_messages[-2]
                if prior_assistant_msg.role == MessageRole.ASSISTANT.value:
                    if (
                        BOT_PROPOSED_ESCALATION_PATTERN.search(prior_assistant_msg.content)
                        and USER_AFFIRMATION_PATTERN.search(last_user_text)
                    ):
                        is_escalation = True
                        logger.info(
                            "Contextual escalation triggered from previous bot proposal and user affirmation "
                            "in conversation %s",
                            conversation_id,
                        )

            if is_escalation:
                support_req.escalation_requested = True
                support_req.outcome = RequestOutcome.ESCALATED.value
                logger.info("Human technician escalation requested for conversation %s", conversation_id)

            # 4. State Machine Phase Determination
            current_phase = support_req.phase or AgentPhase.TRIAGE.value

            if is_escalation:
                current_phase = AgentPhase.FINALIZATION.value
            elif is_resolution:
                current_phase = AgentPhase.FINALIZATION.value
                support_req.outcome = RequestOutcome.RESOLVED_CONFIRMED.value
            elif is_out_of_scope:
                # Keep in triage; do not proceed to diagnostic troubleshooting for non-IT queries
                current_phase = AgentPhase.TRIAGE.value
            elif is_failure and current_phase == AgentPhase.DIAGNOSIS.value:
                # Stay in diagnosis or offer alternative troubleshooting
                current_phase = AgentPhase.DIAGNOSIS.value
            elif current_phase == AgentPhase.TRIAGE.value and len(all_messages) >= 2 and not is_greeting:
                # After initial triage clarification, proceed to diagnosis
                current_phase = AgentPhase.DIAGNOSIS.value
            elif current_phase == AgentPhase.FINALIZATION.value and not is_resolution:
                # If user brings up new problem or clarifies in finalization, return to diagnosis
                current_phase = AgentPhase.DIAGNOSIS.value

            support_req.phase = current_phase

            # 5. RAG Retrieval (avoid completely when out-of-scope, escalation, greeting, or resolution)
            settings = get_settings()
            retrieved_chunks: List[SearchResultItem] = []
            sources: List[Dict[str, Any]] = []

            should_search_rag = (
                current_phase in (AgentPhase.DIAGNOSIS.value, AgentPhase.TRIAGE.value)
                and not is_escalation
                and not is_resolution
                and not is_out_of_scope
                and not is_greeting
            )

            if should_search_rag:
                try:
                    kb_status = self._rag.get_status()
                    if kb_status.is_ready:
                        raw_chunks = self._rag.search(
                            query=last_user_text,
                            top_k=3,
                        )
                        # Filter by minimum relevance threshold (discard irrelevant chunks with low similarity)
                        is_fake = getattr(getattr(self._rag, "encoder", None), "model_name", "").startswith("fake")
                        min_score = 0.0 if is_fake else settings.RAG_MIN_RELEVANCE_SCORE
                        retrieved_chunks = [c for c in raw_chunks if c.score is None or c.score >= min_score]
                        for chunk in retrieved_chunks:
                            sources.append(
                                {
                                    "doc_id": chunk.doc_id,
                                    "title": chunk.doc_title,
                                    "heading": chunk.heading,
                                    "score": chunk.score,
                                    "source_path": chunk.source_path,
                                }
                            )
                except Exception as e:
                    logger.warning("RAG retrieval failed during assistant turn: %s", e)

            # 5b. Enrich SupportRequest category using canonical task categories (docs/task.md)
            raw_kb_cat = getattr(retrieved_chunks[0], "category", None) if retrieved_chunks else None
            support_req.initial_category = normalize_task_category(
                raw_category=support_req.initial_category or raw_kb_cat,
                text=last_user_text,
            )

            # 6. Retrieve Active Incidents and Process Escalation Ticketing
            active_incidents = list(
                db.scalars(select(Incident).where(Incident.status != IncidentStatus.RESOLVED.value)).all()
            )

            # Check if an active ticket already exists for this support request
            existing_ticket = db.scalar(
                select(Ticket)
                .where(
                    Ticket.support_request_id == support_req.id,
                    Ticket.status != TicketStatus.CLOSED.value,
                )
                .order_by(Ticket.created_at.desc())
            )

            current_ticket: Optional[Ticket] = existing_ticket
            if current_ticket is None and (
                is_escalation or (current_phase == AgentPhase.FINALIZATION.value and support_req.escalation_requested)
            ):
                try:
                    explicit_source_ids = [str(s.get("doc_id", "")) for s in sources if s.get("doc_id")]
                    ticket_summary = await generate_ticket_summary(
                        support_request=support_req,
                        messages=all_messages,
                        llm_provider=self._llm,
                        explicit_sources=explicit_source_ids,
                    )
                    current_ticket = LocalTicketingAdapter.create_ticket(
                        db=db,
                        support_request_id=support_req.id,
                        conversation_id=conversation_id,
                        title=ticket_summary.title,
                        summary=ticket_summary.summary,
                        symptoms=ticket_summary.symptoms,
                        attempted_steps=ticket_summary.attempted_steps,
                        diagnostic_findings=ticket_summary.diagnostic_findings,
                        source_refs=ticket_summary.source_refs,
                        summary_quality=ticket_summary.summary_quality,
                    )
                except Exception as exc:
                    logger.error("Failed to create ticket on escalation for request %s: %s", support_req.id, exc)
                    # Invariant: Never fake ticket creation if database persistence failed
                    current_ticket = None

            # 7. Build Prompts and Context Window
            now_utc = datetime.now(timezone.utc)
            current_time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
            system_prompt = build_system_prompt(
                phase=current_phase,
                kb_chunks=retrieved_chunks,
                current_time_str=current_time_str,
                is_out_of_scope=is_out_of_scope,
                active_incidents=active_incidents,
                created_ticket_id=current_ticket.id if current_ticket else None,
            )

            # Context windowing: last N turns with timestamps & elapsed intervals
            window_size = settings.AGENT_CONTEXT_WINDOW_TURNS
            window_messages = all_messages[-window_size:]
            llm_messages: List[LLMMessage] = []
            prev_msg: Message | None = None

            for m in window_messages:
                time_str = m.created_at.strftime("%H:%M:%S UTC")
                if prev_msg is not None:
                    t_curr = m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=timezone.utc)
                    t_prev = (
                        prev_msg.created_at
                        if prev_msg.created_at.tzinfo
                        else prev_msg.created_at.replace(tzinfo=timezone.utc)
                    )
                    delta_sec = max(0, int((t_curr - t_prev).total_seconds()))
                    if delta_sec < 60:
                        elapsed_desc = f"inviato {delta_sec} secondi dopo il messaggio precedente"
                    elif delta_sec < 3600:
                        elapsed_desc = f"inviato {delta_sec // 60} minuti dopo il messaggio precedente"
                    else:
                        elapsed_desc = f"inviato {delta_sec // 3600} ore dopo il messaggio precedente"
                    content_with_time = f"[{time_str} • {elapsed_desc}]\n{m.content}"
                else:
                    content_with_time = f"[{time_str}]\n{m.content}"

                llm_messages.append(
                    LLMMessage(
                        role=m.role,
                        content=content_with_time,
                    )
                )
                prev_msg = m

            # Model and thinking level per phase
            model_name = settings.GEMINI_DIAGNOSIS_MODEL
            thinking_level = settings.GEMINI_DIAGNOSIS_THINKING
            if current_phase == AgentPhase.TRIAGE.value:
                model_name = settings.GEMINI_TRIAGE_MODEL
                thinking_level = settings.GEMINI_TRIAGE_THINKING
            elif current_phase == AgentPhase.FINALIZATION.value:
                model_name = settings.GEMINI_FINALIZATION_MODEL
                thinking_level = settings.GEMINI_FINALIZATION_THINKING

            gen_tools = [CREATE_TICKET_TOOL] if current_ticket is None else None
            gen_config = LLMGenerationConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                thinking_level=thinking_level,
                tools=gen_tools,
            )

            # 8. Generate Response from Provider
            try:
                llm_res = await self._llm.generate(
                    messages=llm_messages,
                    system_instruction=system_prompt,
                    config=gen_config,
                    model=model_name,
                )
            except Exception as e:
                logger.error("LLM Provider generation failed: %s", e)
                # Do NOT save assistant message on failure (invariant)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Generazione risposta assistente non riuscita: {e}",
                ) from e

            # 8b. Dispatch Tool Calls (e.g. create_ticket)
            ticket_tool_call = next(
                (tc for tc in llm_res.tool_calls if tc.get("name") == "create_ticket"),
                None,
            )
            if ticket_tool_call and current_ticket is None:
                args = ticket_tool_call.get("args", {})
                t_title = redact_secrets(str(args.get("title") or "Richiesta intervento tecnico"))
                t_symptoms = redact_secrets(str(args.get("symptoms") or last_user_text))
                t_reason = redact_secrets(str(args.get("reason") or "Escalation richiesta tramite tool"))

                # Check if ticket already exists (idempotency)
                existing_ticket = db.scalar(
                    select(Ticket)
                    .where(
                        Ticket.support_request_id == support_req.id,
                        Ticket.status != TicketStatus.CLOSED.value,
                    )
                    .order_by(Ticket.created_at.desc())
                )
                if existing_ticket:
                    current_ticket = existing_ticket
                else:
                    try:
                        explicit_source_ids = [str(s.get("doc_id", "")) for s in sources if s.get("doc_id")]
                        current_ticket = LocalTicketingAdapter.create_ticket(
                            db=db,
                            support_request_id=support_req.id,
                            conversation_id=conversation_id,
                            title=t_title,
                            summary=f"{t_title} - {t_reason}",
                            symptoms=t_symptoms,
                            attempted_steps=t_reason,
                            diagnostic_findings=f"Aperto tramite tool 'create_ticket': {t_reason}",
                            source_refs=explicit_source_ids,
                            summary_quality="llm",
                        )
                    except Exception as exc:
                        logger.error("Failed to create ticket via create_ticket tool: %s", exc)
                        current_ticket = None

                # Update support request state
                support_req.escalation_requested = True
                support_req.outcome = RequestOutcome.ESCALATED.value
                current_phase = AgentPhase.FINALIZATION.value
                support_req.phase = current_phase

                # Complete the tool call roundtrip
                if current_ticket:
                    tool_result = {
                        "ticket_id": current_ticket.id,
                        "status": current_ticket.status,
                        "title": current_ticket.title,
                        "message": f"Ticket {current_ticket.id} aperto con successo nel Service Desk IT.",
                    }
                else:
                    tool_result = {
                        "error": "Impossibile aprire il ticket al momento per errore di persistenza.",
                        "status": "failed",
                    }

                raw_candidate = llm_res.metadata.get("raw_candidate_content")
                try:
                    llm_res = await self._llm.generate_with_tool_result(
                        messages=llm_messages,
                        tool_call=ticket_tool_call,
                        tool_result=tool_result,
                        raw_candidate_content=raw_candidate,
                        system_instruction=system_prompt,
                        config=gen_config,
                        model=model_name,
                    )
                except Exception as exc:
                    logger.warning("Error generating final response after tool execution: %s", exc)
                    if current_ticket:
                        fallback_text = (
                            f"Ho aperto per te il ticket di supporto IT **{current_ticket.id}**. "
                            "La tua richiesta è stata presa in carico dal Service Desk e un tecnico "
                            "analizzerà il caso al più presto."
                        )
                    else:
                        fallback_text = (
                            "Si è verificato un problema temporaneo nella creazione del ticket. "
                            "Puoi contattare direttamente il Service Desk al numero interno 5555."
                        )
                    llm_res.content = fallback_text

            # 9. Atomically Persist Assistant Message
            sanitized_response = redact_secrets(llm_res.content)
            contains_resolution_phrase = bool(RESOLUTION_PROMPT_PHRASE_PATTERN.search(sanitized_response))
            is_bot_resolution = (
                (is_resolution or current_phase == AgentPhase.FINALIZATION.value or contains_resolution_phrase)
                and not support_req.escalation_requested
                and current_ticket is None
            )
            is_truncated = (llm_res.finish_reason == "MAX_TOKENS")
            if is_truncated:
                logger.warning(
                    "Assistant turn response for conversation %s was truncated by MAX_TOKENS: "
                    "prompt_tokens=%d, thoughts_tokens=%d, completion_tokens=%d",
                    conversation_id,
                    llm_res.token_usage.prompt_tokens,
                    llm_res.token_usage.thoughts_tokens,
                    llm_res.token_usage.completion_tokens,
                )

            assistant_metadata: Dict[str, Any] = {
                "sources": sources,
                "phase": current_phase,
                "escalation_requested": support_req.escalation_requested,
                "resolution_proposed": is_bot_resolution,
                "request_id": support_req.id,
                "tokens": llm_res.token_usage.model_dump(),
                "latency_ms": llm_res.latency_ms,
                "model": llm_res.model,
                "finish_reason": llm_res.finish_reason,
                "is_truncated": is_truncated,
            }
            if current_ticket:
                assistant_metadata["ticket_id"] = current_ticket.id
                assistant_metadata["ticket_status"] = current_ticket.status
                assistant_metadata["summary_quality"] = current_ticket.summary_quality

            assistant_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=sanitized_response,
                metadata_json=assistant_metadata,
            )
            db.add(assistant_msg)

            # Update conversation & support request timestamp
            now = datetime.now(timezone.utc)
            conv.updated_at = now
            support_req.updated_at = now

            # 10. Emit Structured Audit Event
            record_audit_event(
                db=db,
                event_type="assistant_turn_completed",
                conversation_id=conversation_id,
                request_id=support_req.id,
                payload={
                    "phase": current_phase,
                    "escalation_requested": support_req.escalation_requested,
                    "resolution_proposed": is_bot_resolution,
                    "ticket_id": current_ticket.id if current_ticket else None,
                    "sources_count": len(sources),
                    "content": redact_secrets(assistant_msg.content),
                    "token_usage": llm_res.token_usage.model_dump(),
                    "latency_ms": llm_res.latency_ms,
                    "finish_reason": llm_res.finish_reason,
                    "is_truncated": is_truncated,
                },
            )

            db.commit()
            db.refresh(assistant_msg)

            return AssistantTurnResult(
                message=MessageResponse.model_validate(assistant_msg),
                sources=sources,
                phase=current_phase,
                escalation_requested=support_req.escalation_requested,
                resolution_proposed=is_bot_resolution,
                request_id=support_req.id,
                ticket_id=current_ticket.id if current_ticket else None,
                ticket_status=current_ticket.status if current_ticket else None,
                tokens=llm_res.token_usage.model_dump(),
                latency_ms=llm_res.latency_ms,
                finish_reason=llm_res.finish_reason,
                is_truncated=is_truncated,
            )


