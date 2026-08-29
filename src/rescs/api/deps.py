"""API dependencies and health-check wiring."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request

from rescs.config import Settings
from rescs.db.engine import check_connectivity
from rescs.logging import get_logger
from rescs.services.factory import Services

logger = get_logger(__name__)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_services(request: Request) -> Services:
    return request.app.state.services


PROBE_KEY = "_rescs_probe"


def _database_check(app: FastAPI) -> str:
    try:
        check_connectivity(app.state.database.engine)
        return "ok"
    except Exception:
        return "down"


def _storage_check(app: FastAPI) -> str:
    try:
        store = app.state.services.files.object_store
        probe = f"{PROBE_KEY}_{uuid.uuid4().hex}"
        store.put(probe, b"ok")
        healthy = store.get(probe) == b"ok"
        store.delete(probe)
        return "ok" if healthy else "down"
    except Exception:
        return "down"


def register_health_checks(app: FastAPI) -> None:
    """Register real dependency probes against the live app state."""
    if hasattr(app.state, "database"):
        app.state.health.register("database", lambda: _database_check(app))
    app.state.health.register("storage", lambda: _storage_check(app))