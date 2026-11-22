from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TechnicianChatMessageRequest(BaseModel):
    """Payload to send a message in the technician assistant chat."""

    content: str = Field(..., min_length=1, description="Contenuto del messaggio del tecnico")
    author: str = Field(default="technician_demo", description="Nome o ID del tecnico")


class TechnicianChatMessageResponse(BaseModel):
    """Schema representing a single message in technician chat."""

    id: str
    ticket_id: str
    sender: str
    content: str
    proposals_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TechnicianChatHistoryResponse(BaseModel):
    """List of messages in the technician chat for a ticket."""

    items: List[TechnicianChatMessageResponse]
    total: int


class TechnicianChatTurnResponse(BaseModel):
    """Response returned when the technician posts a message and the AI responds."""

    technician_message: TechnicianChatMessageResponse
    assistant_message: TechnicianChatMessageResponse
    proposals: Optional[Dict[str, Any]] = None
