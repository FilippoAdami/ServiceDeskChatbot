from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """Normalized message passed to an LLM provider."""

    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Text content of the message")


class TokenUsage(BaseModel):
    """Token consumption metadata reported by the provider."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    thoughts_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    """Standardized response returned by an LLM provider."""

    content: str = Field(..., description="Generated text response")
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str = Field(..., description="Model identifier used for generation")
    latency_ms: float = Field(default=0.0, ge=0.0)
    finish_reason: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tool / function calls requested by the model",
    )


class LLMGenerationConfig(BaseModel):
    """Runtime generation parameters."""

    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=4096, ge=64, le=8192)
    stop_sequences: Optional[List[str]] = Field(default=None)
    thinking_level: Optional[str] = Field(
        default=None,
        description="Thinking level for models supporting chain-of-thought: low, medium, high",
    )
    tools: Optional[List[Any]] = Field(
        default=None,
        description="Tools or function declarations provided to the model",
    )
