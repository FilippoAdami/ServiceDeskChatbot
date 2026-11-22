from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditEventItem(BaseModel):
    """Structured audit event item for inspection in debug console."""

    id: str
    event_type: str
    category: str = Field(
        ...,
        description="Category: 'employee' (user actions), 'technician' (IT ops), or 'system'",
    )
    action_label: str = Field(
        ...,
        description="Human readable Italian label for the event",
    )
    conversation_id: Optional[str] = None
    request_id: Optional[str] = None
    ticket_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditConversationSummary(BaseModel):
    """Conversation summary tailored for audit log grouping and thread filtering."""

    conversation_id: str
    title: str
    user_id: str
    status: str
    event_count: int = 0
    ticket_id: Optional[str] = None
    ticket_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditEventsResponse(BaseModel):
    """Paginated response of audit events."""

    items: List[AuditEventItem]
    total: int
    limit: int
    offset: int


class AuditConversationsResponse(BaseModel):
    """List of conversations available for audit filtering."""

    items: List[AuditConversationSummary]
    total: int
