"""In-memory object store (deterministic test double)."""

from __future__ import annotations

from rescs.errors import StorageError


class MemoryObjectStore:
    """Object store kept in process memory. Data is lost on exit; used by
    tests and demos where a real filesystem/cloud is unnecessary."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def put(self, object_id: str, data: bytes) -> None:
        self._blobs[object_id] = data

    def get(self, object_id: str) -> bytes:
        try:
            return self._blobs[object_id]
        except KeyError:
            raise StorageError(
                "object not found in store", details={"object_id": object_id}
            ) from None

    def delete(self, object_id: str) -> None:
        self._blobs.pop(object_id, None)

    def exists(self, object_id: str) -> bool:
        return object_id in self._blobs