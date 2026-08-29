"""Service composition root.

Constructs the application service layer from a database (persistent) or
from in-memory backends (tests/demo), plus an object store for binary files.
The API layer consumes this ready-made set of services and never assembles
repositories or stores itself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from rescs.db.bootstrap import Database
from rescs.interfaces.object_store import ObjectStore
from rescs.repositories.memory import (
    InMemoryFileObjectRepository,
    InMemoryRecordRepository,
)
from rescs.repositories.sqlalchemy_ import (
    SQLAlchemyFileObjectRepository,
    SQLAlchemyRecordRepository,
)
from rescs.services.files import FileService
from rescs.services.records import RecordService
from rescs.storage.local import LocalObjectStore
from rescs.storage.memory import MemoryObjectStore

DEFAULT_STORAGE_DIR = "rescs_storage"


@dataclass
class Services:
    records: RecordService
    files: FileService


def _default_object_store(use_memory: bool, storage_dir: str | None) -> ObjectStore:
    if use_memory:
        return MemoryObjectStore()
    return LocalObjectStore(storage_dir or DEFAULT_STORAGE_DIR)


def build_services(
    *,
    database: Database | None = None,
    use_memory: bool = False,
    object_store: ObjectStore | None = None,
    storage_dir: str | os.PathLike[str] | None = None,
) -> Services:
    """Build the service layer.

    :param database: persistent backend (engine + session factory).
    :param use_memory: when true (or when ``database`` is None) use the
        in-memory repositories.
    :param object_store: explicit object store; defaults to the in-memory
        store for the memory backend and the local filesystem store for the
        database backend.
    :param storage_dir: base directory for the default local object store.
    """
    if database is None or use_memory:
        records = RecordService(InMemoryRecordRepository())
        files = FileService(
            InMemoryFileObjectRepository(),
            object_store or MemoryObjectStore(),
        )
    else:
        if object_store is None:
            object_store = LocalObjectStore(
                str(storage_dir or DEFAULT_STORAGE_DIR)
            )
        records = RecordService(SQLAlchemyRecordRepository(database.session_factory))
        files = FileService(
            SQLAlchemyFileObjectRepository(database.session_factory),
            object_store,
        )
    return Services(records=records, files=files)