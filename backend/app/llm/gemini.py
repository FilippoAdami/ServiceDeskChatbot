from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, List, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend.app.config import get_settings
from backend.app.core.redaction import redact_secrets
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.models import (
    LLMGenerationConfig,
    LLMMessage,
    LLMResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class GeminiLLMProvider(BaseLLMProvider):
    """Production LLM provider using Google Gemini GenAI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gemini-3.5-flash-lite",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._default_model = default_model or settings.GEMINI_DIAGNOSIS_MODEL
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

        if not self._api_key:
            logger.warning("GeminiLLMProvider initialized without GEMINI_API_KEY")
            self._client = None
        else:
            self._client = genai.Client(api_key=self._api_key)

    @property
    def is_configured(self) -> bool:
        return self._client is not None and bool(self._api_key)

    def format_and_sanitize_contents(self, messages: List[LLMMessage]) -> List[Any]:
        """Convert LLMMessage list to Gemini Content objects with secret redaction."""
        gemini_contents: List[Any] = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            clean_text = redact_secrets(msg.content)
            gemini_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=clean_text)],
                )
            )
        return gemini_contents

    async def generate(
        self,
        messages: List[LLMMessage],
        system_instruction: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
        model: Optional[str] = None,
    ) -> LLMResponse:
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "Gemini API key is not configured in the backend environment. "
                "Set GEMINI_API_KEY in .env to enable real Gemini inference."
            )

        active_model = model or self._default_model
        cfg = config or LLMGenerationConfig()
        gemini_contents = self.format_and_sanitize_contents(messages)

        thinking_cfg = None
        if cfg.thinking_level:
            level_str = cfg.thinking_level.upper()
            level_map = {
                "MINIMAL": types.ThinkingLevel.MINIMAL,
                "LOW": types.ThinkingLevel.LOW,
                "MEDIUM": types.ThinkingLevel.MEDIUM,
                "HIGH": types.ThinkingLevel.HIGH,
                "XHIGH": types.ThinkingLevel.XHIGH,
            }
            if level_str in level_map:
                thinking_cfg = types.ThinkingConfig(thinking_level=level_map[level_str])

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=cfg.temperature,
            max_output_tokens=cfg.max_output_tokens,
            stop_sequences=cfg.stop_sequences,
            thinking_config=thinking_cfg,
            tools=cfg.tools if cfg.tools else None,
        )

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                t0 = time.perf_counter()
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=active_model,
                        contents=gemini_contents,
                        config=gen_config,
                    ),
                    timeout=self._timeout_seconds,
                )
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

                text = response.text or ""

                # Extract finish reason
                finish_reason_str = None
                raw_candidate_content = None
                candidates = getattr(response, "candidates", None)
                if candidates and len(candidates) > 0:
                    c = candidates[0]
                    raw_candidate_content = getattr(c, "content", None)
                    fr = getattr(c, "finish_reason", None)
                    if fr is not None:
                        finish_reason_str = getattr(fr, "name", str(fr))

                # Extract tool calls
                tool_calls: List[dict] = []
                if hasattr(response, "function_calls") and response.function_calls:
                    for fc in response.function_calls:
                        tool_calls.append(
                            {
                                "name": fc.name,
                                "args": dict(fc.args) if fc.args else {},
                                "id": getattr(fc, "id", None),
                            }
                        )

                # Extract token usage
                usage = TokenUsage()
                thoughts_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
                    um = response.usage_metadata
                    thoughts_tokens = getattr(um, "thoughts_token_count", 0) or 0
                    usage = TokenUsage(
                        prompt_tokens=getattr(um, "prompt_token_count", 0) or 0,
                        completion_tokens=getattr(um, "candidates_token_count", 0) or 0,
                        total_tokens=getattr(um, "total_token_count", 0) or 0,
                        thoughts_tokens=thoughts_tokens,
                    )

                if finish_reason_str == "MAX_TOKENS":
                    logger.warning(
                        "Gemini response truncated by MAX_TOKENS: "
                        "prompt=%d, thoughts=%d, completion=%d, total=%d, configured_max=%d",
                        usage.prompt_tokens,
                        thoughts_tokens,
                        usage.completion_tokens,
                        usage.total_tokens,
                        gen_config.max_output_tokens or 0,
                    )

                return LLMResponse(
                    content=text,
                    token_usage=usage,
                    model=active_model,
                    latency_ms=elapsed_ms,
                    finish_reason=finish_reason_str,
                    tool_calls=tool_calls,
                    metadata={
                        "thoughts_tokens": thoughts_tokens,
                        "raw_candidate_content": raw_candidate_content,
                    },
                )

            except (APIError, asyncio.TimeoutError) as err:
                last_error = err
                is_transient = False
                if isinstance(err, asyncio.TimeoutError):
                    is_transient = True
                elif isinstance(err, APIError):
                    code = getattr(err, "code", None)
                    if code in (429, 500, 502, 503, 504):
                        is_transient = True

                logger.warning(
                    "Gemini API error on attempt %d/%d (transient=%s): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    is_transient,
                    err,
                )

                if is_transient and attempt < self._max_retries:
                    # Exponential backoff
                    await asyncio.sleep(1.0 * (2**attempt))
                    continue
                raise

            except Exception as err:
                logger.error("Non-retryable error in Gemini generation: %s", err)
                raise

        raise RuntimeError(f"Gemini generation failed after {self._max_retries + 1} attempts: {last_error}")

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
        """Asynchronously continue generation after executing a tool call."""
        if not self.is_configured or self._client is None:
            raise RuntimeError(
                "Gemini API key is not configured in the backend environment. "
                "Set GEMINI_API_KEY in .env to enable real Gemini inference."
            )

        active_model = model or self._default_model
        cfg = config or LLMGenerationConfig()
        gemini_contents = self.format_and_sanitize_contents(messages)

        # Candidate content with function call (preserve thought_signature if available)
        if raw_candidate_content is not None:
            model_content = raw_candidate_content
        else:
            model_content = types.Content(
                role="model",
                parts=[types.Part.from_function_call(name=tool_call["name"], args=tool_call.get("args", {}))],
            )

        # Tool response content from user
        tool_resp_content = types.Content(
            role="user",
            parts=[
                types.Part.from_function_response(
                    name=tool_call["name"],
                    response={"result": tool_result},
                )
            ],
        )

        all_contents = list(gemini_contents) + [model_content, tool_resp_content]

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=cfg.temperature,
            max_output_tokens=cfg.max_output_tokens,
            tools=cfg.tools if cfg.tools else None,
        )

        t0 = time.perf_counter()
        response = await self._client.aio.models.generate_content(
            model=active_model,
            contents=all_contents,
            config=gen_config,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Extract token usage
        usage = TokenUsage()
        thoughts_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
            um = response.usage_metadata
            thoughts_tokens = getattr(um, "thoughts_token_count", 0) or 0
            usage = TokenUsage(
                prompt_tokens=getattr(um, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(um, "candidates_token_count", 0) or 0,
                total_tokens=getattr(um, "total_token_count", 0) or 0,
                thoughts_tokens=thoughts_tokens,
            )

        return LLMResponse(
            content=response.text or "",
            token_usage=usage,
            model=active_model,
            latency_ms=elapsed_ms,
            finish_reason=None,
            metadata={"thoughts_tokens": thoughts_tokens},
        )

