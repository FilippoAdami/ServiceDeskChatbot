from __future__ import annotations

import logging
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings
from backend.app.db.base import Base, SchemaBootstrap

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


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


def init_db(engine: Optional[Engine] = None) -> None:
    """Initialize database schema and ensure bootstrap entry exists."""
    eng = engine or get_engine()
    settings = get_settings()

    # Create tables if not present
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
