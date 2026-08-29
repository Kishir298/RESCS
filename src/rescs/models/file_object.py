"""SQLAlchemy model for stored file objects (metadata; blobs in object store)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from rescs.db.base import Base
from rescs.domain import FileObjectData, ensure_utc, utcnow


class FileObject(Base):
    __tablename__ = "file_objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    owner: Mapped[str] = mapped_column(String(256), nullable=False, default="system")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True
    )
    etag: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def to_domain(self) -> FileObjectData:
        return FileObjectData(
            id=self.id,
            filename=self.filename,
            mime_type=self.mime_type,
            size=self.size,
            storage_path=self.storage_path,
            sha256=self.sha256,
            metadata=self.meta or {},
            owner=self.owner,
            version=self.version,
            idempotency_key=self.idempotency_key,
            etag=self.etag,
            created_at=ensure_utc(self.created_at),
            updated_at=ensure_utc(self.updated_at),
        )

    @classmethod
    def from_domain(cls, data: FileObjectData) -> FileObject:
        return cls(
            id=data.id,
            filename=data.filename,
            mime_type=data.mime_type,
            size=data.size,
            storage_path=data.storage_path,
            sha256=data.sha256,
            meta=data.metadata,
            owner=data.owner,
            version=data.version,
            idempotency_key=data.idempotency_key,
            etag=data.etag,
            created_at=ensure_utc(data.created_at),
            updated_at=ensure_utc(data.updated_at),
        )