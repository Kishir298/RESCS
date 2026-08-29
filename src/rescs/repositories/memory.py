"""In-memory repository backends.

Deterministic, dependency-free implementations used by unit tests and as the
reference behaviour for the repository protocol. Data is lost on process
exit; they are never used for real persistence.
"""

from __future__ import annotations

import threading
from typing import Generic, TypeVar

from rescs.domain import FileObjectData, Page, RecordData
from rescs.errors import ConflictError, NotFoundError

T = TypeVar("T", RecordData, FileObjectData)


class _InMemoryStore(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._namespace_keys: dict[tuple[str, str], str] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = threading.RLock()

    def create(self, item: T, namespace: str | None = None, key: str | None = None) -> T:
        with self._lock:
            if item.id in self._items:
                raise ConflictError("item already exists", details={"id": item.id})
            if namespace is not None and key is not None:
                natural = (namespace, key)
                if natural in self._namespace_keys:
                    raise ConflictError(
                        "item already exists for namespace/key",
                        details={"namespace": namespace, "key": key},
                    )
            if item.idempotency_key and item.idempotency_key in self._idempotency:
                raise ConflictError(
                    "idempotency key already used",
                    details={"idempotency_key": item.idempotency_key},
                )
            self._items[item.id] = item
            if namespace is not None and key is not None:
                self._namespace_keys[(namespace, key)] = item.id
            if item.idempotency_key:
                self._idempotency[item.idempotency_key] = item.id
            return item

    def update(self, item: T, namespace: str | None = None, key: str | None = None) -> T:
        with self._lock:
            if item.id not in self._items:
                raise NotFoundError("item not found", details={"id": item.id})
            self._items[item.id] = item
            if namespace is not None and key is not None:
                for k, existing_id in list(self._namespace_keys.items()):
                    if existing_id == item.id and k != (namespace, key):
                        del self._namespace_keys[k]
                self._namespace_keys[(namespace, key)] = item.id
            if item.idempotency_key:
                old = self._idempotency.get(item.idempotency_key)
                if old is not None and old != item.id:
                    raise ConflictError(
                        "idempotency key already used",
                        details={"idempotency_key": item.idempotency_key},
                    )
                self._idempotency[item.idempotency_key] = item.id
            return item

    def delete(self, item_id: str) -> None:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                raise NotFoundError("item not found", details={"id": item_id})
            self._namespace_keys = {
                k: v for k, v in self._namespace_keys.items() if v != item_id
            }
            self._idempotency = {
                k: v for k, v in self._idempotency.items() if v != item_id
            }
            del self._items[item_id]

    def get(self, item_id: str) -> T:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                raise NotFoundError("item not found", details={"id": item_id})
            return item

    def get_by_natural_key(self, namespace: str, key: str) -> T | None:
        with self._lock:
            item_id = self._namespace_keys.get((namespace, key))
            if item_id is None:
                return None
            return self._items[item_id]

    def find_by_idempotency_key(self, idempotency_key: str) -> T | None:
        with self._lock:
            item_id = self._idempotency.get(idempotency_key)
            if item_id is None:
                return None
            return self._items[item_id]

    def page(
        self,
        predicate,
        limit: int,
        offset: int,
    ) -> list[T]:
        with self._lock:
            items = [item for item in self._items.values() if predicate(item)]
            items.sort(key=lambda i: (i.updated_at, i.id))
            return items[offset : offset + limit]

    def count(self, predicate) -> int:
        with self._lock:
            return sum(1 for item in self._items.values() if predicate(item))


class InMemoryRecordRepository:
    def __init__(self) -> None:
        self._store: _InMemoryStore[RecordData] = _InMemoryStore()

    def create(self, record: RecordData) -> RecordData:
        return self._store.create(record, record.namespace, record.key)

    def get(self, record_id: str) -> RecordData:
        return self._store.get(record_id)

    def get_by_namespace_key(self, namespace: str, key: str) -> RecordData | None:
        return self._store.get_by_natural_key(namespace, key)

    def update(self, record: RecordData) -> RecordData:
        return self._store.update(record, record.namespace, record.key)

    def delete(self, record_id: str) -> None:
        self._store.delete(record_id)

    def find_by_idempotency_key(self, idempotency_key: str) -> RecordData | None:
        return self._store.find_by_idempotency_key(idempotency_key)

    def list(
        self,
        namespace: str | None = None,
        key_prefix: str | None = None,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[RecordData]:
        predicate = lambda r: (
            (namespace is None or r.namespace == namespace)
            and (key_prefix is None or r.key.startswith(key_prefix))
            and (owner is None or r.owner == owner)
        )
        items = self._store.page(predicate, limit, offset)
        return Page(
            items=items, total=self._store.count(predicate), limit=limit, offset=offset
        )


class InMemoryFileObjectRepository:
    def __init__(self) -> None:
        self._store: _InMemoryStore[FileObjectData] = _InMemoryStore()

    def create(self, file_object: FileObjectData) -> FileObjectData:
        return self._store.create(file_object)

    def get(self, file_id: str) -> FileObjectData:
        return self._store.get(file_id)

    def update(self, file_object: FileObjectData) -> FileObjectData:
        return self._store.update(file_object)

    def delete(self, file_id: str) -> None:
        self._store.delete(file_id)

    def find_by_idempotency_key(self, idempotency_key: str) -> FileObjectData | None:
        return self._store.find_by_idempotency_key(idempotency_key)

    def list(
        self,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[FileObjectData]:
        predicate = lambda f: owner is None or f.owner == owner
        items = self._store.page(predicate, limit, offset)
        return Page(
            items=items, total=self._store.count(predicate), limit=limit, offset=offset
        )