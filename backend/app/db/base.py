from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


class SchemaBootstrap(Base):
    """Minimal bootstrap table to verify schema initialization and SQLite persistence."""

    __tablename__ = "schema_bootstrap"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    initialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
