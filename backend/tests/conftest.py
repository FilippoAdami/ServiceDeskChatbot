from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.config import Settings, reset_settings_for_test
from backend.app.db.session import init_db, reset_db_session
from backend.app.main import create_app


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database file path."""
    return tmp_path / "test_servicedesk.db"


@pytest.fixture
def test_settings(temp_db_path: Path) -> Generator[Settings, None, None]:
    """Fixture providing isolated Settings pointing to a temporary SQLite database."""
    settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL=f"sqlite:///{temp_db_path}",
        CORS_ORIGINS=["http://testserver", "http://localhost:5173"],
        DEBUG=True,
    )
    reset_settings_for_test(settings)
    reset_db_session()
    yield settings
    reset_db_session()
    reset_settings_for_test(None)


@pytest.fixture
def db_session(test_settings: Settings) -> Generator[Session, None, None]:
    """Provide an initialized database session for unit testing."""
    from backend.app.db.session import get_session_factory

    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """TestClient fixture with bootstrapped database."""
    init_db()
    app = create_app(settings=test_settings)
    with TestClient(app) as test_client:
        yield test_client
