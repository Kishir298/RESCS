# Changelog

All notable changes to R.E.S.C.S. are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/).
Versioning follows [Semantic Versioning](https://semver.org/).

## Unreleased

### Added - Phase 1 (foundation)

- `src/rescs` package with application factory (`create_app`)
- Environment / `.env` configuration via pydantic-settings (`RESCS_*`)
- Required API key configuration (`RESCS_API_KEY`, min 16 chars)
- Logging foundation (`rescs.logging`)
- Domain error hierarchy with stable codes and HTTP status mapping
- Health/readiness reporting foundation (`rescs.health`)
- Health endpoints: `/health/live`, `/health/ready`, `/health`
- Project metadata (`pyproject.toml`), pinned dependencies, `.gitignore`,
  `.env.example`
- Test suite: configuration, errors, health service, health API

### Added - Phase 2 (data model and storage abstraction)

- Storage-agnostic domain dataclasses (`RecordData`, `FileObjectData`)
- SQLAlchemy ORM models (`records`, `file_objects`) with unique constraints,
  timestamps, versions and idempotency keys
- Repository protocols decoupling services from database backends
- In-memory repository implementations (deterministic test doubles)
- SQLAlchemy repository implementations with conflict/not-found translation
- Pydantic schemas with JSON-serializability validation and domain mapping
- Test suite: domain, models, schemas, in-memory and SQLAlchemy repositories

### Added - Phase 3 (database and persistence)

- `db.engine`: per-backend engine construction (SQLite static pool, network
  backends with `pool_pre_ping` and connect timeouts)
- `db.session`: session factories and the `session_scope` transaction
  manager (commit/rollback, domain-error translation)
- `db.schema`: `SchemaManager` for idempotent schema creation with a
  versioned `schema_info` table
- `db.bootstrap`: `bootstrap_database` wiring engine, connectivity check,
  schema and session factory from settings
- Startup connectivity check with fail-fast `DEPENDENCY_UNAVAILABLE`
- `RESCS_AUTO_CREATE_SCHEMA` configuration
- Persistent file-backed storage verified by tests
- Docs: `docs/database.md`

### Added - Phase 4 (storage service)

- `RecordService` operations: create, put (upsert), get, update, delete,
  list, search
- Idempotent creates via `idempotency_key`
- Version tracking, ETag computation (`rescs.etag`) and `updated_at` bumps
  on every modification
- Repository `search` across key, value and metadata (portable across
  SQLite/PostgreSQL and in-memory backends)
- Pagination clamping in the service layer
- Service composition root (`build_services`) for memory and persistent
  backends
- Test suite: record service behaviour, factory wiring