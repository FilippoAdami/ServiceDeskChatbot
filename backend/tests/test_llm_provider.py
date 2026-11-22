from __future__ import annotations

import asyncio

import pytest
from google.genai.errors import APIError

from backend.app.llm.gemini import GeminiLLMProvider
from backend.app.llm.mock import MockLLMProvider
from backend.app.llm.models import LLMGenerationConfig, LLMMessage


@pytest.mark.asyncio
async def test_mock_llm_provider_generation() -> None:
    provider = MockLLMProvider()
    messages = [LLMMessage(role="user", content="Problema con la posta Outlook")]

    response = await provider.generate(
        messages=messages,
        system_instruction="Sei un assistente IT",
        config=LLMGenerationConfig(temperature=0.2),
        model="test-model",
    )

    assert response.content != ""
    assert response.token_usage.total_tokens > 0
    assert response.model == "test-model"
    assert len(provider.history) == 1
    assert provider.history[0]["messages"] == messages


@pytest.mark.asyncio
async def test_mock_llm_provider_timeout_simulation() -> None:
    provider = MockLLMProvider(simulate_timeout=True)
    messages = [LLMMessage(role="user", content="Test timeout")]

    with pytest.raises(asyncio.TimeoutError):
        await provider.generate(messages=messages)


@pytest.mark.asyncio
async def test_mock_llm_provider_rate_limit_simulation() -> None:
    provider = MockLLMProvider(simulate_rate_limit=True)
    messages = [LLMMessage(role="user", content="Test 429")]

    with pytest.raises(APIError) as exc_info:
        await provider.generate(messages=messages)
    assert exc_info.value.code == 429


@pytest.mark.asyncio
async def test_mock_llm_provider_server_error_simulation() -> None:
    provider = MockLLMProvider(simulate_server_error=True)
    messages = [LLMMessage(role="user", content="Test 503")]

    with pytest.raises(APIError) as exc_info:
        await provider.generate(messages=messages)
    assert exc_info.value.code == 503


@pytest.mark.asyncio
async def test_mock_llm_provider_canned_responses() -> None:
    provider = MockLLMProvider(canned_responses=["Risposta 1", "Risposta 2"])
    messages = [LLMMessage(role="user", content="Ciao")]

    res1 = await provider.generate(messages=messages)
    assert res1.content == "Risposta 1"

    res2 = await provider.generate(messages=messages)
    assert res2.content == "Risposta 2"


def test_gemini_provider_sanitization() -> None:
    provider = GeminiLLMProvider(api_key="mock_key")
    sensitive_messages = [
        LLMMessage(
            role="user",
            content="Ecco la mia password: SecretPassword123! e token: eyJhbGciOiJIUzI1NiJ9.test",
        ),
    ]

    sanitized = provider.format_and_sanitize_contents(sensitive_messages)
    assert len(sanitized) == 1
    # Secrets should be redacted
    text_content = sanitized[0].parts[0].text
    assert "SecretPassword123!" not in text_content
    assert "[REDACTED" in text_content
