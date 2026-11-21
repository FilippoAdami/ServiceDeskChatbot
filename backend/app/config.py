from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration for Service Desk AI Assistant.

    Separates secrets, URLs, and runtime parameters from application code.
    Gemini API key is optional for G01 (not required for starting or tests).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "Service Desk AI Assistant"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment (development, test, production)",
    )
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API and CORS
    API_V1_PREFIX: str = "/api"
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        description="Allowed CORS origins for local development",
    )

    # Persistence / Database
    DATABASE_URL: str = Field(
        default="sqlite:///./data/service_desk.db",
        description="SQLAlchemy database URL (defaults to persistent local SQLite file)",
    )

    # LLM Settings (optional in G01, required in future goals)
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API Key (optional for G01; server will not crash if missing)",
    )
    GEMINI_TRIAGE_MODEL: str = "gemini-2.5-flash"
    GEMINI_DIAGNOSIS_MODEL: str = "gemini-2.5-flash"
    GEMINI_FINALIZATION_MODEL: str = "gemini-2.5-flash"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Parse comma-separated string if provided via env var
            origins = [item.strip() for item in v.split(",") if item.strip()]
            if not origins:
                raise ValueError("CORS_ORIGINS cannot be empty when provided as string")
            return origins
        if isinstance(v, list):
            if not v:
                raise ValueError("CORS_ORIGINS list cannot be empty")
            return v
        raise ValueError("Invalid format for CORS_ORIGINS")

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("DATABASE_URL cannot be empty")
        valid_prefixes = ("sqlite:///", "sqlite+pysqlite:///", "postgresql://", "postgresql+psycopg2://")
        if not any(v_stripped.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"Unsupported database scheme in DATABASE_URL: '{v_stripped}'. "
                f"Must start with one of {valid_prefixes}"
            )
        return v_stripped

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def sqlite_file_path(self) -> Optional[Path]:
        if not self.is_sqlite or ":memory:" in self.DATABASE_URL:
            return None
        # sqlite:///./data/service_desk.db -> ./data/service_desk.db
        path_str = self.DATABASE_URL.replace("sqlite:///", "")
        return Path(path_str).resolve()


# Singleton factory pattern for settings
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings_for_test(new_settings: Optional[Settings] = None) -> None:
    """Helper to reset or inject custom settings in test fixtures."""
    global _settings_instance
    _settings_instance = new_settings
