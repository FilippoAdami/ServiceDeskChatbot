from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from backend.app.llm.models import LLMGenerationConfig, LLMMessage, LLMResponse


class BaseLLMProvider(ABC):
    """Abstract interface for large language model generation providers."""

    @property
    def is_configured(self) -> bool:
        """Indicate whether the provider has credentials and is ready to process requests."""
        return True

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        system_instruction: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """Asynchronously generate a completion from a list of conversational messages."""
        pass

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
        """Asynchronously generate a completion following a tool execution."""
        return await self.generate(
            messages=messages,
            system_instruction=system_instruction,
            config=config,
            model=model,
        )
