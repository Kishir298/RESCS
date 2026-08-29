"""File storage service.

Stores binary content (blob) in an object store and its descriptive
metadata (filename, MIME type, size, SHA-256, etag, timestamps) in the
record-keeping repository. Metadata and bytes are deliberately separate, so
large payloads never live inside database rows.
"""

from __future__ import annotations

import hashlib
import uuid

from rescs.domain import FileObjectData, Page, utcnow
from rescs.errors import PreconditionFailedError, StorageError
from rescs.etag import file_etag
from rescs.interfaces.object_store import ObjectStore
from rescs.interfaces.repository import FileObjectRepository
from rescs.logging import get_logger
from rescs.schemas.file_object import FileObjectCreate
from rescs.services.utils import clamp_pagination

logger = get_logger(__name__)

DEFAULT_LIMIT = 100


class FileService:
    def __init__(
        self,
        repository: FileObjectRepository,
        object_store: ObjectStore,
    ) -> None:
        self._repo = repository
        self._store = object_store

    @property
    def object_store(self) -> ObjectStore:
        return self._store

    def create(
        self,
        payload: FileObjectCreate,
        data: bytes,
        *,
        actor: str = "system",
    ) -> FileObjectData:
        if payload.idempotency_key is not None:
            existing = self._repo.find_by_idempotency_key(payload.idempotency_key)
            if existing is not None:
                return existing

        digest = hashlib.sha256(data).hexdigest()
        size = len(data)
        now = utcnow()
        file_id = str(uuid.uuid4())

        self._store.put(file_id, data)

        file_object = FileObjectData(
            id=file_id,
            filename=payload.filename,
            mime_type=payload.mime_type,
            size=size,
            storage_path=file_id,
            sha256=digest,
            metadata=payload.metadata,
            owner=payload.owner,
            version=1,
            idempotency_key=payload.idempotency_key,
            etag=file_etag(digest, size),
            created_at=now,
            updated_at=now,
        )
        try:
            return self._repo.create(file_object)
        except Exception:
            self._store.delete(file_id)
            raise

    def get(self, file_id: str, *, actor: str = "system") -> FileObjectData:
        return self._repo.get(file_id)

    def download(
        self, file_id: str, *, actor: str = "system", verify: bool = True
    ) -> tuple[FileObjectData, bytes]:
        file_object = self._repo.get(file_id)
        data = self._store.get(file_object.storage_path)
        if verify:
            actual = hashlib.sha256(data).hexdigest()
            if actual != file_object.sha256:
                raise StorageError(
                    "blob integrity check failed; stored bytes do not match metadata",
                    details={
                        "id": file_id,
                        "expected_sha256": file_object.sha256,
                        "actual_sha256": actual,
                    },
                )
        return file_object, data

    def delete(
        self,
        file_id: str,
        *,
        actor: str = "system",
        expected_etag: str | None = None,
    ) -> None:
        file_object = self._repo.get(file_id)
        if expected_etag is not None and file_object.etag != expected_etag:
            raise PreconditionFailedError(
                "etag does not match current file state",
                details={
                    "id": file_id,
                    "expected_etag": expected_etag,
                    "current_etag": file_object.etag,
                    "version": file_object.version,
                },
            )
        self._repo.delete(file_id)
        try:
            self._store.delete(file_id)
        except Exception:
            logger.warning(
                "blob cleanup failed for file %s (metadata already removed)", file_id
            )

    def list(
        self,
        actor: str = "system",
        *,
        owner: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Page[FileObjectData]:
        limit, offset = clamp_pagination(limit, offset)
        return self._repo.list(owner=owner, limit=limit, offset=offset)