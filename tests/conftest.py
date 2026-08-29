"""Shared test fixtures.

Environment variables are set at module import time, before any
:class:`rescs.config.Settings` is instantiated, so tests are hermetic.
"""

from __future__ import annotations

import os

os.environ.setdefault("RESCS_API_KEY", "test-api-key-0123456789abcdef")
os.environ.setdefault("RESCS_ENV", "test")
os.environ.setdefault("RESCS_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("RESCS_STORAGE_DIR", "rescs_test_storage")
os.environ.setdefault("RESCS_LOG_LEVEL", "WARNING")

import pytest
from fastapi.testclient import TestClient

from rescs.config import Settings
from rescs.main import create_app


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture()
def app(settings: Settings):
    return create_app(settings=settings)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client