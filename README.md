# R.E.S.C.S.

**Rishik's Efficient System for Cloud Storage**

R.E.S.C.S. is the cloud storage and data persistence subsystem of the
[R.I.S.A.R.M.S.](https://github.com/Kishir298) ecosystem. It stores
information, files, records and metadata in cloud-backed storage and makes
them retrievable by authorized R.I.S.A.R.M.S. systems.

```
                    R.I.S.A.R.M.S.
                           |
                           v
                        C.O.R.E.
                           |
                    Storage requests
                           |
                           v
                       R.E.S.C.S.
                           |
                           v
                     Cloud Database
                           +
                      File/Object Storage
```

R.E.S.C.S. is **not** the ecosystem controller. C.O.R.E. coordinates the
ecosystem; R.E.S.C.S. provides storage. The two projects are developed
independently and connected through a stable contract (see
`docs/core-integration-contract.md`).

## Status

v0.1.0 — Phases 1–13 complete (foundation through release readiness).
Automated suite: unit + API + integration (restart persistence, lifecycle,
concurrency, owner scoping, error contract, health, observability,
CORE-consumer contract, bounded endurance). Live PostgreSQL/Supabase,
deployed CORE ↔ RESCS interop and long-horizon endurance remain Ready for
External Validation. See `docs/architecture.md` and `CHANGELOG.md`.

## Stack

- **API:** FastAPI (OpenAPI docs at `/docs`)
- **Persistence:** SQLAlchemy 2.0 with PostgreSQL (`psycopg` 3) support;
  SQLite used by default for development and tests
- **Validation / config:** Pydantic v2, pydantic-settings
- **Tests:** pytest, httpx TestClient

## Project structure

```
src/rescs/
├── main.py            # application factory, lifespan wiring
├── config.py          # pydantic-settings configuration (env / .env)
├── logging.py         # process logging foundation
├── errors.py          # domain error hierarchy (codes + HTTP status)
├── health.py          # named dependency checks + aggregate report
├── domain.py          # storage-agnostic domain dataclasses
├── etag.py            # deterministic content identifiers
├── security.py        # X-API-Key auth + owner scoping
├── observability.py   # request-ID middleware + access logging
├── contract.py        # machine-readable CORE contract
├── db/                # engine, sessions, schema manager, bootstrap
├── models/            # SQLAlchemy ORM models (records, file_objects)
├── schemas/           # Pydantic request/response schemas + validation
├── interfaces/        # repository + object-store protocols
├── repositories/      # in-memory + SQLAlchemy implementations
├── services/          # record + file services, composition root
├── storage/           # object stores (local, memory)
└── api/               # versioned HTTP API (v1), routers, deps, errors
```

Detailed phase-by-phase documentation lives in `docs/`.

## Installation

Requires Python 3.11+ (developed on 3.14).

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Configuration

Copy `.env.example` to `.env` and set the required values. Secrets are never
committed.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `RESCS_API_KEY` | Yes (min 16 chars) | — | API authentication key, sent via `X-API-Key` |
| `RESCS_ENV` | No | `development` | `development`, `test`, or `production` |
| `RESCS_DATABASE_URL` | No | `sqlite:///rescs_dev.db` | SQLAlchemy URL; use `postgresql+psycopg://` for PostgreSQL/Supabase |
| `RESCS_STORAGE_DIR` | No | `rescs_storage` | Local object-store directory |
| `RESCS_LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `RESCS_REQUEST_ID_HEADER` | No | `X-Request-ID` | Request correlation header echoed on every response |

## Running

```powershell
.\.venv\Scripts\python.exe -m uvicorn rescs.main:create_app --factory --reload --port 8000
```

Verify:

```text
GET http://127.0.0.1:8000/health/live
GET http://127.0.0.1:8000/health/ready
```

## Running tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Development workflow

The system is developed in phases; each phase ends with a full test run, a
Git commit, and a push to `main`. See `docs/architecture.md` for the roadmap
and `CHANGELOG.md` for per-phase notes.

## License

MIT (provisional).