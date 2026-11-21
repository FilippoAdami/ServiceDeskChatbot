from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def generate_uuid(prefix: str = "") -> str:
    """Generate a clean unique identifier with optional prefix."""
    raw = uuid.uuid4().hex[:16]
    return f"{prefix}_{raw}" if prefix else raw


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    WAITING_USER = "waiting_user"
    ARCHIVED = "archived"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class RequestStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class RequestOutcome(str, enum.Enum):
    RESOLVED_CONFIRMED = "resolved_confirmed"
    RESOLVED_UNCONFIRMED = "resolved_unconfirmed"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"


class Conversation(Base):
    """Represents a persistent user conversation thread."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("conv"),
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="user_demo_01",
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ConversationStatus.ACTIVE.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc(), Message.id.asc()",
    )
    requests: Mapped[List["SupportRequest"]] = relationship(
        "SupportRequest",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="SupportRequest.created_at.desc()",
    )


class Message(Base):
    """Represents a single message inside a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("msg"),
    )
    conversation_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=MessageRole.USER.value,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )


class SupportRequest(Base):
    """Represents an IT support request tracked across diagnosis or escalation.

    Multiple SupportRequests can be associated with the same conversation thread.
    """

    __tablename__ = "support_requests"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("req"),
    )
    conversation_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    initial_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    final_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RequestStatus.OPEN.value,
        index=True,
    )
    outcome: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="requests",
    )


class AuditEvent(Base):
    """Structured audit log entry persisted in real time at action occurrence.

    Contains sanitized metadata only (never full message text or secrets).
    """

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("evt"),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )


# Indexes for compound lookups
Index("ix_messages_conv_created", Message.conversation_id, Message.created_at)
Index("ix_requests_conv_created", SupportRequest.conversation_id, SupportRequest.created_at)
