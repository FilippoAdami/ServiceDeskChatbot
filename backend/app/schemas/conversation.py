from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.message import MessageResponse
from backend.app.schemas.support_request import SupportRequestResponse


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional title or topic for the conversation thread",
    )
    user_id: Optional[str] = Field(
        default="user_demo_01",
        max_length=64,
        description="Demo user identifier",
    )


class ConversationSummaryResponse(BaseModel):
    """Schema for summarized conversation item in lists."""

    id: str
    user_id: str
    title: Optional[str] = None
    category: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    request_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Detailed conversation schema with full ordered messages and associated requests."""

    id: str
    user_id: str
    title: Optional[str] = None
    category: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)
    requests: List[SupportRequestResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """Schema for paginated conversations list."""

    items: List[ConversationSummaryResponse]
    total: int
    limit: int
    offset: int
