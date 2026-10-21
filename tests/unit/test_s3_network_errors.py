import sys
from types import SimpleNamespace

import pytest
from rescs.errors import StorageError
from rescs.storage.s3 import S3ObjectStore


def test_sdk_timeouts_are_bounded_and_outage_is_not_absence(monkeypatch):
    seen = {}
    class Object:
        def load(self): raise OSError("offline")
    bucket = SimpleNamespace(Object=lambda key: Object())
    def resource(*args, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(Bucket=lambda name: bucket)
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(resource=resource))
    monkeypatch.setitem(sys.modules, "botocore.config", SimpleNamespace(Config=lambda **kwargs: kwargs))
    store = S3ObjectStore(bucket="bucket")
    assert seen["config"] == {"connect_timeout": 5, "read_timeout": 10, "retries": {"max_attempts": 1, "mode": "standard"}}
    with pytest.raises(StorageError, match="availability"):
        store.exists("key")


def test_s3_known_missing_key_is_absent():
    class Missing(Exception):
        response = {"Error": {"Code": "404"}}
    class Object:
        def load(self): raise Missing()
    store = object.__new__(S3ObjectStore)
    store._bucket = SimpleNamespace(Object=lambda key: Object())
    store._prefix = ""
    assert store.exists("key") is False
