"""Storage abstraction: repository interfaces (protocols).

The service layer depends only on these protocols. Concrete backends
(in-memory, SQLAlchemy) implement them; future backends can too without
touching the application core.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rescs.domain import FileObjectData, Page, RecordData


@runtime_checkable
class RecordRepository(Protocol):
    def create(self, record: RecordData) -> RecordData: ...

    def get(self, record_id: str) -> RecordData: ...

    def get_by_namespace_key(self, namespace: str, key: str) -> RecordData | None: ...

    def update(self, record: RecordData) -> RecordData: ...

    def delete(self, record_id: str) -> None: ...

    def find_by_idempotency_key(self, idempotency_key: str) -> RecordData | None: ...

    def list(
        self,
        namespace: str | None = None,
        key_prefix: str | None = None,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[RecordData]: ...


@runtime_checkable
class FileObjectRepository(Protocol):
    def create(self, file_object: FileObjectData) -> FileObjectData: ...

    def get(self, file_id: str) -> FileObjectData: ...

    def update(self, file_object: FileObjectData) -> FileObjectData: ...

    def delete(self, file_id: str) -> None: ...

    def find_by_idempotency_key(self, idempotency_key: str) -> FileObjectData | None: ...

    def list(
        self,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[FileObjectData]: ...