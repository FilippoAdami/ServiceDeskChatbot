"""Add technician_chat_messages and knowledge_proposals tables.

Revision ID: 004_technician_chat_and_knowledge_proposals
Revises: 003_tickets_and_incidents
Create Date: 2026-11-22 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_technician_chat_and_knowledge_proposals"
down_revision: Union[str, None] = "003_tickets_and_incidents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create technician_chat_messages table
    op.create_table(
        "technician_chat_messages",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column(
            "ticket_id",
            sa.String(length=32),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("proposals_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_technician_chat_messages_ticket_id",
        "technician_chat_messages",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        "ix_technician_chat_messages_created_at",
        "technician_chat_messages",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_tech_messages_ticket_created",
        "technician_chat_messages",
        ["ticket_id", "created_at"],
        unique=False,
    )

    # 2. Create knowledge_proposals table
    op.create_table(
        "knowledge_proposals",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("destination", sa.String(length=32), nullable=False, server_default="create"),
        sa.Column("target_kb_slug", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("summary_quality", sa.String(length=32), nullable=False, server_default="llm"),
        sa.Column("author", sa.String(length=64), nullable=False, server_default="system_ai"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("published_path", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_knowledge_proposals_status",
        "knowledge_proposals",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_proposals_source_type",
        "knowledge_proposals",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_proposals_source_id",
        "knowledge_proposals",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_proposals_created_at",
        "knowledge_proposals",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_kb_proposals_status_updated",
        "knowledge_proposals",
        ["status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_kb_proposals_source",
        "knowledge_proposals",
        ["source_type", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("knowledge_proposals")
    op.drop_table("technician_chat_messages")
