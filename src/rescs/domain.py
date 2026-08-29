"""Domain objects used across the storage layers.

Domain objects are plain dataclasses and deliberately independent of
SQLAlchemy, Pydantic and FastAPI. Repository implementations and API schemas
convert to and from these shapes, which keeps the layers decoupled and lets
the in-memory test backend stay free of database dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, TypeVar

T = TypeVar("T")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Return a timezone-aware UTC datetime, assuming UTC for naive input."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass
class RecordData:
    id: str
    namespace: str
    key: str
    value: dict
    metadata: dict = field(default_factory=dict)
    owner: str = "system"
    version: int = 1
    idempotency_key: str | None = None
    etag: str = ""
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "namespace": self.namespace,
            "key": self.key,
            "value": self.value,
            "metadata": self.metadata,
            "owner": self.owner,
            "version": self.version,
            "idempotency_key": self.idempotency_key,
            "etag": self.etag,
            "created_at": ensure_utc(self.created_at),
            "updated_at": ensure_utc(self.updated_at),
        }


@dataclass
class FileObjectData:
    id: str
    filename: str
    mime_type: str
    size: int
    storage_path: str
    sha256: str
    metadata: dict = field(default_factory=dict)
    owner: str = "system"
    version: int = 1
    idempotency_key: str | None = None
    etag: str = ""
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size": self.size,
            "storage_path": self.storage_path,
            "sha256": self.sha256,
            "metadata": self.metadata,
            "owner": self.owner,
            "version": self.version,
            "idempotency_key": self.idempotency_key,
            "etag": self.etag,
            "created_at": ensure_utc(self.created_at),
            "updated_at": ensure_utc(self.updated_at),
        }


@dataclass
class Page(Generic[T]):
    """A page of items plus the total matching count for pagination."""

    items: list[T]
    total: int
    limit: int
    offset: int