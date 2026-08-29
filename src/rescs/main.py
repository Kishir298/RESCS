"""RESCS application factory and HTTP entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rescs.config import Settings, get_settings
from rescs.errors import RESCSError
from rescs.health import HealthService
from rescs.logging import configure_logging, get_logger

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully configured RESCS FastAPI application."""
    if settings is None:
        settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        logger.info(
            "starting %s v%s (%s)",
            settings.app_name,
            settings.version,
            settings.environment,
        )
        yield
        logger.info("%s stopped", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Rishik's Efficient System for Cloud Storage",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.health = HealthService()

    @app.exception_handler(RESCSError)
    async def _domain_error_handler(_request: Request, exc: RESCSError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.to_dict()},
        )

    @app.get("/", tags=["meta"])
    def root() -> dict[str, Any]:
        return {
            "service": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
        }

    @app.get("/health/live", tags=["health"])
    def health_live() -> dict[str, Any]:
        return {
            "status": "alive",
            "service": settings.app_name,
            "version": settings.version,
        }

    @app.get("/health/ready", tags=["health"])
    def health_ready() -> dict[str, Any]:
        report = app.state.health.report()
        return {
            "status": "ready" if report["status"] == "ok" else "not_ready",
            "checks": report["checks"],
        }

    @app.get("/health", tags=["health"])
    def health_summary() -> dict[str, Any]:
        return {
            "service": settings.app_name,
            "version": settings.version,
            **app.state.health.report(),
        }

    return app