"""Health endpoint API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_meta(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "RESCS"
    assert body["version"] == "0.1.0"
    assert body["docs"] == "/docs"


def test_health_live(client: TestClient):
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "alive"
    assert body["service"] == "RESCS"


def test_health_ready(client: TestClient):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {}


def test_health_summary(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "RESCS"