"""Test script for RES-2: Idempotency Scoping"""

import pytest
from rescs.errors import ConflictError
from rescs.schemas.record import RecordCreate
from rescs.schemas.file_object import FileObjectCreate
from rescs.services.factory import build_services


def test_record_idempotency_scoped_to_owner_namespace_key():
    """RES-2: Idempotency keys scoped to (owner, namespace, key)."""
    services = build_services(use_memory=True)
    
    # Same idempotency key, different owner -> should create new record
    payload1 = RecordCreate(namespace="ns", key="k1", owner="owner1", idempotency_key="idem-1", value={"v": 1})
    payload2 = RecordCreate(namespace="ns", key="k2", owner="owner2", idempotency_key="idem-1", value={"v": 2})
    r1 = services.records.create(payload1)
    r2 = services.records.create(payload2)
    assert r1.id != r2.id
    assert r1.owner == "owner1"
    assert r2.owner == "owner2"
    print("✓ Different owners with same idempotency key create different records")


def test_record_idempotency_scoped_to_namespace_key():
    """RES-2: Idempotency keys scoped to (owner, namespace, key)."""
    services = build_services(use_memory=True)
    
    # Same idempotency key, same owner, different namespace -> should create new record
    payload1 = RecordCreate(namespace="ns1", key="k", owner="owner1", idempotency_key="idem-1", value={"v": 1})
    payload2 = RecordCreate(namespace="ns2", key="k", owner="owner1", idempotency_key="idem-1", value={"v": 2})
    r1 = services.records.create(payload1)
    r2 = services.records.create(payload2)
    assert r1.id != r2.id
    assert r1.namespace == "ns1"
    assert r2.namespace == "ns2"
    print("✓ Different namespaces with same idempotency key create different records")


def test_record_idempotency_scoped_to_key():
    """RES-2: Idempotency keys scoped to (owner, namespace, key)."""
    services = build_services(use_memory=True)
    
    # Same idempotency key, same owner, same namespace, different key -> should create new record
    payload1 = RecordCreate(namespace="ns", key="k1", owner="owner1", idempotency_key="idem-1", value={"v": 1})
    payload2 = RecordCreate(namespace="ns", key="k2", owner="owner1", idempotency_key="idem-1", value={"v": 2})
    r1 = services.records.create(payload1)
    r2 = services.records.create(payload2)
    assert r1.id != r2.id
    assert r1.key == "k1"
    assert r2.key == "k2"
    print("✓ Different keys with same idempotency key create different records")


def test_record_idempotency_rejects_incompatible_payload():
    """RES-2: Incompatible payload reuse returns 409, not foreign data."""
    services = build_services(use_memory=True)
    
    payload1 = RecordCreate(namespace="ns", key="k", owner="owner1", idempotency_key="idem-1", value={"v": 1})
    r1 = services.records.create(payload1)
    
    # Same idempotency key, same owner/namespace/key, different value -> 409
    payload2 = RecordCreate(namespace="ns", key="k", owner="owner1", idempotency_key="idem-1", value={"v": 2})
    with pytest.raises(ConflictError) as exc:
        services.records.create(payload2)
    assert "idempotency key" in exc.value.message.lower()
    
    # Original record unchanged
    fetched = services.records.get(r1.id)
    assert fetched.value == {"v": 1}
    print("✓ Incompatible payload reuse rejected with 409")


def test_record_idempotency_same_payload_returns_existing():
    """RES-2: Same payload with same idempotency key returns existing record."""
    services = build_services(use_memory=True)
    
    payload1 = RecordCreate(namespace="ns", key="k", owner="owner1", idempotency_key="idem-1", value={"v": 1})
    r1 = services.records.create(payload1)
    
    # Same payload -> returns existing
    payload2 = RecordCreate(namespace="ns", key="k", owner="owner1", idempotency_key="idem-1", value={"v": 1})
    r2 = services.records.create(payload2)
    assert r1.id == r2.id
    assert r2.version == 1
    print("✓ Same payload with same idempotency key returns existing record")


def test_file_idempotency_scoped_to_owner_filename():
    """RES-2: File idempotency keys scoped to (owner, filename)."""
    services = build_services(use_memory=True)
    
    # Same idempotency key, different owner -> should create new file
    payload1 = FileObjectCreate(filename="a.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain")
    payload2 = FileObjectCreate(filename="b.txt", owner="owner2", idempotency_key="idem-1", mime_type="text/plain")
    f1 = services.files.create(payload1, b"data1")
    f2 = services.files.create(payload2, b"data2")
    assert f1.id != f2.id
    assert f1.owner == "owner1"
    assert f2.owner == "owner2"
    print("✓ Different owners with same idempotency key create different files")


def test_file_idempotency_scoped_to_filename():
    """RES-2: File idempotency keys scoped to (owner, filename)."""
    services = build_services(use_memory=True)
    
    # Same idempotency key, same owner, different filename -> should create new file
    payload1 = FileObjectCreate(filename="a.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain")
    payload2 = FileObjectCreate(filename="b.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain")
    f1 = services.files.create(payload1, b"data1")
    f2 = services.files.create(payload2, b"data2")
    assert f1.id != f2.id
    assert f1.filename == "a.txt"
    assert f2.filename == "b.txt"
    print("✓ Different filenames with same idempotency key create different files")


def test_file_idempotency_rejects_incompatible_payload():
    """RES-2: File incompatible payload reuse returns 409."""
    services = build_services(use_memory=True)
    
    payload1 = FileObjectCreate(filename="a.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain", metadata={"m": 1})
    f1 = services.files.create(payload1, b"data1")
    
    # Same idempotency key, same owner/filename, different metadata -> 409
    payload2 = FileObjectCreate(filename="a.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain", metadata={"m": 2})
    with pytest.raises(ConflictError) as exc:
        services.files.create(payload2, b"data2")
    assert "idempotency key" in exc.value.message.lower()
    
    # Original file unchanged
    fetched = services.files.get(f1.id)
    assert fetched.metadata == {"m": 1}
    print("✓ File incompatible payload reuse rejected with 409")


def test_file_idempotency_same_payload_returns_existing():
    """RES-2: File same payload with same idempotency key returns existing."""
    services = build_services(use_memory=True)
    
    payload1 = FileObjectCreate(filename="a.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain")
    f1 = services.files.create(payload1, b"data1")
    
    # Same payload -> returns existing
    payload2 = FileObjectCreate(filename="a.txt", owner="owner1", idempotency_key="idem-1", mime_type="text/plain")
    f2 = services.files.create(payload2, b"data1")
    assert f1.id == f2.id
    assert f2.version == 1
    print("✓ File same payload with same idempotency key returns existing")


if __name__ == "__main__":
    test_record_idempotency_scoped_to_owner_namespace_key()
    test_record_idempotency_scoped_to_namespace_key()
    test_record_idempotency_scoped_to_key()
    test_record_idempotency_rejects_incompatible_payload()
    test_record_idempotency_same_payload_returns_existing()
    test_file_idempotency_scoped_to_owner_filename()
    test_file_idempotency_scoped_to_filename()
    test_file_idempotency_rejects_incompatible_payload()
    test_file_idempotency_same_payload_returns_existing()
    print("\nAll RES-2 tests passed!")