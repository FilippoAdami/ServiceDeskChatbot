"""Add agent phase and escalation to support_requests and metadata_json to messages.

Revision ID: 002_agent_phase_and_metadata
Revises: 001_initial_schema
Create Date: 2026-11-21 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_agent_phase_and_metadata"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update support_requests table
    with op.batch_alter_table("support_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("phase", sa.String(length=32), nullable=False, server_default="triage"))
        batch_op.add_column(sa.Column("escalation_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_support_requests_phase", ["phase"], unique=False)
        batch_op.create_index("ix_support_requests_escalation_requested", ["escalation_requested"], unique=False)

    # 2. Update messages table
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    # 1. Revert messages table
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("metadata_json")

    # 2. Revert support_requests table
    with op.batch_alter_table("support_requests", schema=None) as batch_op:
        batch_op.drop_index("ix_support_requests_escalation_requested")
        batch_op.drop_index("ix_support_requests_phase")
        batch_op.drop_column("escalation_requested")
        batch_op.drop_column("phase")
