# RESCS 0.3.1 validation evidence

Date: 21 October 2026. This is local release validation, not a production deployment.

## Baselines

- RESCS source commit: `37cb3d7159d875d17f8a9f2e229724b64147b173`.
- RISARMS-DOCS commit: `ad40fc38e865dca4527bcb40dc2287d19505b17b`.
- CORE-HOST command-release ZIP SHA-256: `578c072d90934db389267ccf5aaf996ea092a8ca3f127a18144fae5fb3425ad1`.
- All 149 source blobs in the RESCS tree were retrieved through the GitHub connector. No source files were missing. Unchanged files were checked against Git blob hashes; transport-added trailing newlines were removed where the original hash matched.
- Execution host: macOS 15.7.7, Intel x86_64; Python 3.14.7. Build interpreter: Python 3.11.15.
- Installed test libraries: FastAPI 0.142.2, Starlette 1.7.0, SQLAlchemy 2.1.3, Pydantic 2.13.5, pydantic-settings 2.15.0, pytest 9.1.1, pytest-asyncio 1.4.0, httpx2 2.13.1. These are the available host libraries, not a clean installation of every requirements.txt pin.

## Executed checks

The release full-suite command was run from RESCS with `RESCS_CORE_HOST_SOURCE` pointing to a staged copy of the supplied CORE-HOST containing the two supplied patch files:

```sh
python3 -m pytest -q -o addopts='' \
  --deselect=tests/unit/test_db_bootstrap.py::test_bootstrap_unreachable_database_raises \
  --deselect=tests/unit/test_db_engine.py::test_postgres_engine_gets_pool_pre_ping \
  --deselect=tests/unit/test_db_engine.py::test_check_connectivity_unreachable_raises_domain_error \
  --junitxml=release-results.xml
```

**Final full-suite result: 331 passed, 4 skipped, 3 deselected in 138.16 seconds.** The successful JUnit evidence is preserved as `docs/RESCS-Release-Results.xml`. Three deselections are environment-blocked checks, not passes. Before exclusion they failed while importing psycopg because neither its binary implementation nor libpq was available. Four configured skips cover three live PostgreSQL checks and one live S3 check; provider credentials/endpoints were not supplied.

Additional executed checks:

| Check | Result and scope |
| --- | --- |
| `python3 -m pytest tests/integration/test_core_release.py tests/integration/test_uploads.py -q -o addopts=''` | 24 passed after final upload-lock changes; real local SQLite/file APIs, backup/restore, staged CORE source, simulated OS selection |
| `python3 -m pytest tests/integration/test_core_release.py -q -o addopts=''` with original supplied CORE-HOST | 10 passed against the unmodified supplied CORE-HOST source (pagination/startup enhancements apply only with the separate patch) |
| `python3 -m pytest tests/unit/test_s3_network_errors.py ... test_res1_put_auth.py` | Included in targeted checks; SDK resource/Config are mocks, not live S3 |
| `ruff check --select F src tests scripts/validate_installed.py test_res1_put_auth.py` | Passed |
| `python3 -m compileall -q src core-host-patch scripts/validate_installed.py` | Passed |
| `python3.11 -m pip wheel --no-deps --no-build-isolation . --wheel-dir dist` | Built `rescs-0.3.1-py3-none-any.whl`; requires uvicorn and other declared dependencies |
| Install wheel in separate venv using `pip install --no-deps` | Passed for wheel packaging; dependencies were inherited from host and were incomplete |
| Installed `rescs --help`, `rescs --version`, `rescs --config ... setup`, run from `/tmp` with launcher directory on PATH | Passed; version 0.3.1; config created without printing its key |
| Installed `rescs --config ... doctor` | Correctly returned 2 and reported missing uvicorn; did not require network |
| `python3 scripts/validate_installed.py` against installed wheel | Blocked at doctor because uvicorn is absent; real listener startup was not reached |
| `git apply --check .../CORE-HOST-RESCS.patch` in original extracted CORE-HOST | Passed |
| DOCX ZIP/XML parsing and Markdown-content coverage | Passed; all 215 content blocks represented |
| DOCX page rendering | Blocked: document runtime dependency loader failed; local renderer could not import pdf2image; python-docx and bundled LibreOffice were unavailable |

## Real behavior versus test doubles

The new integration tests construct the real RESCS app with real disk SQLite databases and local blob directories. They verify equal keys in equal namespaces for different owners, owner-filtered pages, ordinary reads, updates, deletes, restores, file downloads, restarts, four concurrent profile writers, old-index migration and repeat migration. The backup recovery test runs the real backup script, verifies its database hash, restores database/blobs into a different directory and reads the recovered record/file through a restarted app.

The configured-backend failure test injects a connectivity failure before database creation. It proves no local replacement is initialized; it is not a live remote-provider outage test. The offline test blocks DNS and outgoing connection helper calls using monkeypatch while local record/file operations and restart succeed. Wi-Fi/LAN were not physically disabled.

The CORE adapter test loads the actual supplied `storage.py`, serializes real adapter requests and routes them through a small in-process transport to the real RESCS API. This is not a TCP or deployed-pair test. The gateway test uses real CORE account/session code and verifies browser owner/namespace fields are ignored; its storage target is a recording test double. The patched gateway also rejects starting local managed RESCS when another endpoint is configured.

Windows and POSIX managed interpreter branches are tested with an OS facade. Per-user Windows/macOS/Linux path selection is tested with supplied environment/home values. Native Windows and Linux execution, persistent PATH changes on those OSs and actual process-group shutdown were not tested. The CLI no-argument test replaces the uvicorn runner and verifies loopback arguments and real application configuration; it is not proof of an actual listening server.

## Limitations and follow-up commands

Install complete dependencies in a clean environment before deployment. Run `python scripts/validate_installed.py` to exercise the installed command, actual listener, readiness, upsert and list from an unrelated directory. With the service installed in its source `.venv`, exercise CORE managed start/stop on the target Windows host. Set `RESCS_CORE_HOST_SOURCE` to the extracted CORE source to enable its adapter/command tests elsewhere.

Install `psycopg[binary]` or a usable libpq, rerun the three excluded checks, then supply an isolated integration database to run `requires_postgres` tests. Supply a test S3 bucket and credentials to run live S3 checks. Do not use production data for destructive test fixtures. The expanded CI matrix is configured for Windows/macOS/Linux and Python 3.11–3.13, but no GitHub workflow execution is claimed.

Global SQL idempotency-token uniqueness, single-instance rate limits and non-snapshot offset pagination remain limitations. Read the handoff before migrating or rolling back. The DOCX is an editable OOXML document with structural/content checks; its visual page layout has not been verified in this environment.

No GitHub connector writes, external publication, cloud endpoint creation or public deployment occurred.
