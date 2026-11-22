from __future__ import annotations

import enum
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.ticket import TicketItem


class IncidentStatusEnum(str, enum.Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class IncidentItem(BaseModel):
    """Schema representing a company-wide IT incident."""

    id: str
    service: str
    title: str
    symptoms: str
    summary: str
    status: str
    created_at: datetime
    updated_at: datetime
    ticket_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class IncidentDetail(BaseModel):
    """Detail schema for an incident including linked tickets."""

    id: str
    service: str
    title: str
    symptoms: str
    summary: str
    status: str
    created_at: datetime
    updated_at: datetime
    ticket_count: int = 0
    tickets: List[TicketItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    """Response containing list of incidents."""

    items: List[IncidentItem]
    total: int
