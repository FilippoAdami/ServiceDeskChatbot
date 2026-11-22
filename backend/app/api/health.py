from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import Settings, get_settings
from backend.app.db.session import check_db_connection, get_db

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Typed schema for system health and status check."""

    status: str = Field(description="Overall service status ('ok' or 'error')")
    database: str = Field(description="Database connectivity status ('connected' or 'disconnected')")
    timestamp: datetime = Field(description="Current UTC timestamp in ISO 8601 format")
    version: str = Field(description="Backend application version")
    environment: str = Field(description="Runtime environment name")
    gemini_configured: bool = Field(
        default=False,
        description="Whether Gemini API key is configured in backend",
    )
    detail: Optional[str] = Field(default=None, description="Optional diagnostic details")


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        200: {"description": "Service and database are healthy"},
        503: {"description": "Database or service connection failure", "model": HealthResponse},
    },
    summary="System and Database Health Check",
)
def get_health(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Check API, database connectivity, and AI provider readiness.

    Returns HTTP 200 when database and service are responsive.
    Returns HTTP 503 if database connection fails.
    """
    now_utc = datetime.now(timezone.utc)
    db_ok = check_db_connection()
    gemini_ok = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="error",
            database="disconnected",
            timestamp=now_utc,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            gemini_configured=gemini_ok,
            detail="Database connection check failed",
        )

    return HealthResponse(
        status="ok",
        database="connected",
        timestamp=now_utc,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        gemini_configured=gemini_ok,
        detail=None,
    )
