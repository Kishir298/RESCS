"""Local filesystem object store tests."""

from __future__ import annotations

import pytest

from rescs.errors import StorageError
from rescs.storage.local import LocalObjectStore


def test_creates_base_dir(tmp_path):
    store = LocalObjectStore(tmp_path / "nested" / "store")
    assert (tmp_path / "nested" / "store").is_dir()


def test_round_trip(tmp_path):
    store = LocalObjectStore(tmp_path / "store")
    store.put("rec-123", b"payload-data")
    assert store.exists("rec-123")
    assert store.get("rec-123") == b"payload-data"
    assert (tmp_path / "store" / "rec-123").is_file()


def test_missing_get_raises(tmp_path):
    store = LocalObjectStore(tmp_path / "store")
    with pytest.raises(StorageError):
        store.get("nope")


def test_delete_removes_blob(tmp_path):
    store = LocalObjectStore(tmp_path / "store")
    store.put("abc", b"data")
    store.delete("abc")
    assert not store.exists("abc")
    store.delete("abc")


def test_path_traversal_rejected(tmp_path):
    store = LocalObjectStore(tmp_path / "store")
    with pytest.raises(StorageError):
        store.put("../escape", b"x")
    with pytest.raises(StorageError):
        store.get("../escape")


def test_persists_across_instances(tmp_path):
    base = tmp_path / "store"
    first = LocalObjectStore(base)
    first.put("persist-me", b"bytes")
    second = LocalObjectStore(base)
    assert second.get("persist-me") == b"bytes"