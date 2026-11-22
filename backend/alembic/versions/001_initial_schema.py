"""Initial schema with conversations, messages, support requests, and audit events.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-21 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ensure schema_bootstrap table exists (from G01)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_bootstrap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component VARCHAR(50) NOT NULL UNIQUE,
            version VARCHAR(20) NOT NULL,
            initialized_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # 2. Create conversations table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id VARCHAR(32) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            title VARCHAR(255),
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_status ON conversations (status)")

    # 3. Create messages table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR(32) PRIMARY KEY,
            conversation_id VARCHAR(32) NOT NULL,
            role VARCHAR(16) NOT NULL DEFAULT 'user',
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_conv_created ON messages (conversation_id, created_at)")

    # 4. Create support_requests table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS support_requests (
            id VARCHAR(32) PRIMARY KEY,
            conversation_id VARCHAR(32) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            initial_category VARCHAR(64),
            final_category VARCHAR(64),
            status VARCHAR(32) NOT NULL DEFAULT 'open',
            outcome VARCHAR(32),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_requests_conversation_id ON support_requests (conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_requests_status ON support_requests (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_support_requests_outcome ON support_requests (outcome)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_requests_conv_created ON support_requests (conversation_id, created_at)")

    # 5. Create audit_events table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id VARCHAR(32) PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL,
            conversation_id VARCHAR(32),
            request_id VARCHAR(32),
            payload JSON NOT NULL DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_event_type ON audit_events (event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_conversation_id ON audit_events (conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_request_id ON audit_events (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_events")
    op.execute("DROP TABLE IF EXISTS support_requests")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversations")
    op.execute("DROP TABLE IF EXISTS schema_bootstrap")
