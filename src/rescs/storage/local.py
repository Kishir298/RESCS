"""Local filesystem object store.

Stores blobs under ``<base_dir>/<object_id>``. This is the concrete default
backend; the :class:`rescs.interfaces.object_store.ObjectStore` protocol is
the seam where cloud object storage (S3-compatible, Supabase Storage) will
plug in later.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from rescs.errors import StorageError

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class LocalObjectStore:
    def __init__(self, base_dir: str | os.PathLike[str]) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, object_id: str) -> Path:
        if not _SAFE_ID.match(object_id):
            raise StorageError(
                "unsafe object identifier",
                details={"object_id": object_id},
            )
        return self._base / object_id

    def put(self, object_id: str, data: bytes) -> None:
        target = self._resolve(object_id)
        try:
            temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
            temp.write_bytes(data)
            os.replace(temp, target)
        except OSError as exc:
            raise StorageError(
                "failed to write object",
                details={"object_id": object_id, "cause": str(exc)},
            ) from exc

    def get(self, object_id: str) -> bytes:
        target = self._resolve(object_id)
        try:
            return target.read_bytes()
        except OSError as exc:
            raise StorageError(
                "failed to read object",
                details={"object_id": object_id, "cause": str(exc)},
            ) from exc

    def delete(self, object_id: str) -> None:
        target = self._resolve(object_id)
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(
                "failed to delete object",
                details={"object_id": object_id, "cause": str(exc)},
            ) from exc

    def exists(self, object_id: str) -> bool:
        path = self._resolve(object_id)
        return path.is_file()