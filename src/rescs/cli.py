"""Installed standalone launcher. Managed uvicorn startup remains unchanged."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import secrets
import sys

from rescs import __version__


def data_directory(platform=None, environ=None, home=None):
    platform = platform or sys.platform
    env = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform == "win32":
        return Path(env.get("LOCALAPPDATA", home / "AppData" / "Local")) / "RESCS"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "RESCS"
    return Path(env.get("XDG_DATA_HOME", home / ".local" / "share")) / "rescs"


def setup(path):
    """Create credentials once, without printing or overwriting them."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Configuration already exists: {path}")
        return
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write("# Local RESCS credential; keep private. Environment overrides this file.\n")
        stream.write("RESCS_API_KEY=" + secrets.token_urlsafe(32) + "\n")
    print(f"Configuration created: {path}")
    if sys.platform == "win32":
        print("Restrict this file's Windows ACL to your account using Properties > Security.")


def load_settings(path):
    from rescs.config import Settings
    settings = Settings(_env_file=path)
    # Explicit environment/file settings always win, including remote backends.
    root = data_directory()
    if "database_url" not in settings.model_fields_set:
        settings.database_url = "sqlite:///" + (root / "rescs.sqlite3").as_posix()
    if "storage_dir" not in settings.model_fields_set:
        settings.storage_dir = str(root / "files")
    return settings


def doctor(settings, check_backends=False):
    from sqlalchemy.engine import make_url
    url = make_url(settings.database_url)
    print(f"RESCS {__version__}; Python {sys.version_info.major}.{sys.version_info.minor}; {sys.platform}")
    print(f"Database backend: {url.get_backend_name()}; object backend: {settings.storage_backend}")
    print("Owner authorization: " + ("single owner locked" if settings.api_key_owner else "trusted gateway key; caller selects owner"))
    ok = True
    if importlib.util.find_spec("uvicorn") is None:
        print("ERROR: uvicorn is missing; reinstall RESCS with its dependencies.")
        ok = False
    if url.get_backend_name() == "sqlite":
        print(f"SQLite file: {url.database}")
    if settings.storage_backend == "local":
        print(f"Object directory: {Path(settings.storage_dir).resolve()}")
    if settings.storage_backend == "memory" or url.database == ":memory:":
        print("WARNING: an explicitly configured memory backend is not durable.")
    if settings.storage_backend == "s3":
        if not settings.s3_bucket or settings.s3_endpoint.startswith("fake:"):
            print("ERROR: S3 requires a real bucket/endpoint for durable operation.")
            ok = False
        if importlib.util.find_spec("boto3") is None:
            print("ERROR: install rescs[s3] for S3 support.")
            ok = False
    if check_backends and ok:
        from rescs.db.bootstrap import bootstrap_database
        database = bootstrap_database(settings, create_schema=False)
        try:
            from rescs.db.schema import SchemaManager
            print(f"Reachable database schema: {SchemaManager(database.engine).applied_version()}")
            if settings.storage_backend == "s3":
                from rescs.storage.s3 import build_object_store
                store = build_object_store(settings)
                store._bucket.meta.client.head_bucket(Bucket=settings.s3_bucket)
            print("Backend checks succeeded; no schema migration performed.")
        finally:
            database.engine.dispose()
    elif not check_backends:
        print("No network probes performed. Use doctor --check-backends for explicit connectivity checks.")
    return 0 if ok else 2


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rescs", description="Independent RESCS storage service; loopback hosting by default.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="Explicit env file; defaults to the per-user RESCS directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8081, type=int)
    parser.add_argument("--allow-remote", action="store_true", help="Explicitly permit a non-loopback listener; configure TLS separately")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("setup", help="Create a private local API credential once")
    check = commands.add_parser("doctor", help="Validate configuration without requiring a network")
    check.add_argument("--check-backends", action="store_true", help="Explicit database/S3 connectivity checks without migration")
    commands.add_parser("serve", help="Start the service (also the default with no arguments)")
    args = parser.parse_args(argv)
    path = (args.config or data_directory() / "rescs.env").expanduser().resolve()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_remote:
        parser.error("non-loopback hosting requires --allow-remote")
    try:
        if args.command == "setup":
            setup(path)
            return 0
        if args.config and not path.is_file():
            print("ERROR: explicit configuration file does not exist.", file=sys.stderr)
            return 2
        if args.command != "doctor" and not path.exists() and not os.environ.get("RESCS_API_KEY"):
            setup(path)
        settings = load_settings(path)
        if args.command == "doctor":
            return doctor(settings, args.check_backends)
        from sqlalchemy.engine import make_url
        url = make_url(settings.database_url)
        if url.get_backend_name() == "sqlite" and url.database not in {None, "", ":memory:"}:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        from rescs.main import create_app
        import uvicorn
        print(f"Local API docs: http://{args.host}:{args.port}/docs")
        uvicorn.run(create_app(settings), host=args.host, port=args.port)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        # Validation/driver errors can embed credentials; never echo them.
        print(f"ERROR: RESCS could not complete the operation ({type(exc).__name__}). Check configuration, dependencies and backend access; no fallback was used.", file=sys.stderr)
        return 2
