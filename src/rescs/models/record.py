"""SQLAlchemy model for stored records (JSON-value storage cells)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from rescs.db.base import Base
from rescs.domain import RecordData, ensure_utc, utcnow


class Record(Base):
    __tablename__ = "records"
    __table_args__ = (
        UniqueConstraint("namespace", "key", name="uq_records_namespace_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
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

    def to_domain(self) -> RecordData:
        return RecordData(
            id=self.id,
            namespace=self.namespace,
            key=self.key,
            value=self.value,
            metadata=self.meta or {},
            owner=self.owner,
            version=self.version,
            idempotency_key=self.idempotency_key,
            etag=self.etag,
            created_at=ensure_utc(self.created_at),
            updated_at=ensure_utc(self.updated_at),
        )

    @classmethod
    def from_domain(cls, data: RecordData) -> Record:
        return cls(
            id=data.id,
            namespace=data.namespace,
            key=data.key,
            value=data.value,
            meta=data.metadata,
            owner=data.owner,
            version=data.version,
            idempotency_key=data.idempotency_key,
            etag=data.etag,
            created_at=ensure_utc(data.created_at),
            updated_at=ensure_utc(data.updated_at),
        )