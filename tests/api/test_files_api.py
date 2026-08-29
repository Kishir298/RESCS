"""File API endpoint tests."""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

BASE = "/api/v1/files"


def test_upload_and_metadata(client: TestClient):
    data = b"file-content-bytes"
    response = client.post(
        BASE, files={"upload": ("notes.txt", data, "text/plain")}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["mime_type"] == "text/plain"
    assert body["size"] == len(data)
    assert body["sha256"] == hashlib.sha256(data).hexdigest()
    assert body["version"] == 1


def test_metadata_lookup(client: TestClient):
    created = client.post(BASE, files={"upload": ("a.bin", b"x", None)}).json()
    response = client.get(f"{BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_download_content(client: TestClient):
    data = b"payload"
    created = client.post(BASE, files={"upload": ("p.bin", data, "application/octet-stream")}).json()
    response = client.get(f"{BASE}/{created['id']}/content")
    assert response.status_code == 200
    assert response.content == data
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["etag"]
    assert response.headers["x-file-sha256"] == created["sha256"]


def test_missing_file(client: TestClient):
    assert client.get(f"{BASE}/no-id").status_code == 404
    assert client.get(f"{BASE}/no-id/content").status_code == 404


def test_delete_file(client: TestClient):
    created = client.post(BASE, files={"upload": ("d.txt", b"x", "text/plain")}).json()
    response = client.delete(f"{BASE}/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"{BASE}/{created['id']}").status_code == 404


def test_list_files(client: TestClient):
    client.post(BASE, files={"upload": ("one.txt", b"1", "text/plain")})
    client.post(BASE, files={"upload": ("two.txt", b"2", "text/plain")})
    response = client.get(BASE)
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_upload_requires_file(client: TestClient):
    response = client.post(BASE)
    assert response.status_code == 422