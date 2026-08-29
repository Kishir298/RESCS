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

### Added - Phase 5 (file storage)

- Object store protocol (`interfaces/object_store`) separating blobs from
  metadata
- `LocalObjectStore` (filesystem, atomic writes, path-traversal protection)
  and `MemoryObjectStore` (test double)
- `FileService`: upload, download, metadata read, delete, list
- Content fingerprints (`sha256`), size tracking and file etags
- Blob cleanup on metadata-write failure; best-effort blob deletion on remove
- Composition root now wires record + file services with an object store
- Docs: `docs/storage.md`

### Added - Phase 6 (API and service integration)

- Versioned HTTP API under `/api/v1` (`rescs.api.routers`)
- Record endpoints: create (201), upsert (PUT), read, patch, delete (204),
  list and search with pagination
- File endpoints: upload (multipart, 201), metadata read, content download,
  delete (204), list
- API dependencies (`api.deps`) exposing settings and the composed services
- Real health probes wired into `/health/ready` (database connectivity,
  object-store read/write probe)
- Consistent `{error: {code, message, details}}` response envelope for domain
  and validation errors (`api.errors`)
- Application factory lifecycle: bootstrap database + services on startup,
  dispose engine on shutdown
- Interactive OpenAPI docs at `/docs` and `/redoc`
- Docs: `docs/api.md`

### Added - Phase 7 (security and access control)

- `X-API-Key` authentication enforced on every `/api/v1` route with
  constant-time comparison (`rescs.security`)
- `401 UNAUTHORIZED` envelope for missing/invalid credentials
- Owner scoping via `RESCS_API_KEY_OWNER`: single-owner lock mode forcing
  `owner` on writes, on list filters, and authorizing reads/deletes
- Cross-owner access rejected with `401` (claiming another owner) or `403`
  (touching another owner's resource)
- Owner field plumbed through file uploads and all record routes
- Test suite: authentication, scoped-owner enforcement across records

### Added - Phase 8 (synchronization and consistency)

- Optimistic concurrency via `If-Match` / etag precondition on record
  `PATCH`/`PUT`/`DELETE` and file `DELETE` (`412 PRECONDITION_FAILED`)
- RFC 9110 etag parsing (bare, quoted `"..."`, weak `W/"..."`, `*`)
- `ETag` response header on read/create/update routes
- Idempotent creates/upload formalized and covered by unit + API tests
- Blob integrity verification on download (sha256 mismatch ->
  `STORAGE_ERROR` with expected/actual digests)
- Docs: `docs/synchronization.md`