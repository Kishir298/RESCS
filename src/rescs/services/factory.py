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
from rescs.config import Settings
from rescs.interfaces.object_store import ObjectStore
from rescs.repositories.memory import (
    InMemoryAuditRepository,
    InMemoryFileObjectRepository,
    InMemoryRecordRepository,
)
from rescs.repositories.sqlalchemy_ import (
    SQLAlchemyAuditRepository,
    SQLAlchemyFileObjectRepository,
    SQLAlchemyRecordRepository,
)
from rescs.services.audit import AuditService
from rescs.services.files import FileService
from rescs.services.records import RecordService
from rescs.storage.local import LocalObjectStore
from rescs.storage.memory import MemoryObjectStore

DEFAULT_STORAGE_DIR = "rescs_storage"


@dataclass
class Services:
    records: RecordService
    files: FileService
    audit: AuditService


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
    settings: Settings | None = None,
) -> Services:
    """Build the service layer.

    :param database: persistent backend (engine + session factory).
    :param use_memory: when true (or when ``database`` is None) use the
        in-memory repositories.
    :param object_store: explicit object store; defaults to the in-memory
        store for the memory backend and the local filesystem store for the
        database backend.
    :param storage_dir: base directory for the default local object store.
    :param settings: runtime settings for quotas/governance (optional).
    """
    if database is None or use_memory:
        shared_audit = AuditService(InMemoryAuditRepository())
        records = RecordService(
            InMemoryRecordRepository(), settings=settings, audit=shared_audit
        )
        files = FileService(
            InMemoryFileObjectRepository(),
            object_store or MemoryObjectStore(),
            settings=settings,
            audit=shared_audit,
        )
        audit = shared_audit
    else:
        if object_store is None:
            object_store = LocalObjectStore(
                str(storage_dir or DEFAULT_STORAGE_DIR)
            )
        audit_service = AuditService(SQLAlchemyAuditRepository(database.session_factory))
        records = RecordService(
            SQLAlchemyRecordRepository(database.session_factory),
            settings=settings,
            audit=audit_service,
        )
        files = FileService(
            SQLAlchemyFileObjectRepository(database.session_factory),
            object_store,
            settings=settings,
            audit=audit_service,
        )
        audit = audit_service
    return Services(records=records, files=files, audit=audit)