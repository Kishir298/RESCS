"""API key authentication and owner-scoping tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rescs.config import Settings
from rescs.main import create_app

RECORDS = "/api/v1/records"
SCOPED_KEY = "scoped-tenant-key-0123456789abcdef"


@pytest.fixture()
def scoped_app(settings: Settings):
    scoped_settings = Settings(
        _env_file=None,
        api_key=SCOPED_KEY,
        api_key_owner="tenant-a",
        database_url="sqlite+pysqlite:///:memory:",
        storage_dir="rescs_test_storage",
        environment="test",
    )
    return create_app(settings=scoped_settings)


@pytest.fixture()
def scoped_client(scoped_app):
    with TestClient(
        scoped_app, headers={"X-API-Key": SCOPED_KEY}
    ) as test_client:
        yield test_client


def _record(owner: str = "system"):
    return {"namespace": "default", "key": "k", "value": {"v": 1}, "owner": owner}


def test_missing_key_rejected(client: TestClient):
    response = client.post(RECORDS, json=_record(), headers={"X-API-Key": ""})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_key_rejected(client: TestClient):
    response = client.get(RECORDS, headers={"X-API-Key": "definitely-wrong"})
    assert response.status_code == 401


def test_valid_key_allowed(client: TestClient):
    assert client.post(RECORDS, json=_record()).status_code == 201


def test_health_endpoints_open(client: TestClient):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_scoped_owner_lock_rejects_other_owner(scoped_client: TestClient):
    response = scoped_client.post(RECORDS, json=_record(owner="tenant-b"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_scoped_owner_matches(scoped_client: TestClient):
    response = scoped_client.post(RECORDS, json=_record(owner="tenant-a"))
    assert response.status_code == 201
    assert response.json()["owner"] == "tenant-a"


def test_scoped_list_forces_owner(scoped_client: TestClient):
    scoped_client.post(RECORDS, json=_record(owner="tenant-a"))
    response = scoped_client.get(RECORDS)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["owner"] == "tenant-a"


def test_scoped_list_rejects_other_owner_filter(scoped_client: TestClient):
    response = scoped_client.get(RECORDS, params={"owner": "tenant-b"})
    assert response.status_code == 401