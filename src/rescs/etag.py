"""Deterministic content identifiers (ETags)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"object of type {type(value).__name__} is not JSON serializable")


def content_etag(value: dict, metadata: dict) -> str:
    """Stable hash of a record's JSON payload (canonical serialization)."""
    canonical = json.dumps(
        [value, metadata],
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_etag(sha256: str, size: int) -> str:
    """Stable hash derived from a stored blob's fingerprint."""
    raw = f"{sha256}:{size}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()