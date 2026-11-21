from __future__ import annotations

import logging
import sqlite3
from typing import Any, Generator, Optional

from sqlalchemy import Engine, create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings
from backend.app.db.base import Base, SchemaBootstrap

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enforce SQLite foreign key constraints and WAL mode where applicable."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine() -> Engine:
    """Get or create the global SQLAlchemy Engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.DATABASE_URL

        # Ensure parent directory exists for file-based SQLite
        if settings.is_sqlite and ":memory:" not in db_url:
            db_path = settings.sqlite_file_path
            if db_path is not None:
                db_path.parent.mkdir(parents=True, exist_ok=True)

        connect_args = {}
        if settings.is_sqlite:
            # SQLite specific threading configuration
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            echo=settings.DEBUG,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or create the Session factory bound to current engine."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionFactory


def reset_db_session() -> None:
    """Reset global engine and session factory (useful in test suites)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


def check_db_connection(engine: Optional[Engine] = None) -> bool:
    """Execute a simple SELECT 1 to verify database responsiveness."""
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False


def run_migrations(engine: Optional[Engine] = None) -> None:
    """Run Alembic migrations programmatically to head."""
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    eng = engine or get_engine()
    settings = get_settings()

    ini_path = Path(__file__).resolve().parent.parent.parent.parent / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    with eng.connect() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, "head")


def init_db(engine: Optional[Engine] = None) -> None:
    """Initialize database schema, tables, and ensure bootstrap entry exists."""
    import backend.app.db.models  # noqa: F401

    eng = engine or get_engine()
    settings = get_settings()

    try:
        run_migrations(eng)
    except Exception as exc:
        logger.warning(f"Alembic migration skipped or failed ({exc}), applying create_all fallback")
        Base.metadata.create_all(bind=eng)

    # Verify/create bootstrap record
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    with factory() as session:
        existing = session.execute(
            select(SchemaBootstrap).where(SchemaBootstrap.component == "core")
        ).scalar_one_or_none()

        if not existing:
            bootstrap = SchemaBootstrap(
                component="core",
                version=settings.APP_VERSION,
            )
            session.add(bootstrap)
            session.commit()
            logger.info(f"Database schema initialized with version {settings.APP_VERSION}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for obtaining a database session."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()
