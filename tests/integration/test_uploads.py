"""Integration: resumable uploads (create/chunk/status/finalize/cancel)."""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

UPLOADS = "/api/v1/uploads"
FILES = "/api/v1/files"


def test_upload_lifecycle(client: TestClient):
    data = b"hello-world-" * 1000  # ~12KB
    total = len(data)
    created = client.post(
        UPLOADS,
        json={"filename": "a.bin", "content_type": "application/octet-stream", "total_size": total, "chunk_size": 65536},
    )
    assert created.status_code == 201, created.text
    session = created.json()
    sid = session["id"]
    assert session["received_bytes"] == 0

    # Sequential chunks via ?offset=
    offset = 0
    chunk = 65536
    while offset < total:
        piece = data[offset : offset + chunk]
        r = client.put(f"{UPLOADS}/{sid}/chunks?offset={offset}", content=piece, headers={"Content-Type": "application/octet-stream"})
        assert r.status_code == 200, r.text
        offset += len(piece)

    status = client.get(f"{UPLOADS}/{sid}").json()
    assert status["received_bytes"] == total

    # Duplicate chunk is idempotent.
    dup = client.put(f"{UPLOADS}/{sid}/chunks?offset=0", content=data[:chunk], headers={"Content-Type": "application/octet-stream"})
    assert dup.status_code == 200

    # Finalize publishes a normal file.
    fin = client.post(f"{UPLOADS}/{sid}/finalize")
    assert fin.status_code == 200, fin.text
    meta = fin.json()
    assert meta["size"] == total
    assert meta["sha256"] == hashlib.sha256(data).hexdigest()

    # Download round-trips.
    dl = client.get(f"{FILES}/{meta['id']}/content")
    assert dl.status_code == 200
    assert dl.content == data


def test_upload_validation_and_isolation(client: TestClient, scoped_client: TestClient):
    # Invalid chunk size rejected.
    bad = client.post(UPLOADS, json={"filename": "x", "total_size": 10, "chunk_size": 10})
    assert bad.status_code == 422
    # Oversized chunk offset rejected.
    s = client.post(UPLOADS, json={"filename": "y", "total_size": 10}).json()
    over = client.put(f"{UPLOADS}/{s['id']}/chunks?offset=999", content=b"zz", headers={"Content-Type": "application/octet-stream"})
    assert over.status_code in (400, 422)
    # Cross-owner access denied: scoped client cannot read first client's session.
    other = scoped_client.get(f"{UPLOADS}/{s['id']}")
    assert other.status_code in (401, 403, 404)


def test_upload_cancel(client: TestClient):
    s = client.post(UPLOADS, json={"filename": "c.bin", "total_size": 5}).json()
    sid = s["id"]
    r = client.put(f"{UPLOADS}/{sid}/chunks?offset=0", content=b"hello", headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 200
    c = client.delete(f"{UPLOADS}/{sid}")
    assert c.status_code == 204
    assert client.get(f"{UPLOADS}/{sid}").status_code == 404


def test_upload_checksum_mismatch(client: TestClient):
    data = b"abcde"
    s = client.post(
        UPLOADS, json={"filename": "k.bin", "total_size": len(data), "checksum": "0" * 64}
    ).json()
    client.put(f"{UPLOADS}/{s['id']}/chunks?offset=0", content=data, headers={"Content-Type": "application/octet-stream"})
    fin = client.post(f"{UPLOADS}/{s['id']}/finalize")
    assert fin.status_code in (400, 422)
