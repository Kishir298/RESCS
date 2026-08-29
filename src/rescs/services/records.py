"""Record storage service: CREATE, READ, UPDATE, DELETE, LIST, SEARCH.

The service is the single entry point used by the API layer. It validates
inputs (done at the schema boundary), performs the operation through a
repository, and returns domain objects. Every predictable failure raises a
domain error; callers never see repository or database exceptions.
"""

from __future__ import annotations

import uuid

from rescs.domain import Page, RecordData, utcnow
from rescs.errors import InvalidRequestError, PreconditionFailedError
from rescs.etag import content_etag
from rescs.interfaces.repository import RecordRepository
from rescs.schemas.record import RecordCreate, RecordUpdate
from rescs.services.utils import clamp_pagination

DEFAULT_LIMIT = 100


def _check_etag(existing: RecordData, expected_etag: str | None) -> None:
    if expected_etag is not None and existing.etag != expected_etag:
        raise PreconditionFailedError(
            "etag does not match current record state",
            details={
                "id": existing.id,
                "expected_etag": expected_etag,
                "current_etag": existing.etag,
                "version": existing.version,
            },
        )


class RecordService:
    def __init__(self, repository: RecordRepository) -> None:
        self._repo = repository

    def create(self, payload: RecordCreate, *, actor: str = "system") -> RecordData:
        if payload.idempotency_key is not None:
            existing = self._repo.find_by_idempotency_key(payload.idempotency_key)
            if existing is not None:
                return existing
        now = utcnow()
        record = RecordData(
            id=str(uuid.uuid4()),
            namespace=payload.namespace,
            key=payload.key,
            value=payload.value,
            metadata=payload.metadata,
            owner=payload.owner,
            version=1,
            idempotency_key=payload.idempotency_key,
            etag=content_etag(payload.value, payload.metadata),
            created_at=now,
            updated_at=now,
        )
        return self._repo.create(record)

    def put(
        self,
        payload: RecordCreate,
        *,
        actor: str = "system",
        expected_etag: str | None = None,
    ) -> RecordData:
        """Create or replace the record identified by (namespace, key)."""
        existing = self._repo.get_by_namespace_key(payload.namespace, payload.key)
        if existing is None:
            if expected_etag is not None:
                raise PreconditionFailedError(
                    "record does not exist; cannot match If-Match",
                    details={"namespace": payload.namespace, "key": payload.key},
                )
            return self.create(payload, actor=actor)
        _check_etag(existing, expected_etag)
        updated = RecordData(
            id=existing.id,
            namespace=payload.namespace,
            key=payload.key,
            value=payload.value,
            metadata=payload.metadata,
            owner=payload.owner,
            version=existing.version + 1,
            idempotency_key=existing.idempotency_key or payload.idempotency_key,
            etag=content_etag(payload.value, payload.metadata),
            created_at=existing.created_at,
            updated_at=utcnow(),
        )
        return self._repo.update(updated)

    def get(self, record_id: str, *, actor: str = "system") -> RecordData:
        return self._repo.get(record_id)

    def update(
        self,
        record_id: str,
        payload: RecordUpdate,
        *,
        actor: str = "system",
        expected_etag: str | None = None,
    ) -> RecordData:
        existing = self._repo.get(record_id)
        _check_etag(existing, expected_etag)
        fields = (
            payload.value,
            payload.metadata,
            payload.namespace,
            payload.key,
        )
        if all(field is None for field in fields):
            raise InvalidRequestError(
                "no fields to update", details={"id": record_id}
            )
        updated = RecordData(
            id=existing.id,
            namespace=payload.namespace if payload.namespace is not None else existing.namespace,
            key=payload.key if payload.key is not None else existing.key,
            value=payload.value if payload.value is not None else existing.value,
            metadata=payload.metadata if payload.metadata is not None else existing.metadata,
            owner=existing.owner,
            version=existing.version + 1,
            idempotency_key=existing.idempotency_key,
            etag=content_etag(
                payload.value if payload.value is not None else existing.value,
                payload.metadata if payload.metadata is not None else existing.metadata,
            ),
            created_at=existing.created_at,
            updated_at=utcnow(),
        )
        return self._repo.update(updated)

    def delete(
        self,
        record_id: str,
        *,
        actor: str = "system",
        expected_etag: str | None = None,
    ) -> None:
        existing = self._repo.get(record_id)
        _check_etag(existing, expected_etag)
        self._repo.delete(record_id)

    def list(
        self,
        actor: str = "system",
        *,
        namespace: str | None = None,
        key_prefix: str | None = None,
        owner: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Page[RecordData]:
        limit, offset = clamp_pagination(limit, offset)
        return self._repo.list(
            namespace=namespace,
            key_prefix=key_prefix,
            owner=owner,
            limit=limit,
            offset=offset,
        )

    def search(
        self,
        actor: str = "system",
        *,
        query: str,
        namespace: str | None = None,
        owner: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Page[RecordData]:
        limit, offset = clamp_pagination(limit, offset)
        return self._repo.search(
            query=query,
            namespace=namespace,
            owner=owner,
            limit=limit,
            offset=offset,
        )