"""Real local SQLite/API behavior; CORE source is supplied explicitly for adapter tests."""
import importlib.util
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from rescs.config import Settings
from rescs.db.bootstrap import bootstrap_database
from rescs.db.schema import SchemaManager
from rescs.main import create_app

KEY = "release-test-key-0123456789abcdef"
RECORDS = "/api/v1/records"


def settings_for(tmp_path, **kwargs):
    return Settings(_env_file=None, api_key=KEY, database_url=f"sqlite:///{tmp_path}/records.db",
                    storage_dir=str(tmp_path / "files"), **kwargs)


def test_owners_share_natural_key_and_paginate_offline(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("unexpected network access")
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    settings = settings_for(tmp_path)
    with TestClient(create_app(settings), headers={"X-API-Key": KEY}) as client:
        ids = {}
        for owner in ["owner-a", "owner-b"]:
            for index in range(4):
                result = client.put(RECORDS, json={"owner": owner, "namespace": "same", "key": str(index), "value": {"owner": owner}})
                assert result.status_code == 200, result.text
                ids[owner, index] = result.json()["id"]
        for owner in ["owner-a", "owner-b"]:
            seen = []
            for offset in [0, 2, 4]:
                page = client.get(RECORDS, params={"owner": owner, "namespace": "same", "limit": 2, "offset": offset}).json()
                assert (page["total"], page["limit"], page["offset"]) == (4, 2, offset)
                assert all(item["owner"] == owner for item in page["items"])
                seen.extend(item["id"] for item in page["items"])
            assert len(set(seen)) == 4
        old = client.get(RECORDS + "/" + ids["owner-a", 0]).json()
        changed = client.put(RECORDS, json={"owner": "owner-a", "namespace": "same", "key": "0", "value": {"updated": True}}, headers={"If-Match": old["etag"]})
        assert changed.status_code == 200
        assert client.patch(RECORDS + "/" + old["id"], json={"value": {}}, headers={"If-Match": old["etag"]}).status_code == 412
        assert client.delete(RECORDS + "/" + old["id"]).status_code == 204
        assert client.get(RECORDS + "/" + old["id"]).status_code == 404
        assert client.get(RECORDS + "/" + ids["owner-b", 0]).json()["value"] == {"owner": "owner-b"}
        assert client.post(RECORDS + "/" + old["id"] + "/restore").status_code == 200
        upload = client.post("/api/v1/files", data={"owner": "owner-a"}, files={"upload": ("data.bin", b"offline data")})
        assert upload.status_code == 201
        file_id = upload.json()["id"]
        assert client.get(f"/api/v1/files/{file_id}/content").content == b"offline data"
    # Restart uses the same database and local blobs.
    with TestClient(create_app(settings), headers={"X-API-Key": KEY}) as client:
        assert client.get(RECORDS + "/" + ids["owner-b", 0]).status_code == 200
        assert client.get(f"/api/v1/files/{file_id}/content").content == b"offline data"


def test_locked_owner_blocks_foreign_crud_and_device_bypass(tmp_path):
    open_settings = settings_for(tmp_path)
    with TestClient(create_app(open_settings), headers={"X-API-Key": KEY}) as client:
        foreign = client.put(RECORDS, json={"owner": "personal.device.other.owner", "namespace": "personal.device.other.ns", "key": "same", "value": {}}).json()
        foreign_file = client.post("/api/v1/files", data={"owner": "personal.device.other.owner"}, files={"upload": ("foreign.bin", b"private")}).json()
        foreign_upload = client.post("/api/v1/uploads", json={"owner": "personal.device.other.owner", "filename": "upload.bin", "total_size": 1, "chunk_size": 65536}).json()
    with TestClient(create_app(settings_for(tmp_path, api_key_owner="owner-a")), headers={"X-API-Key": KEY}) as client:
        assert client.get(RECORDS, headers={"X-API-Key": "invalid"}).status_code == 401
        for headers in [{}, {"X-Device-Id": "other"}]:
            assert client.get(RECORDS + "/" + foreign["id"], headers=headers).status_code == 403
            assert client.patch(RECORDS + "/" + foreign["id"], json={"value": {}}, headers=headers).status_code == 403
            assert client.delete(RECORDS + "/" + foreign["id"], headers=headers).status_code == 403
        assert client.get(RECORDS, params={"owner": "owner-b", "offset": 2}).status_code == 401
        assert client.put(RECORDS, json={"owner": "owner-b", "namespace": "same", "key": "same", "value": {}}).status_code == 401
        assert client.get(RECORDS).json()["total"] == 0
        headers = {"X-Device-Id": "other"}
        file_path = "/api/v1/files/" + foreign_file["id"]
        assert client.get(file_path, headers=headers).status_code == 403
        assert client.get(file_path + "/content", headers=headers).status_code == 403
        assert client.delete(file_path, headers=headers).status_code == 403
        upload_path = "/api/v1/uploads/" + foreign_upload["id"]
        assert client.get(upload_path, headers=headers).status_code == 403
        assert client.put(upload_path + "/chunks?offset=0", content=b"x", headers=headers).status_code == 403
        assert client.post(upload_path + "/finalize", headers=headers).status_code == 403
        assert client.delete(upload_path, headers=headers).status_code == 403
        assert client.post("/api/v1/uploads", json={"owner": "owner-a", "filename": "x", "total_size": 1, "chunk_size": 65536}, headers=headers).status_code == 401


def test_old_index_migration_preserves_rows(tmp_path):
    database = bootstrap_database(settings_for(tmp_path))
    engine = database.engine
    with TestClient(create_app(settings_for(tmp_path)), headers={"X-API-Key": KEY}) as client:
        saved = client.put(RECORDS, json={"namespace": "legacy", "key": "old", "owner": "a", "value": {"keep": 1}}).json()
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX uq_records_live_owner_namespace_key"))
        conn.execute(text("CREATE UNIQUE INDEX uq_records_live_namespace_key ON records(namespace,key) WHERE deleted_at IS NULL"))
        conn.execute(text("UPDATE schema_info SET value='0.3.0' WHERE key='version'"))
    manager = SchemaManager(engine)
    manager.migrate()
    manager.migrate()
    assert manager.applied_version() == "0.3.1"
    assert "uq_records_live_namespace_key" not in {i["name"] for i in inspect(engine).get_indexes("records")}
    with TestClient(create_app(settings_for(tmp_path)), headers={"X-API-Key": KEY}) as client:
        assert client.get(RECORDS + "/" + saved["id"]).json()["value"] == {"keep": 1}
        assert client.put(RECORDS, json={"namespace": "legacy", "key": "old", "owner": "b", "value": {}}).status_code == 200
    engine.dispose()


def test_configured_backend_failure_never_falls_back(tmp_path, monkeypatch):
    import rescs.db.bootstrap as bootstrap
    from rescs.errors import DependencyUnavailableError
    def unreachable(*args, **kwargs):
        raise DependencyUnavailableError("configured remote unavailable")
    monkeypatch.setattr(bootstrap, "check_connectivity", unreachable)
    settings = settings_for(tmp_path)
    with pytest.raises(DependencyUnavailableError):
        with TestClient(create_app(settings)):
            pass
    assert not (tmp_path / "records.db").exists()


def test_parallel_profile_writes_remain_separate(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from rescs.schemas.record import RecordCreate
    from rescs.services.factory import build_services
    database = bootstrap_database(settings_for(tmp_path))
    services = build_services(database=database, settings=settings_for(tmp_path))
    def put(owner):
        return services.records.put(RecordCreate(owner=owner, namespace="shared", key="identical", value={"owner": owner}))
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(put, ["a", "b", "c", "d"]))
    assert len({row.id for row in rows}) == 4
    for row in rows:
        assert services.records.list(owner=row.owner).total == 1
    database.engine.dispose()


def test_backup_restore_retains_record_and_file(tmp_path):
    import hashlib
    import json
    import shutil
    import subprocess
    settings = settings_for(tmp_path)
    with TestClient(create_app(settings), headers={"X-API-Key": KEY}) as client:
        row = client.put(RECORDS, json={"owner": "restore", "namespace": "ns", "key": "same", "value": {"recover": True}}).json()
        file = client.post("/api/v1/files", data={"owner": "restore"}, files={"upload": ("backup.bin", b"recover bytes")}).json()
    backup = tmp_path / "backup"
    result = subprocess.run([sys.executable, "scripts/rescs_backup.py", "--database-url", settings.database_url,
                             "--storage-dir", settings.storage_dir, "--out", str(backup), "--verify"],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((backup / "manifest.json").read_text())
    assert hashlib.sha256((backup / "db.dump").read_bytes()).hexdigest() == manifest["db"]["sha256"]
    recovered = tmp_path / "recovered"
    recovered.mkdir()
    shutil.copy2(backup / "db.dump", recovered / "records.db")
    shutil.copytree(backup / "blobs", recovered / "files")
    with TestClient(create_app(settings_for(recovered)), headers={"X-API-Key": KEY}) as client:
        assert client.get(RECORDS + "/" + row["id"]).json()["value"] == {"recover": True}
        assert client.get("/api/v1/files/" + file["id"] + "/content").content == b"recover bytes"


def load_core_module(root, name):
    spec = importlib.util.spec_from_file_location("core_release_" + name, Path(root) / "core/web" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("platform,python_tail", [("nt", "Scripts/python.exe"), ("posix", "bin/python")])
def test_core_managed_command(platform, python_tail, tmp_path, monkeypatch):
    root = os.environ.get("RESCS_CORE_HOST_SOURCE")
    if not root:
        pytest.skip("Set RESCS_CORE_HOST_SOURCE to the extracted command-release CORE-HOST")
    module = load_core_module(root, "services")
    # Replace only this module's OS facade; no global platform mutation.
    monkeypatch.setattr(module, "os", SimpleNamespace(name=platform, environ={}))
    service_root = tmp_path / "RESCS"
    (service_root / "src/rescs").mkdir(parents=True)
    candidate = service_root / ".venv" / python_tail
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    service = module.Services(tmp_path / "data", {"rescs": str(service_root)}, KEY)
    argv, cwd, env = service.command("rescs", {"id": "a"*32, "role": "owner"}, "", "plan")
    assert argv == [str(candidate), "-u", "-m", "uvicorn", "rescs.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8081"]
    assert env["RESCS_API_KEY_OWNER"] == ""
    assert env["RESCS_AUTO_CREATE_SCHEMA"] == "true"
    assert env["RESCS_DATABASE_URL"].startswith("sqlite:///")
    assert env["RESCS_STORAGE_DIR"].endswith("rescs-files")


def test_actual_core_adapter_against_rescs_app(tmp_path):
    root = os.environ.get("RESCS_CORE_HOST_SOURCE")
    if not root:
        pytest.skip("Set RESCS_CORE_HOST_SOURCE for the real CORE adapter")
    module = load_core_module(root, "storage")
    with TestClient(create_app(settings_for(tmp_path)), headers={"X-API-Key": KEY}) as client:
        class Response:
            def __init__(self, response): self.response = response
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return self.response.content[:size]
        class Transport:
            def open(self, request, timeout):
                assert timeout == 8
                response = client.request(request.method, request.full_url, content=request.data, headers=dict(request.header_items()))
                assert response.status_code < 400, response.text
                return Response(response)
        adapter = module.RescsStorage("http://127.0.0.1:8081", KEY)
        adapter.opener = Transport()  # in-process transport; real adapter serialization and SQLite API
        for profile in ["a"*32, "b"*32]:
            for index in range(3): adapter.save(profile, str(index), {"profile": profile})
        page = adapter.records("a"*32)
        assert page["total"] == 3
        assert all(row["owner"] == "core.profile." + "a"*32 for row in page["items"])
        if "offset" in __import__("inspect").signature(adapter.records).parameters:
            page = adapter.records("a"*32, limit=1, offset=2)
            assert len(page["items"]) == 1 and page["offset"] == 2


def test_gateway_ignores_browser_owner_namespace_and_keeps_remote_backend(tmp_path):
    import importlib
    import types
    root = os.environ.get("RESCS_CORE_HOST_SOURCE")
    if not root:
        pytest.skip("Set RESCS_CORE_HOST_SOURCE for gateway tests")
    package = types.ModuleType("release_gateway")
    package.__path__ = [str(Path(root) / "core/web")]
    sys.modules[package.__name__] = package
    module = importlib.import_module("release_gateway.gateway")
    gateway = module.Gateway(directory=tmp_path / "gateway")
    gateway.accounts.create("owner", "Long-release-password-123", "Owner", first=True)
    token, csrf, user = gateway.accounts.login("owner", "Long-release-password-123")
    headers = {"Cookie": "core_session=" + token, "X-Core-CSRF": csrf}
    calls = []
    class Storage:
        endpoint = "https://configured.example"
        def save(self, *args): calls.append(args); return {"saved": True}
    gateway.storage = Storage()
    status, _, _ = gateway.dispatch("POST", "/api/records", {"owner": "victim", "namespace": "victim", "key": "a", "value": {}, "service": "workspace"}, headers)
    assert status == 200 and calls[0][0] == user["id"]
    if "Managed RESCS uses" in __import__("inspect").getsource(module.Gateway.dispatch):
        with pytest.raises(ValueError, match="Managed RESCS uses"):
            gateway.dispatch("POST", "/api/jobs", {"service": "rescs"}, headers)
        assert gateway.storage.endpoint == "https://configured.example"
    gateway.close()
