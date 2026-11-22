from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SupportRequestCreate(BaseModel):
    """Schema for registering a support request associated with a conversation."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Brief summary or subject of the problem",
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=10000,
        description="Detailed description of symptoms and context",
    )
    initial_category: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Preliminary problem category (e.g. account, email, network)",
    )


class SupportRequestResponse(BaseModel):
    """Schema representing a stored SupportRequest."""

    id: str
    conversation_id: str
    title: str
    description: str
    initial_category: Optional[str] = None
    final_category: Optional[str] = None
    status: str
    phase: str = "triage"
    escalation_requested: bool = False
    outcome: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupportRequestListResponse(BaseModel):
    """Schema for paginated support request list."""

    items: List[SupportRequestResponse]
    total: int
    limit: int
    offset: int


class ConfirmResolutionRequest(BaseModel):
    """Payload for confirming or auto-closing a bot-resolved support request."""

    confirmed_by_user: bool = Field(
        default=True,
        description="True if explicitly confirmed by user click, False if triggered by auto-timer expiry",
    )

