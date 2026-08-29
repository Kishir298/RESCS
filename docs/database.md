# R.E.S.C.S. Database

## Backends

R.E.S.C.S. is PostgreSQL-ready via SQLAlchemy 2.0 and the `psycopg` 3
driver. It runs against SQLite by default so the application, tests and local
development work with zero external infrastructure.

| Backend | URL | Use |
| --- | --- | --- |
| SQLite | `sqlite:///rescs_dev.db` | local development (default) |
| SQLite (memory) | `sqlite+pysqlite:///:memory:` | tests |
| PostgreSQL | `postgresql+psycopg://user:pass@host:5432/dbname` | production / Supabase |

Set the URL through `RESCS_DATABASE_URL`. Credentials belong in the
environment or `.env`, never in committed files.

## Layers

```
src/rescs/db/
├── engine.py     # build_engine: per-backend pool/connect tuning
├── session.py    # session factories + session_scope transaction manager
├── schema.py     # SchemaManager: create tables + versioned schema_info
├── bootstrap.py  # bootstrap_database: engine -> connectivity -> schema -> factory
└── base.py       # SQLAlchemy DeclarativeBase
```

## Lifecycle

`bootstrap_database(settings)`:

1. builds an engine tuned for the backend (in-memory SQLite uses a static
   pool; network backends get `pool_pre_ping` and a connect timeout)
2. performs a `SELECT 1` connectivity check and fails fast with
   `DEPENDENCY_UNAVAILABLE` when the database is unreachable
3. creates the schema and records the applied version in `schema_info`
   (unless `RESCS_AUTO_CREATE_SCHEMA=false`)
4. returns a `Database` object exposing the engine and a session factory

## Transactions

Every repository operation runs through `session_scope`, which:

- opens a session
- commits on success or rolls back on failure
- maps failures to domain errors:
  - integrity violation            -> `CONFLICT`
  - connectivity problem           -> `DEPENDENCY_UNAVAILABLE`
  - any other database failure     -> `STORAGE_ERROR`

Raw database exceptions never reach API consumers.

## Schema management

`SchemaManager.migrate()` is idempotent: it derives DDL from the ORM models,
creates the `schema_info` table, and stamps the expected schema version.
Production schemas managed by a dedicated migration tool (such as Alembic)
should run with `RESCS_AUTO_CREATE_SCHEMA=false`.

## Secrets

Never put credentials in code. Use environment variables (e.g.
`RESCS_DATABASE_URL=postgresql+psycopg://...`) or the git-ignored `.env`
file. See `.env.example` for the reference template.