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
import re

from rescs.errors import InvalidRequestError

T = TypeVar("T")

MAX_TAGS = 32
MAX_TAG_LENGTH = 64
_TAG_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def normalize_tags(tags: list[str] | tuple[str, ...] | None) -> list[str]:
    """Deduplicate (order-preserving) a tag list; validation lives in schemas."""
    if not tags:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            normalized.append(tag)
    return normalized


def validate_tags(tags: list[str]) -> None:
    """Enforce tag count/length/character constraints (raises ValueError)."""
    if len(tags) > MAX_TAGS:
        raise InvalidRequestError(
            f"at most {MAX_TAGS} tags are allowed",
            details={"count": len(tags), "max": MAX_TAGS},
        )
    for tag in tags:
        if not tag or len(tag) > MAX_TAG_LENGTH or not _TAG_PATTERN.match(tag):
            raise InvalidRequestError(
                f"invalid tag {tag!r}; 1-{MAX_TAG_LENGTH} chars of "
                "[A-Za-z0-9._-] expected",
                details={"tag": tag},
            )


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
    tags: list[str] = field(default_factory=list)
    expires_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def is_expired(self, at: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return ensure_utc(self.expires_at) <= (at or utcnow())

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
            "tags": list(self.tags),
            "expires_at": ensure_utc(self.expires_at),
            "deleted_at": ensure_utc(self.deleted_at),
            "deleted_by": self.deleted_by,
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
    tags: list[str] = field(default_factory=list)
    expires_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def is_expired(self, at: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return ensure_utc(self.expires_at) <= (at or utcnow())

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
            "tags": list(self.tags),
            "expires_at": ensure_utc(self.expires_at),
            "deleted_at": ensure_utc(self.deleted_at),
            "deleted_by": self.deleted_by,
        }


@dataclass
class Page(Generic[T]):
    """A page of items plus the total matching count for pagination."""

    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass
class AuditData:
    """A persistent audit event.

    Deliberately narrow: who did what to which resource, when, with what
    outcome. Never carries secrets, record values, or file bytes.
    """

    id: str
    timestamp: datetime = field(default_factory=utcnow)
    operation: str = ""
    resource_type: str = ""
    resource_id: str | None = None
    owner: str = "system"
    request_id: str | None = None
    outcome: str = "ok"
    error_code: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": ensure_utc(self.timestamp),
            "operation": self.operation,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "owner": self.owner,
            "request_id": self.request_id,
            "outcome": self.outcome,
            "error_code": self.error_code,
        }