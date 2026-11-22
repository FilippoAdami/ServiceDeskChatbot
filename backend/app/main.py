from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.audit import router as audit_router
from backend.app.api.conversations import router as conversations_router
from backend.app.api.health import router as health_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.kb_proposals import router as kb_proposals_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.requests import router as requests_router
from backend.app.api.tech_chat import router as tech_chat_router
from backend.app.api.tickets import router as tickets_router
from backend.app.config import Settings, get_settings
from backend.app.db.session import init_db

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("service_desk.backend")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown tasks."""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.ENVIRONMENT})")

    # Bootstrap SQLite database schema on startup
    try:
        init_db()
        logger.info("Database bootstrap completed successfully")
    except Exception as exc:
        logger.error(f"Failed to bootstrap database on startup: {exc}")

    yield

    logger.info("Shutting down Service Desk Assistant Backend")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        description="Backend API for Service Desk AI Assistant (Local Prototyping)",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Restrict CORS to explicitly configured development origins
    cors_origins = (
        app_settings.CORS_ORIGINS if isinstance(app_settings.CORS_ORIGINS, list) else [app_settings.CORS_ORIGINS]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(health_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(conversations_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(requests_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(knowledge_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(tickets_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(tech_chat_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(kb_proposals_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(incidents_router, prefix=app_settings.API_V1_PREFIX)
    app.include_router(audit_router, prefix=app_settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    def root_info() -> dict[str, str]:
        return {
            "name": app_settings.APP_NAME,
            "version": app_settings.APP_VERSION,
            "docs": "/docs",
            "health": f"{app_settings.API_V1_PREFIX}/health",
        }

    return app


# Default ASGI application instance for uvicorn
app = create_app()
