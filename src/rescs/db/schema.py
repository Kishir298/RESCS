"""Schema creation and lightweight versioned migration."""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text


class SchemaManager:
    """Ensure the application schema exists and track its version.

    Table DDL is derived from the ORM metadata. A ``schema_info`` table
    records the applied schema version; running ``migrate`` repeatedly is
    idempotent. This covers development and lightweight deployments;
    heavily versioned production schemas may adopt a migration tool such as
    Alembic on top of this foundation.
    """

    SCHEMA_VERSION = "0.1.0"

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def migrate(self) -> None:
        import rescs.models  # noqa: F401 - populate ORM metadata

        Base = rescs.models.Base
        Base.metadata.create_all(self._engine)
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_info "
                    "(key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL)"
                )
            )

        with self._engine.begin() as connection:
            existing = connection.execute(
                text("SELECT value FROM schema_info WHERE key = 'version'")
            ).first()
            if existing is None:
                connection.execute(
                    text(
                        "INSERT INTO schema_info (key, value) "
                        "VALUES ('version', :version)"
                    ),
                    {"version": self.SCHEMA_VERSION},
                )
            else:
                connection.execute(
                    text("UPDATE schema_info SET value = :version WHERE key = 'version'"),
                    {"version": self.SCHEMA_VERSION},
                )

    def applied_version(self) -> str | None:
        with self._engine.connect() as connection:
            if not inspect(connection).has_table("schema_info"):
                return None
            result = connection.execute(
                text("SELECT value FROM schema_info WHERE key = 'version'")
            ).first()
            return result[0] if result is not None else None