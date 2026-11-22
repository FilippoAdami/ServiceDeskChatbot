from __future__ import annotations

from typing import Optional

from fastapi import Depends

from backend.app.agent.orchestrator import (
    AssistantTurnResult,
    ConversationalAgentOrchestrator,
)
from backend.app.agent.prompts import build_system_prompt
from backend.app.llm import BaseLLMProvider, get_llm_provider
from backend.app.rag.service import KnowledgeRetrievalService, get_rag_service

_orchestrator_instance: Optional[ConversationalAgentOrchestrator] = None


def get_agent_orchestrator(
    llm: BaseLLMProvider = Depends(get_llm_provider),
    rag: KnowledgeRetrievalService = Depends(get_rag_service),
) -> ConversationalAgentOrchestrator:
    """Dependency provider for ConversationalAgentOrchestrator."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ConversationalAgentOrchestrator(
            llm_provider=llm,
            rag_service=rag,
        )
    return _orchestrator_instance


def reset_agent_orchestrator_for_test(
    orchestrator: Optional[ConversationalAgentOrchestrator] = None,
) -> None:
    """Helper to inject custom orchestrator in test fixtures."""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator


__all__ = [
    "AssistantTurnResult",
    "ConversationalAgentOrchestrator",
    "build_system_prompt",
    "get_agent_orchestrator",
    "reset_agent_orchestrator_for_test",
]
