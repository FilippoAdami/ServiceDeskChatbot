from __future__ import annotations

from typing import Optional

from backend.app.config import get_settings
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.gemini import GeminiLLMProvider
from backend.app.llm.mock import MockLLMProvider
from backend.app.llm.models import (
    LLMGenerationConfig,
    LLMMessage,
    LLMResponse,
    TokenUsage,
)

_llm_provider_instance: Optional[BaseLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    """Dependency injection factory for FastAPI and Agent Orchestrator."""
    global _llm_provider_instance
    if _llm_provider_instance is None:
        settings = get_settings()
        _llm_provider_instance = GeminiLLMProvider(
            api_key=settings.GEMINI_API_KEY,
            default_model=settings.GEMINI_DIAGNOSIS_MODEL,
            timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
            max_retries=settings.GEMINI_MAX_RETRIES,
        )
    return _llm_provider_instance


def reset_llm_provider_for_test(provider: Optional[BaseLLMProvider] = None) -> None:
    """Helper to inject MockLLMProvider in test suites."""
    global _llm_provider_instance
    _llm_provider_instance = provider


__all__ = [
    "BaseLLMProvider",
    "GeminiLLMProvider",
    "LLMGenerationConfig",
    "LLMMessage",
    "LLMResponse",
    "MockLLMProvider",
    "TokenUsage",
    "get_llm_provider",
    "reset_llm_provider_for_test",
]
