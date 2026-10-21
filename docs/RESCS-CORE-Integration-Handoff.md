# RESCS and CORE integration handoff

Release: RESCS 0.3.1, 21 October 2026

## 1. Changes and source baseline

RESCS remains an independent storage service. The release adds the installed `rescs` command, stable per-user standalone paths, private first-run credentials, explicit remote binding, offline diagnostics, owner-scoped record identity and a schema migration. Existing record/file/upload APIs and the uvicorn factory remain available. CORE is optional; no tunnel, cloud endpoint, device pairing or external listener is enabled by ordinary startup.

Inspected through the GitHub connector: `Kishir298/RESCS` at `37cb3d7159d875d17f8a9f2e229724b64147b173` and `Kishir298/RISARMS-DOCS` at `ad40fc38e865dca4527bcb40dc2287d19505b17b`. Related documents read: `systems/rescs.md`, `interfaces/integration-contracts.md`, ADR 0001, ADR 0005 and `security/trust-boundaries.md`. The authoritative CORE source for this work is `CORE-HOST-Terminal-Commands-2026-10-20.zip`, including `core/web/storage.py`, `services.py` and `gateway.py`. Its ZIP SHA-256 is recorded in the validation evidence.

The existing docs described `(owner, namespace, key)` record identity, but the model index and natural-key lookup omitted owner. This release makes lookup, expiration reclamation, upsert, restore and database uniqueness use owner consistently. Equal namespace/key pairs may now exist for separate owners. No stored records or files are intentionally moved or removed by this migration.

Changed source files:

- `pyproject.toml`: console entry point, uvicorn runtime dependency, optional PostgreSQL extra, version 0.3.1.
- `src/rescs/__init__.py`, `src/rescs/__main__.py`, `src/rescs/cli.py`: version and launcher/setup/doctor.
- `src/rescs/models/record.py`, `src/rescs/db/schema.py`: owner-scoped partial unique index and migration 0.3.1.
- `src/rescs/interfaces/repository.py`, `src/rescs/repositories/memory.py`, `src/rescs/repositories/sqlalchemy_.py`, `src/rescs/services/records.py`: owner-aware natural keys and collision checks.
- `src/rescs/api/routers/records.py`, `src/rescs/api/routers/files.py`, `src/rescs/api/routers/uploads.py`: owner locks also apply when a device header is supplied; device transformation cannot override a locked owner.
- `src/rescs/storage/s3.py`: bounded SDK connect/read timeouts and retries; outages are errors rather than missing-object responses.
- `tests/unit/test_cli.py`, `tests/unit/test_s3_network_errors.py`, `tests/integration/test_core_release.py`, `tests/unit/test_db_migration_v02.py`, `tests/api/test_records_api.py`, `tests/integration/test_reliability.py`, `test_res1_put_auth.py`: new regression coverage and corrected identity expectations.
- `.github/workflows/ci.yml`, `scripts/validate_installed.py`: Windows/macOS/Linux CI matrix and real installed-listener smoke script (workflow not run here).
- `README.md`, `CHANGELOG.md`, `docs/database.md`, `docs/core-integration-contract.md`, this handoff and validation evidence: release instructions and accurate boundary descriptions.
- `core-host-patch/`: separate CORE-HOST replacement files, unified patch and instructions. These are not RESCS runtime imports.

## 2. Architecture and verified HTTP contracts

Standalone clients call RESCS directly with a trusted API credential. Portal browsers authenticate to CORE; CORE derives profile scope and calls RESCS using its server credential. RESCS never imports CORE and never calls it at startup.

| Surface | Contract |
| --- | --- |
| Upsert | `PUT /api/v1/records`; JSON fields `owner`, `namespace`, `key`, `value`; value must be a JSON object |
| List/search | `GET /api/v1/records`; owner/namespace/limit/offset filters; optional query and other documented filters |
| Page | Object containing `items`, `total`, `limit`, `offset`; limit 1–500; offset >= 0 |
| Authentication | `X-API-Key` required on protected API routes; missing/wrong key returns 401 |
| Record mutation | Existing GET/PATCH/DELETE by ID, restore, purge and bulk interfaces preserved |
| Concurrency | Existing ETag / `If-Match` behavior retained; stale sequential writes return 412; no transactional snapshot pagination is promised |
| Files | Existing multipart file, binary download and resumable-upload APIs retained in RESCS |
| Health | `/health/live` and `/health/ready`; API schema at `/docs`; contract at `/api/v1/contract` |

CORE derives `owner=core.profile.PROFILE_UUID` and `namespace=personal.profile.PROFILE_UUID.SERVICE`. Profile UUID is 32 lowercase hex characters; service is validated against the adapter's scope syntax. Browser owner/namespace fields are ignored. CORE's portal implements record saving/listing; it does not implement browser file uploads, record-ID CRUD or restore/purge controls.

Managed startup remains exactly:

```text
python -m uvicorn rescs.main:create_app --factory --host 127.0.0.1 --port 8081
```

`services.py` selects the service's `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` elsewhere, falling back to the host interpreter if absent. The managed process receives `RESCS_API_KEY`, `RESCS_API_KEY_OWNER=""`, `RESCS_DATABASE_URL`, `RESCS_STORAGE_DIR`, `RESCS_AUTO_CREATE_SCHEMA=true` and a source `PYTHONPATH`. Install RESCS plus uvicorn into the selected interpreter; discovery of a source directory alone does not install dependencies.

## 3. Permissions and trusted gateway boundary

API-key authentication proves possession of a service credential. It does not authenticate an individual profile. With `RESCS_API_KEY_OWNER` empty, that credential is deliberately privileged: it may choose any owner and use ID routes across owners. Keep it only on the trusted gateway/server. Owner and namespace strings supplied directly with this credential are not an independent authorization mechanism.

With `RESCS_API_KEY_OWNER` set, the credential is locked to one owner: mismatched owner writes/list filters are rejected with 401; foreign ID reads/mutations are rejected with 403. Device labels cannot bypass this lock. `X-Device-Id` is also a trusted-gateway assertion, not a second credential. Never expose a multi-owner RESCS key to browsers, agents, devices or untrusted users. Do not publish the raw service without a suitable authenticated HTTPS boundary.

Application profile separation is not an OS sandbox. Operators and processes with filesystem access to the database, credential or object directory can access that data. Use separate OS accounts and file permissions where stronger isolation is needed. The first-run credential file uses exclusive creation and POSIX mode 0600; Windows users must restrict its ACL using Properties > Security. A user-selected parent directory retains its existing permissions.

## 4. Prerequisites and installation

Python 3.11+ and pip/venv are required. Internet is needed only to obtain dependencies initially, or use the offline wheelhouse below. RESCS needs no local language model, Ollama, CORE login, cloud login or hardware device for SQLite/local-file use. PostgreSQL needs the optional `postgres` extra and a reachable configured server; S3 needs the optional `s3` extra and its configured provider credentials. Use the extracted source directory or included wheel as the installation input. These are ordinary installations, not editable installs.

### Windows PowerShell

Run once, replacing the extracted-source path:

```powershell
$venv = Join-Path $env:LOCALAPPDATA 'Programs\RESCS'
py -3.11 -m venv $venv
& "$venv\Scripts\python.exe" -m pip install 'C:\Downloads\RESCS'
$scripts = Join-Path $venv 'Scripts'
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $scripts) {
  [Environment]::SetEnvironmentVariable('Path', "$scripts;$userPath", 'User')
}
$env:Path = "$scripts;$env:Path"
rescs setup
rescs doctor
rescs
```

Reopen terminals after the persistent PATH change. The service runs in the foreground; Ctrl+C stops it. The default API is `http://127.0.0.1:8081`, with the normal interactive API interface at `/docs`. `rescs` with no arguments starts the local service and creates its credential once if needed. It does not open a public endpoint.

### macOS, zsh

```sh
python3 -m venv "$HOME/.local/share/rescs-venv"
"$HOME/.local/share/rescs-venv/bin/python" -m pip install '/absolute/path/to/RESCS'
printf '\nexport PATH="$HOME/.local/share/rescs-venv/bin:$PATH"\n' >> "$HOME/.zshrc"
export PATH="$HOME/.local/share/rescs-venv/bin:$PATH"
rescs setup
rescs doctor
rescs
```

### Linux, login shell

Install your distribution's Python/venv package if necessary, then:

```sh
python3 -m venv "$HOME/.local/share/rescs-venv"
"$HOME/.local/share/rescs-venv/bin/python" -m pip install '/absolute/path/to/RESCS'
printf '\nexport PATH="$HOME/.local/share/rescs-venv/bin:$PATH"\n' >> "$HOME/.profile"
export PATH="$HOME/.local/share/rescs-venv/bin:$PATH"
rescs setup
rescs doctor
rescs
```

For interactive zsh on Linux, add the same export to `~/.zshrc`; login-shell startup files vary. Do not use sudo pip or bypass externally managed system Python. These PATH additions are one-time changes; avoid repeatedly appending them.

### Daily commands on all three OSs

```text
rescs --help
rescs --version
rescs setup
rescs doctor
rescs doctor --check-backends
rescs
rescs --port 8082 serve
rescs --config ABSOLUTE_ENV_FILE doctor
rescs --config ABSOLUTE_ENV_FILE
```

Global options precede the subcommand. `doctor` validates configuration and dependency availability without network probes. `--check-backends` explicitly probes configured database/S3 access without migrating schema. It requires dependencies to be present. Diagnostic failures return exit code 2 and do not substitute storage. Configuration exceptions are summarized without printing secret-bearing validation inputs.

Use `/docs` and its Authorize control for a trusted local API session; obtain the generated API key from the private credential file, never from shared logs. Close the browser session when done. Remote hosting is a separate operator choice, for example `rescs --host 0.0.0.0 --allow-remote`; this opens a listener and must be combined with network/firewall policy and HTTPS ingress. It creates no tunnel or cloud deployment. Prefer a loopback listener behind a separately configured HTTPS gateway.

## 5. Configuration, storage and compatibility

Standalone `rescs` uses a per-user `rescs.env` and stable local paths:

| OS | Data and config directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\RESCS` (fallback `%USERPROFILE%\AppData\Local\RESCS`) |
| macOS | `~/Library/Application Support/RESCS` |
| Linux | `$XDG_DATA_HOME/rescs`, or `~/.local/share/rescs` |

The directory contains `rescs.env`, default database `rescs.sqlite3` and default object directory `files`. The launcher ignores unrelated working-directory `.env` files. Environment variables override the chosen env file. Explicit database and storage settings, including remote backends, always win; a failure never selects local persistence instead.

The existing factory entry point retains its old configuration behavior: `.env` in the working directory, default relative `sqlite:///rescs_dev.db` and `rescs_storage`, and an explicitly supplied API key. CORE managed startup supplies absolute paths under its web data directory: `rescs.sqlite3` and `rescs-files`. Standalone and managed data are separate unless explicitly configured to use the same paths. Do not run concurrent independently configured servers against one local blob directory without evaluating locking and consistency.

For an existing installation, preserve its API key and use `rescs --config ABSOLUTE_ENV_FILE`; set absolute `RESCS_DATABASE_URL` and `RESCS_STORAGE_DIR` before switching launch methods. The new command does not discover, copy or migrate data from arbitrary old working directories. An explicitly missing config file is an error.

Important configuration variables:

| Variable | Meaning/default |
| --- | --- |
| `RESCS_API_KEY` | Required service credential, at least 16 characters; generated privately by standalone setup |
| `RESCS_API_KEY_OWNER` | Empty for trusted multi-owner gateway; set to lock one owner |
| `RESCS_DATABASE_URL` | SQLAlchemy URL; stable SQLite path in standalone launcher, relative legacy default in factory |
| `RESCS_STORAGE_DIR` | Local object directory; stable standalone default or legacy factory setting |
| `RESCS_AUTO_CREATE_SCHEMA` | true by default; migrates at startup when enabled |
| `RESCS_STORAGE_BACKEND` | local default; s3 or explicit nondurable memory |
| `RESCS_ENV` | development/test/production |
| `RESCS_LOG_LEVEL` | INFO default |
| `RESCS_S3_ENDPOINT`, `RESCS_S3_BUCKET`, `RESCS_S3_REGION` | Optional S3 provider connection |
| `RESCS_S3_ACCESS_KEY`, `RESCS_S3_SECRET_KEY`, `RESCS_S3_PATH_PREFIX` | Optional S3 credentials/object prefix; never put real values in handoff docs |
| `RESCS_REQUEST_ID_HEADER` | X-Request-ID default |
| `RESCS_MAX_RECORDS_PER_OWNER`, `RESCS_MAX_FILES_PER_OWNER`, `RESCS_MAX_BYTES_PER_OWNER`, `RESCS_MAX_FILE_SIZE` | Zero means unlimited |
| `RESCS_MAX_METADATA_BYTES`, `RESCS_MAX_BULK_BATCH` | 65536 bytes / 100 operations defaults |
| `RESCS_MAX_TTL_SECONDS`, `RESCS_AUDIT_RETENTION_DAYS` | 31536000 seconds / 90 days defaults |
| `RESCS_STREAMING_THRESHOLD_BYTES` | 8388608 default |
| `RESCS_RATE_LIMIT_ENABLED` | false default; in-process single-instance limiter |
| `RESCS_RATE_LIMIT_GENERAL_PER_MINUTE`, `RESCS_RATE_LIMIT_WRITES_PER_MINUTE`, `RESCS_RATE_LIMIT_UPLOADS_PER_MINUTE` | 100 / 60 / 20 defaults |

`RESCS_APP_NAME` and `RESCS_VERSION` can override display metadata; normally leave them unset. Existing `Settings` validation and the machine-readable contract remain authoritative for all schema limits.

## 6. CORE installation and portal usage

1. Keep RESCS as a sibling project of CORE-HOST. Install it in `RESCS/.venv` with the same venv and pip commands above, choosing `.venv` as the destination, so CORE finds its interpreter. The globally installed standalone command may use a separate environment.
2. Apply `core-host-patch/CORE-HOST-RESCS.patch` from the CORE-HOST source root with `git apply --check PATH_TO_PATCH`, then `git apply PATH_TO_PATCH`. Alternatively replace the exact two files supplied under `core-host-patch/core/web/`. Back up originals first. `services.py` requires no change.
3. Start `core-host`, create/sign in to its owner profile, configure the RESCS source root in Settings and choose the intended RESCS URL/key. A remote URL continues using that backend; managed startup is rejected until Settings explicitly selects `http://127.0.0.1:8081`.
4. For managed local storage, start RESCS from the portal as owner. CORE supplies its own service credential and empty key-owner lock. Do not replace this with a single profile lock: one managed service holds several profiles.
5. Save/list profile records in the portal. A task result is saved only when explicitly requested. Sign in to a different profile to see its separate data.

The supplied CORE-HOST patch adds validated `limit`/`offset` forwarding at `/api/records`, checks returned page metadata, and verifies owner/namespace/key on saved-record responses. The existing portal page displays its first page; client-side pagination controls are not added. API consumers may request further pages explicitly. No CORE-CLIENT patch is required for this HTTP contract; its browser launcher continues using the same portal URL. Native client transport is unchanged and was not exercised here.

## 7. Offline and network matrix

| Feature | Network requirement | Failure behavior |
| --- | --- | --- |
| setup, help, version, ordinary doctor | None after installation | Clear nonzero configuration/dependency errors |
| SQLite records and local files, local health, local backups | No internet or Wi-Fi; loopback API needs a functioning OS loopback stack | Local filesystem/database errors remain errors |
| CORE portal and RESCS on the same machine | No internet/Wi-Fi once installed | Each local service must be running |
| Another device reaching CORE or RESCS | Its LAN/VPN/other configured network | Unreachable errors; no local replacement |
| Local PostgreSQL or local S3-compatible server | Only its configured local/LAN connection | Database connect timeout 5s; S3 connect 5s/read 10s, one retry |
| Remote PostgreSQL/S3/cloud storage | Reachable provider network, TLS and credentials | Fail clearly; no fallback to SQLite/local blobs |
| Downloads, internet search, external APIs, model downloads | Their respective connection | Not RESCS local-storage prerequisites |

CORE's HTTP adapter uses an 8-second timeout, refuses redirects and limits response size. These bounds are per operation, not an overall process deadline; large transfers and SDK credential discovery may take additional time. RESCS itself has no search or local-model runtime. `fake:` S3 and memory stores remain explicit test facilities, not production persistence; doctor rejects a fake S3 configuration as durable operation.

### Prepare offline installations

On an online machine matching each target OS, CPU and Python minor version, use a dedicated preparation environment. Build/download the service wheel plus all dependency wheels; a single wheelhouse is not guaranteed portable across platforms.

Windows PowerShell, from the extracted RESCS directory:

```powershell
py -3.11 -m venv .prep
& '.\.prep\Scripts\python.exe' -m pip install --upgrade pip setuptools wheel
& '.\.prep\Scripts\python.exe' -m pip wheel --wheel-dir wheelhouse .
# If required, also prepare optional backends:
& '.\.prep\Scripts\python.exe' -m pip wheel --wheel-dir wheelhouse '.[postgres,s3]'
Get-FileHash .\wheelhouse\* -Algorithm SHA256
```

macOS/Linux:

```sh
python3 -m venv .prep
.prep/bin/python -m pip install --upgrade pip setuptools wheel
.prep/bin/python -m pip wheel --wheel-dir wheelhouse .
# Only when those backends are required:
.prep/bin/python -m pip wheel --wheel-dir wheelhouse '.[postgres,s3]'
shasum -a 256 wheelhouse/* > wheelhouse-SHA256.txt
```

Transfer the wheelhouse, hash manifest and Python installer to the offline machine. Verify hashes, create its venv, then install without resolving any index:

```powershell
& "$venv\Scripts\python.exe" -m pip install --no-index --find-links 'D:\wheelhouse' rescs==0.3.1
```

```sh
"$HOME/.local/share/rescs-venv/bin/python" -m pip install --no-index --find-links /media/wheelhouse rescs==0.3.1
```

Apply the same PATH/setup/start steps. For optional backends install `'rescs[postgres,s3]==0.3.1'` from the prepared wheelhouse. Preinstall provider/native tools such as `pg_dump`/`pg_restore` if needed. No models need preparing for RESCS; prepare each other RISARMS service's models separately. The delivered source ZIP and RESCS wheel do not include all third-party dependency wheels.

## 8. Migration, backup, recovery and rollback

Stop writers and take a verified database-plus-blob backup before upgrading. Preserve the credential/env file separately with restricted permissions. Schema migration 0.3.1 creates unique partial index `uq_records_live_owner_namespace_key` on `(owner, namespace, key)` for rows with `deleted_at IS NULL`, then removes `uq_records_live_namespace_key`. It is idempotent and retains rows, IDs, timestamps, versions, ETags and file data. Existing pre-0.2 migrations remain available. Only SQLite and PostgreSQL are supported for this migration.

For automatic migration use normal startup with `RESCS_AUTO_CREATE_SCHEMA=true`. For controlled production migration, stop the service, back up, run the following through the configured environment, then set auto-create false before ordinary service startup if desired:

```python
from rescs.cli import load_settings
from rescs.db.bootstrap import bootstrap_database
from pathlib import Path
database = bootstrap_database(load_settings(Path('ABSOLUTE_ENV_FILE')), create_schema=True)
database.engine.dispose()
```

The existing backup utility is included in the source ZIP. Run it with absolute paths, using the same environment that has RESCS installed:

```text
python ABSOLUTE_RESCS_SOURCE/scripts/rescs_backup.py --database-url sqlite:///ABSOLUTE_DATABASE_FILE --storage-dir ABSOLUTE_OBJECT_DIRECTORY --out ABSOLUTE_NEW_BACKUP_DIRECTORY --verify
```

Stop writes for a consistent database/blob pair: SQLite's online database snapshot alone does not synchronize blobs written concurrently. The utility writes `db.dump`, `blobs/` and `manifest.json`, checks hashes, refuses to overwrite an existing output, and returns failure for incomplete backups. For PostgreSQL use `pg_dump`/`pg_restore` from the appropriate installed provider toolset; prefer private credential environment/pgpass configuration instead of a password-bearing URL in shell history. The tool does not snapshot remote S3 objects: use provider snapshots/versioning/export and retain the matching database snapshot.

Restore with the service stopped: verify manifest hashes; copy SQLite `db.dump` to the configured database path or restore the PostgreSQL custom-format dump into the intended empty database; restore `blobs/` to the configured local object directory; restore private configuration; start the matching version and check `/health/ready`, a known record and a downloaded file hash. Never restore over a running database. Keep the original backup immutable and test recovery in an isolated directory before replacing production data.

Rollback requires stopping the service and restoring the pre-upgrade database/blob snapshot plus configuration, then reinstalling the previous RESCS wheel/source. Do not run 0.3.0 lookup code against 0.3.1 data that now contains duplicate namespace/key pairs across owners: it can select the wrong owner's row. Reversing the index alone is unsafe when such pairs exist. Roll back the two CORE files from their backups or apply the supplied patch in reverse after checking it.

## 9. Verification, limitations and troubleshooting

See `docs/RESCS-Release-Validation.md` for executed commands, exact results, dependency versions and blocked checks. Validation distinguishes real local SQLite/files/ASGI calls from a replaced uvicorn runner, mocked OS branches and in-process CORE HTTP transport. Windows and Linux were not executed. No public deployment, provider-backed PostgreSQL/S3 validation or endurance run is claimed. Local standalone functions do not depend on CORE, remote authentication or internet probes.

The database still retains the existing global uniqueness constraint on record `idempotency_key`; use globally unique idempotency tokens for SQL-backed creates. This release corrects owner-scoped natural keys, not that separate legacy limitation. Offset pages are not snapshots during concurrent edits. The service remains a single-instance design for rate limiting; broader multi-process concurrency guarantees and zero-downtime migrations require further validation.

If the command is not found, reopen the terminal, check the venv's Scripts/bin directory is on PATH and run its absolute `rescs` launcher. Windows: `Get-Command rescs`; macOS/Linux: `command -v rescs`. Verify installation with that venv's `python -m pip show rescs`; multiple Python installations often explain PATH mistakes. If dependencies are missing, reinstall from the prepared wheelhouse or online package source into that same venv.

For invalid credentials, check the chosen private env file and environment overrides without posting its contents. For a port conflict, stop the other process or use `--port`; CORE managed RESCS uses fixed port 8081. For missing old records, verify the absolute database/object paths and chosen backend; do not initialize a replacement database as a recovery shortcut. For schema errors, stop and restore a verified backup or complete the migration deliberately. For remote failures, check the configured provider/network and run the explicit backend doctor; retain that backend choice until the operator changes it.

The Markdown and DOCX handoffs are separate deliverables. The DOCX passed structural and content checks; page rendering was blocked by unavailable runtime dependencies, so its visual layout is unverified. The updated ZIP contains the complete RESCS source, tests, handoff, built service wheel and separate CORE-HOST patch. GitHub was read but was not written or deployed during this release work.
