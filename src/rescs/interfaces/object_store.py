"""Storage abstraction: object store interface (binary blobs)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStore(Protocol):
    """Binary object storage. Backends: local filesystem (now), cloud object
    storage (future: S3-compatible, Supabase Storage, ...)."""

    def put(self, object_id: str, data: bytes) -> None: ...

    def get(self, object_id: str) -> bytes: ...

    def delete(self, object_id: str) -> None: ...

    def exists(self, object_id: str) -> bool: ...