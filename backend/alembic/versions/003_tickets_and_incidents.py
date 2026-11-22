"""Add tickets, ticket_activities, and incidents tables.

Revision ID: 003_tickets_and_incidents
Revises: 002_agent_phase_and_metadata
Create Date: 2026-11-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_tickets_and_incidents"
down_revision: Union[str, None] = "002_agent_phase_and_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="investigating"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incidents_service", "incidents", ["service"], unique=False)
    op.create_index("ix_incidents_status", "incidents", ["status"], unique=False)
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"], unique=False)

    # 2. Create tickets table
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column(
            "support_request_id",
            sa.String(length=32),
            sa.ForeignKey("support_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=32),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "incident_id",
            sa.String(length=32),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("attempted_steps", sa.Text(), nullable=False),
        sa.Column("diagnostic_findings", sa.Text(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=True),
        sa.Column("summary_quality", sa.String(length=32), nullable=False, server_default="llm"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tickets_support_request_id", "tickets", ["support_request_id"], unique=False)
    op.create_index("ix_tickets_conversation_id", "tickets", ["conversation_id"], unique=False)
    op.create_index("ix_tickets_incident_id", "tickets", ["incident_id"], unique=False)
    op.create_index("ix_tickets_status", "tickets", ["status"], unique=False)
    op.create_index("ix_tickets_priority", "tickets", ["priority"], unique=False)
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"], unique=False)
    op.create_index("ix_tickets_req_status", "tickets", ["support_request_id", "status"], unique=False)
    op.create_index("ix_tickets_conv_created", "tickets", ["conversation_id", "created_at"], unique=False)

    # 3. Create ticket_activities table
    op.create_table(
        "ticket_activities",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column(
            "ticket_id",
            sa.String(length=32),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author", sa.String(length=64), nullable=False, server_default="technician_demo"),
        sa.Column("author_role", sa.String(length=32), nullable=False, server_default="technician"),
        sa.Column("activity_type", sa.String(length=32), nullable=False, server_default="note"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ticket_activities_ticket_id", "ticket_activities", ["ticket_id"], unique=False)
    op.create_index("ix_ticket_activities_activity_type", "ticket_activities", ["activity_type"], unique=False)
    op.create_index("ix_ticket_activities_created_at", "ticket_activities", ["created_at"], unique=False)
    op.create_index(
        "ix_ticket_activities_ticket_created",
        "ticket_activities",
        ["ticket_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("ticket_activities")
    op.drop_table("tickets")
    op.drop_table("incidents")
