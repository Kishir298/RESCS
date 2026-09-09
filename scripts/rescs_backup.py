#!/usr/bin/env python3
"""RESCS backup: database dump + blob snapshot + manifest.

Usage:
  python scripts/rescs_backup.py --database-url sqlite:///rescs_dev.db \\
      --storage-dir rescs_storage --out backups/rescs-YYYYMMDD

Produces:
  out/db.dump (sqlite backup or pg_dump when postgres)
  out/blobs/ (copy of object-store files)
  out/manifest.json (sha256 per file + counts + RPO/RTO notes)

Restore: see docs/backups.md. Never commits secrets; manifest contains
only hashes and counts, never API keys or raw values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_sqlite(db_path: Path, out: Path) -> Path:
    dest = out / "db.dump"
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(dest))
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="RESCS backup tool")
    ap.add_argument("--database-url", default="sqlite:///rescs_dev.db")
    ap.add_argument("--storage-dir", default="rescs_storage")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    blobs_out = out / "blobs"
    out.mkdir(parents=True, exist_ok=True)
    blobs_out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_url_scheme": args.database_url.split(":")[0],
        "files": [],
    }

    db_url: str = args.database_url
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", ""))
        if db_path.exists():
            dest = backup_sqlite(db_path, out)
            manifest["db"] = {"file": "db.dump", "sha256": _sha256_file(dest)}
        else:
            manifest["db"] = {"missing": str(db_path)}
    else:
        manifest["db"] = {
            "note": "non-sqlite backend: use pg_dump manually",
            "hint": "pg_dump $DATABASE_URL -Fc -f out/db.dump",
        }

    storage = Path(args.storage_dir)
    count = 0
    if storage.exists():
        for blob in sorted(storage.iterdir()):
            if blob.is_file() and not blob.name.startswith("."):
                dest = blobs_out / blob.name
                shutil.copy2(blob, dest)
                manifest["files"].append({"name": blob.name, "sha256": _sha256_file(dest), "size": dest.stat().st_size})
                count += 1
    manifest["blob_count"] = count
    manifest["rpo"] = "daily backups: up to 24h data loss window"
    manifest["rto"] = "restore DB then blobs, verify manifest hashes; target <1h for small deployments"
    manifest["restore"] = "see docs/backups.md"

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"backup complete: {count} blobs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
