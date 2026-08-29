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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from rescs.config import Settings
from rescs.db.base import Base
from rescs.main import create_app
from rescs.repositories.memory import (
    InMemoryFileObjectRepository,
    InMemoryRecordRepository,
)
from rescs.repositories.sqlalchemy_ import (
    SQLAlchemyFileObjectRepository,
    SQLAlchemyRecordRepository,
)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture()
def app(settings: Settings):
    return create_app(settings=settings)


@pytest.fixture()
def client(app, settings: Settings):
    with TestClient(
        app, headers={"X-API-Key": settings.api_key}
    ) as test_client:
        yield test_client


SCOPED_API_KEY = "scoped-tenant-key-0123456789abcdef"
SCOPED_OWNER = "tenant-a"


@pytest.fixture()
def scoped_app(settings: Settings):
    scoped_settings = Settings(
        _env_file=None,
        api_key=SCOPED_API_KEY,
        api_key_owner=SCOPED_OWNER,
        database_url="sqlite+pysqlite:///:memory:",
        storage_dir="rescs_test_storage",
        environment="test",
    )
    return create_app(settings=scoped_settings)


@pytest.fixture()
def scoped_client(scoped_app):
    with TestClient(
        scoped_app, headers={"X-API-Key": SCOPED_API_KEY}
    ) as test_client:
        yield test_client


@pytest.fixture()
def memory_record_repo() -> InMemoryRecordRepository:
    return InMemoryRecordRepository()


@pytest.fixture()
def memory_file_repo() -> InMemoryFileObjectRepository:
    return InMemoryFileObjectRepository()


@pytest.fixture()
def sqlite_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def sqlalchemy_record_repo(sqlite_session_factory) -> SQLAlchemyRecordRepository:
    return SQLAlchemyRecordRepository(sqlite_session_factory)


@pytest.fixture()
def sqlalchemy_file_repo(sqlite_session_factory) -> SQLAlchemyFileObjectRepository:
    return SQLAlchemyFileObjectRepository(sqlite_session_factory)