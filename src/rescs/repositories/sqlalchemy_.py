"""SQLAlchemy repository backends.

Persistent implementations of the repository protocols on top of a session
factory. Every operation runs through :func:`rescs.db.session.session_scope`,
which provides transaction handling and converts raw database failures into
domain errors.
"""

from __future__ import annotations

from rescs.db.session import SessionFactory, session_scope
from rescs.domain import FileObjectData, Page, RecordData
from rescs.errors import ConflictError, NotFoundError
from rescs.models import FileObject, Record


class SQLAlchemyRecordRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create(self, record: RecordData) -> RecordData:
        with session_scope(
            self._session_factory,
            "create record",
            conflict=lambda: self._conflict(record),
        ) as session:
            if session.get(Record, record.id) is not None:
                raise ConflictError("record already exists", details={"id": record.id})
            session.add(Record.from_domain(record))
        return record

    def get(self, record_id: str) -> RecordData:
        with session_scope(self._session_factory, "get record") as session:
            row = session.get(Record, record_id)
            if row is None:
                raise NotFoundError("record not found", details={"id": record_id})
            return row.to_domain()

    def get_by_namespace_key(self, namespace: str, key: str) -> RecordData | None:
        with session_scope(self._session_factory, "get record by namespace/key") as session:
            row = (
                session.query(Record)
                .filter(Record.namespace == namespace, Record.key == key)
                .first()
            )
            return row.to_domain() if row is not None else None

    def update(self, record: RecordData) -> RecordData:
        with session_scope(
            self._session_factory,
            "update record",
            conflict=lambda: self._conflict(record),
        ) as session:
            row = session.get(Record, record.id)
            if row is None:
                raise NotFoundError("record not found", details={"id": record.id})
            row.namespace = record.namespace
            row.key = record.key
            row.value = record.value
            row.meta = record.metadata
            row.owner = record.owner
            row.version = record.version
            row.idempotency_key = record.idempotency_key
            row.etag = record.etag
            row.updated_at = record.updated_at
        return record

    def delete(self, record_id: str) -> None:
        with session_scope(self._session_factory, "delete record") as session:
            row = session.get(Record, record_id)
            if row is None:
                raise NotFoundError("record not found", details={"id": record_id})
            session.delete(row)

    def find_by_idempotency_key(self, idempotency_key: str) -> RecordData | None:
        with session_scope(self._session_factory, "find record by idempotency key") as session:
            row = (
                session.query(Record)
                .filter(Record.idempotency_key == idempotency_key)
                .first()
            )
            return row.to_domain() if row is not None else None

    def list(
        self,
        namespace: str | None = None,
        key_prefix: str | None = None,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[RecordData]:
        with session_scope(self._session_factory, "list records") as session:
            query = session.query(Record)
            if namespace is not None:
                query = query.filter(Record.namespace == namespace)
            if key_prefix is not None:
                query = query.filter(Record.key.startswith(key_prefix))
            if owner is not None:
                query = query.filter(Record.owner == owner)
            total = query.count()
            rows = (
                query.order_by(Record.updated_at.asc(), Record.id.asc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            items = [row.to_domain() for row in rows]
            return Page(items=items, total=total, limit=limit, offset=offset)

    @staticmethod
    def _conflict(record: RecordData) -> ConflictError:
        return ConflictError(
            "a record with the same id, namespace/key, or idempotency key "
            "already exists",
            details={
                "id": record.id,
                "namespace": record.namespace,
                "key": record.key,
                "idempotency_key": record.idempotency_key,
            },
        )


class SQLAlchemyFileObjectRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create(self, file_object: FileObjectData) -> FileObjectData:
        with session_scope(
            self._session_factory,
            "create file object",
            conflict=lambda: self._conflict(file_object),
        ) as session:
            if session.get(FileObject, file_object.id) is not None:
                raise ConflictError(
                    "file object already exists", details={"id": file_object.id}
                )
            session.add(FileObject.from_domain(file_object))
        return file_object

    def get(self, file_id: str) -> FileObjectData:
        with session_scope(self._session_factory, "get file object") as session:
            row = session.get(FileObject, file_id)
            if row is None:
                raise NotFoundError("file not found", details={"id": file_id})
            return row.to_domain()

    def update(self, file_object: FileObjectData) -> FileObjectData:
        with session_scope(
            self._session_factory,
            "update file object",
            conflict=lambda: self._conflict(file_object),
        ) as session:
            row = session.get(FileObject, file_object.id)
            if row is None:
                raise NotFoundError("file not found", details={"id": file_object.id})
            row.filename = file_object.filename
            row.mime_type = file_object.mime_type
            row.size = file_object.size
            row.storage_path = file_object.storage_path
            row.sha256 = file_object.sha256
            row.meta = file_object.metadata
            row.owner = file_object.owner
            row.version = file_object.version
            row.idempotency_key = file_object.idempotency_key
            row.etag = file_object.etag
            row.updated_at = file_object.updated_at
        return file_object

    def delete(self, file_id: str) -> None:
        with session_scope(self._session_factory, "delete file object") as session:
            row = session.get(FileObject, file_id)
            if row is None:
                raise NotFoundError("file not found", details={"id": file_id})
            session.delete(row)

    def find_by_idempotency_key(self, idempotency_key: str) -> FileObjectData | None:
        with session_scope(self._session_factory, "find file by idempotency key") as session:
            row = (
                session.query(FileObject)
                .filter(FileObject.idempotency_key == idempotency_key)
                .first()
            )
            return row.to_domain() if row is not None else None

    def list(
        self,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[FileObjectData]:
        with session_scope(self._session_factory, "list file objects") as session:
            query = session.query(FileObject)
            if owner is not None:
                query = query.filter(FileObject.owner == owner)
            total = query.count()
            rows = (
                query.order_by(FileObject.updated_at.asc(), FileObject.id.asc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            items = [row.to_domain() for row in rows]
            return Page(items=items, total=total, limit=limit, offset=offset)

    @staticmethod
    def _conflict(file_object: FileObjectData) -> ConflictError:
        return ConflictError(
            "a file with the same id or idempotency key already exists",
            details={"id": file_object.id, "idempotency_key": file_object.idempotency_key},
        )