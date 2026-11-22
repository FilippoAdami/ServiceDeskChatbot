from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.config import Settings


def test_default_settings() -> None:
    """Verify default settings values and optional Gemini API key."""
    settings = Settings(GEMINI_API_KEY=None)
    assert settings.APP_NAME == "Service Desk AI Assistant"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.GEMINI_API_KEY is None
    assert settings.is_sqlite is True
    assert "service_desk.db" in settings.DATABASE_URL
    assert len(settings.CORS_ORIGINS) >= 1


def test_cors_origins_parsing_from_string() -> None:
    """Verify comma-separated CORS_ORIGINS string is parsed into a list."""
    settings = Settings(CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:5173")
    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_invalid_database_url_scheme() -> None:
    """Verify invalid database URL scheme triggers clear ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(DATABASE_URL="mysql://root:pass@localhost/db")
    assert "Unsupported database scheme" in str(exc_info.value)


def test_empty_database_url() -> None:
    """Verify empty database URL triggers ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(DATABASE_URL="   ")
    assert "DATABASE_URL cannot be empty" in str(exc_info.value)


def test_empty_cors_origins_string() -> None:
    """Verify empty CORS origins string triggers ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(CORS_ORIGINS="")
    assert "CORS_ORIGINS cannot be empty" in str(exc_info.value)
