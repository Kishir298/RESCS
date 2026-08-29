"""Service composition root.

Constructs the application service layer from a database (persistent) or
from in-memory backends (tests/demo). The API layer consumes this ready-made
set of services and never assembles repositories itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from rescs.db.bootstrap import Database
from rescs.repositories.memory import InMemoryRecordRepository
from rescs.repositories.sqlalchemy_ import SQLAlchemyRecordRepository
from rescs.services.records import RecordService


@dataclass
class Services:
    records: RecordService

    def __iter__(self):
        yield self.records


def build_services(
    *,
    database: Database | None = None,
    use_memory: bool = False,
) -> Services:
    """Build the service layer.

    :param database: persistent backend (engine + session factory).
    :param use_memory: when true (or when ``database`` is None) use the
        in-memory repositories instead of the database.
    """
    if database is None or use_memory:
        records = RecordService(InMemoryRecordRepository())
    else:
        records = RecordService(SQLAlchemyRecordRepository(database.session_factory))
    return Services(records=records)