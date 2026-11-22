from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for adding a user message to a conversation.

    Public API in G02 only permits user messages.
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text content of the message",
    )


class MessageResponse(BaseModel):
    """Schema representing a stored message."""

    id: str
    conversation_id: str
    role: str
    content: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
