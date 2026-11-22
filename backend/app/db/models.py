from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
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


class AgentPhase(str, enum.Enum):
    TRIAGE = "triage"
    DIAGNOSIS = "diagnosis"
    FINALIZATION = "finalization"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class ActivityType(str, enum.Enum):
    CREATED = "created"
    NOTE = "note"
    STATUS_CHANGE = "status_change"
    INCIDENT_LINKED = "incident_linked"
    INCIDENT_UNLINKED = "incident_unlinked"


class ProposalStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHING_FAILED = "publishing_failed"


class ProposalSourceType(str, enum.Enum):
    SUPPORT_REQUEST = "support_request"
    TICKET = "ticket"


class ProposalDestination(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"


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
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
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
    phase: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AgentPhase.TRIAGE.value,
        index=True,
    )
    escalation_requested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="support_request",
        cascade="all, delete-orphan",
        order_by="Ticket.created_at.desc()",
    )


class Incident(Base):
    """Represents a shared company-wide IT incident (outage, degradation, scheduled maintenance)."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=IncidentStatus.INVESTIGATING.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="incident",
        order_by="Ticket.created_at.desc()",
    )


class Ticket(Base):
    """Represents an IT support ticket generated upon chatbot escalation.

    Linked to the triggering SupportRequest and Conversation.
    """

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("tick"),
    )
    support_request_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("support_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TicketStatus.OPEN.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TicketPriority.MEDIUM.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_steps: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostic_findings: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    summary_quality: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="llm",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    support_request: Mapped["SupportRequest"] = relationship(
        "SupportRequest",
        back_populates="tickets",
    )
    conversation: Mapped["Conversation"] = relationship("Conversation")
    incident: Mapped[Optional["Incident"]] = relationship(
        "Incident",
        back_populates="tickets",
    )
    activities: Mapped[List["TicketActivity"]] = relationship(
        "TicketActivity",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketActivity.created_at.asc()",
    )

    @property
    def category(self) -> Optional[str]:
        if self.support_request:
            raw = self.support_request.final_category or self.support_request.initial_category
            if raw:
                from backend.app.knowledge.categories import normalize_task_category

                return normalize_task_category(raw)
        return None
    tech_messages: Mapped[List["TechnicianChatMessage"]] = relationship(
        "TechnicianChatMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TechnicianChatMessage.created_at.asc()",
    )


class TicketActivity(Base):
    """Represents an entry in the ticket activity timeline (notes, status changes, incident links)."""

    __tablename__ = "ticket_activities"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("act"),
    )
    ticket_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author: Mapped[str] = mapped_column(String(64), nullable=False, default="technician_demo")
    author_role: Mapped[str] = mapped_column(String(32), nullable=False, default="technician")
    activity_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ActivityType.NOTE.value,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="activities")


class TechnicianChatMessage(Base):
    """Represents a message in the technician AI assistant chat dedicated to a ticket."""

    __tablename__ = "technician_chat_messages"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("tm"),
    )
    ticket_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(String(32), nullable=False)  # "technician" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    proposals_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="tech_messages")


class KnowledgeProposal(Base):
    """Represents a draft knowledge base guide generated from a resolved request or ticket.

    Requires human technician review, duplicate verification, and explicit approval before
    being written to a Markdown file in knowledge_base/ and re-indexed in RAG.
    """

    __tablename__ = "knowledge_proposals"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: generate_uuid("prop"),
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # "support_request" | "ticket"
    source_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProposalStatus.DRAFT.value,
        index=True,
    )  # "draft" | "approved" | "rejected" | "publishing_failed"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProposalDestination.CREATE.value,
    )  # "create" | "update"
    target_kb_slug: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    summary_quality: Mapped[str] = mapped_column(String(32), nullable=False, default="llm")
    author: Mapped[str] = mapped_column(String(64), nullable=False, default="system_ai")
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
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
Index("ix_tickets_req_status", Ticket.support_request_id, Ticket.status)
Index("ix_tickets_conv_created", Ticket.conversation_id, Ticket.created_at)
Index("ix_ticket_activities_ticket_created", TicketActivity.ticket_id, TicketActivity.created_at)
Index("ix_tech_messages_ticket_created", TechnicianChatMessage.ticket_id, TechnicianChatMessage.created_at)
Index("ix_kb_proposals_status_updated", KnowledgeProposal.status, KnowledgeProposal.updated_at)
Index("ix_kb_proposals_source", KnowledgeProposal.source_type, KnowledgeProposal.source_id)
