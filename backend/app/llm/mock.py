from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from google.genai.errors import APIError

from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import (
    LLMGenerationConfig,
    LLMMessage,
    LLMResponse,
    TokenUsage,
)


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, offline LLM provider for unit tests, integration tests, and CI."""

    def __init__(
        self,
        canned_responses: Optional[List[str]] = None,
        canned_tool_calls: Optional[List[List[dict]]] = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_server_error: bool = False,
        simulate_empty: bool = False,
        is_configured: bool = True,
    ) -> None:
        self.canned_responses: List[str] = list(canned_responses or [])
        self.canned_tool_calls: List[List[dict]] = list(canned_tool_calls or [])
        self.simulate_timeout: bool = simulate_timeout
        self.simulate_rate_limit: bool = simulate_rate_limit
        self.simulate_server_error: bool = simulate_server_error
        self.simulate_empty: bool = simulate_empty
        self._is_configured: bool = is_configured

        self.call_count: int = 0
        self.history: List[dict] = []

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    @is_configured.setter
    def is_configured(self, value: bool) -> None:
        self._is_configured = value

    async def generate(
        self,
        messages: List[LLMMessage],
        system_instruction: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
        model: Optional[str] = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.history.append(
            {
                "messages": messages,
                "system_instruction": system_instruction,
                "config": config,
                "model": model,
            }
        )

        if self.simulate_timeout:
            raise asyncio.TimeoutError("Simulated LLM call timeout")

        if self.simulate_rate_limit:
            raise APIError(code=429, response_json={"error": {"message": "Simulated 429 Resource Exhausted"}})

        if self.simulate_server_error:
            raise APIError(code=503, response_json={"error": {"message": "Simulated 503 Backend Unavailable"}})

        if self.simulate_empty:
            return LLMResponse(
                content="",
                token_usage=TokenUsage(prompt_tokens=10, completion_tokens=0, total_tokens=10),
                model=model or "mock-model",
                latency_ms=1.0,
            )

        if self.canned_tool_calls:
            calls = self.canned_tool_calls.pop(0)
            return LLMResponse(
                content="",
                token_usage=TokenUsage(prompt_tokens=40, completion_tokens=10, total_tokens=50),
                model=model or "mock-model",
                latency_ms=1.5,
                tool_calls=calls,
            )

        if self.canned_responses:
            content = self.canned_responses.pop(0)
            return LLMResponse(
                content=content,
                token_usage=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
                model=model or "mock-model",
                latency_ms=2.0,
            )

        # Automatic phase-aware heuristic response based on system instruction / messages
        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content.lower()
                break

        sys_str = (system_instruction or "").lower()

        if "tecnico" in last_user_msg or "umano" in last_user_msg or "escalation" in last_user_msg:
            content = (
                "Ho registrato la tua richiesta di intervento con un tecnico specializzato del Service Desk. "
                "La segnalazione è stata contrassegnata per escalation prioritaria. "
                "Ti informo che il sistema di ticketing automatico sarà attivato a breve con il prossimo rilascio; "
                "nel frattempo i tecnici hanno visibilità diretta della tua richiesta nella console interna."
            )
        elif "finalizzazione" in sys_str:
            content = (
                "Riepilogo della procedura eseguita: abbiamo verificato la configurazione "
                "e applicato i passaggi raccomandati. "
                "Puoi confermarmi se il problema è stato risolto con successo o se hai bisogno di ulteriore supporto?"
            )
        elif "diagnosi" in sys_str:
            content = (
                "In base alla procedura aziendale [KB-MAIL-001], ti suggerisco di seguire questi passaggi:\n"
                "1. Accedi via webmail a https://outlook.office.com per verificare se la casella è attiva.\n"
                "2. Nel client desktop, controlla in basso a destra che non sia attivo 'Lavora non in linea'.\n"
                "3. Se richiesto, inserisci la password aziendale completando l'autenticazione MFA.\n"
                "Fammi sapere l'esito di questa verifica."
            )
        else:
            # Triage phase
            content = (
                "Ho compreso che riscontri una problematica tecnica. Per poterti guidare con precisione: "
                "il problema si verifica da client installato o da browser web? "
                "Ricevi uno specifico codice di errore a schermo?"
            )

        return LLMResponse(
            content=content,
            token_usage=TokenUsage(prompt_tokens=120, completion_tokens=65, total_tokens=185),
            model=model or "mock-model",
            latency_ms=5.0,
        )

    async def generate_with_tool_result(
        self,
        messages: List[LLMMessage],
        tool_call: dict,
        tool_result: dict,
        raw_candidate_content: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
        model: Optional[str] = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.history.append(
            {
                "messages": messages,
                "tool_call": tool_call,
                "tool_result": tool_result,
                "system_instruction": system_instruction,
            }
        )
        if "error" in tool_result or tool_result.get("status") == "failed":
            content = (
                "Non è stato possibile aprire automaticamente il ticket di supporto per un errore di sistema. "
                "Puoi contattare direttamente il Service Desk IT al numero interno 5555."
            )
        else:
            t_id = tool_result.get("ticket_id", "tick_mock")
            content = (
                f"Ho aperto con successo il ticket di supporto {t_id}. "
                "Un tecnico del Service Desk IT analizzerà il caso al più presto."
            )
        return LLMResponse(
            content=content,
            token_usage=TokenUsage(prompt_tokens=80, completion_tokens=30, total_tokens=110),
            model=model or "mock-model",
            latency_ms=2.0,
        )

