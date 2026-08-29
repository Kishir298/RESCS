# R.E.S.C.S. Architecture

## What R.E.S.C.S. is

R.E.S.C.S. (**R**ishik's **E**fficient **S**ystem for **C**loud **S**torage)
is the cloud storage and data persistence subsystem of the R.I.S.A.R.M.S.
ecosystem.

Boundary of responsibility:

```text
R.I.S.A.R.M.S.
       |
       v
    C.O.R.E.          (manages, coordinates, routes)
       |
       +---- A.S.I.S. (intelligence)
       +---- R.E.S.C.S.(storage)
                     |
                     v
              PostgreSQL / cloud object storage
```

C.O.R.E. manages. A.S.I.S. provides intelligence. R.E.S.C.S. stores. These
responsibilities are deliberately kept separate; projects are developed
independently and never import each other.

## Target architecture

```text
                R.E.S.C.S.
                    |
     +--------------+---------------+------+
     v              v               v      v
  Records        Files          Metadata  Health/Security
     |              |              |       |
     +--------------+--------------+       |
                    |                       |
             Storage Service                |
                    |                       |
             Storage Abstraction            |
                    |                       |
        +-----------+-----------+        +--+
        v                       v
   Repository              Object Store
   (SQLAlchemy: SQLite/     (local filesystem,
   PostgreSQL/Supabase)     cloud-adoptable)
```

Layered without shortcuts:

```text
API layer        -> HTTP handlers, validation, error mapping
Service layer    -> business operations, orchestration
Repository layer -> data access behind a Protocol
Storage layer    -> binary object persistence behind a Protocol
Database layer   -> SQLAlchemy engine/session wiring
```

No API route contains direct database logic.

## Project structure

```
src/rescs/
├── main.py            # application factory, lifespan, health endpoints
├── config.py          # pydantic-settings configuration (env / .env)
├── logging.py         # process logging foundation
├── errors.py          # domain error hierarchy (codes + HTTP status)
├── health.py          # named dependency checks + aggregate report
├── domain.py          # storage-agnostic domain dataclasses (RecordData, FileObjectData)
├── etag.py            # deterministic content identifiers
├── db/base.py         # SQLAlchemy declarative base
├── db/                # engine, sessions, schema manager, bootstrap
├── models/            # SQLAlchemy ORM models (records, file_objects)
├── schemas/           # Pydantic request/response schemas + validation
├── interfaces/        # repository protocols (record, file object)
├── repositories/      # in-memory + SQLAlchemy implementations
├── services/          # record service + composition root
├── storage/           # object-store implementation               (phase 5)
├── services/          # records & files services                  (phase 4/5)
└── api/               # routers, dependencies, error handlers     (phase 6)
```

## Development roadmap

| Phase | Focus | Status |
| --- | --- | --- |
| 1 | Project foundation and architecture | Complete (v0.1.0) |
| 2 | Data model and storage abstraction | Complete |
| 3 | Database and persistence | Complete |
| 4 | Storage service | Complete |
| 3 | Database and persistence | Pending |
| 4 | Storage service | Pending |
| 5 | File storage | Pending |
| 6 | API and service integration | Pending |
| 7 | Security and access control | Pending |
| 8 | Synchronization and consistency | Pending |
| 9 | C.O.R.E. integration contract | Pending |
| 10 | Observability and health | Pending |
| 11 | Testing and integration | Pending |
| 12 | R.I.S.A.R.M.S. readiness | Pending |
| 13 | Cleanup, documentation, release | Pending |

Each phase ends with: full test run, documentation update, Git commit, and a
push to `main`.