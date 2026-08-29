"""Health endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health/live")
def health_live(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "status": "alive",
        "service": settings.app_name,
        "version": settings.version,
    }


@router.get("/health/ready")
def health_ready(request: Request) -> dict[str, Any]:
    report = request.app.state.health.report()
    return {
        "status": "ready" if report["status"] == "ok" else "not_ready",
        "checks": report["checks"],
    }


@router.get("/health")
def health_summary(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "service": settings.app_name,
        "version": settings.version,
        **request.app.state.health.report(),
    }