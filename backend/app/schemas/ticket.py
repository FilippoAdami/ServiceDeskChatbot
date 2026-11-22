from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TicketStatusEnum(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriorityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketActivityItem(BaseModel):
    """Schema representing an activity or note on a ticket."""

    id: str
    ticket_id: str
    author: str
    author_role: str
    activity_type: str
    content: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketItem(BaseModel):
    """Compact schema for tickets in lists."""

    id: str
    support_request_id: str
    conversation_id: str
    incident_id: Optional[str] = None
    category: Optional[str] = None
    status: str
    priority: str
    title: str
    summary: str
    summary_quality: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketDetail(BaseModel):
    """Full detail schema for a ticket including diagnostics and activities."""

    id: str
    support_request_id: str
    conversation_id: str
    incident_id: Optional[str] = None
    category: Optional[str] = None
    status: str
    priority: str
    title: str
    summary: str
    symptoms: str
    attempted_steps: str
    diagnostic_findings: str
    source_refs: Optional[List[str]] = Field(default_factory=list)
    summary_quality: str
    created_at: datetime
    updated_at: datetime
    activities: List[TicketActivityItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TicketStatusUpdateRequest(BaseModel):
    """Request payload to transition ticket status."""

    status: str
    note: Optional[str] = None
    author: str = "technician_demo"


class TicketNoteCreateRequest(BaseModel):
    """Request payload to append a technical note."""

    content: str
    author: str = "technician_demo"


class TicketIncidentLinkRequest(BaseModel):
    """Request payload to link or unlink an incident."""

    incident_id: Optional[str] = None
    author: str = "technician_demo"


class TicketListResponse(BaseModel):
    """Paginated response for tickets list."""

    items: List[TicketItem]
    total: int
    limit: int
    offset: int
