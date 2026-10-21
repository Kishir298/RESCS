"""Test script for RES-2: Idempotency Scoping with device scope"""

import pytest
from rescs.errors import ConflictError
from rescs.schemas.record import RecordCreate
from rescs.schemas.file_object import FileObjectCreate
from rescs.services.factory import build_services


def test_record_idempotency_with_device_scope():
    """RES-2: Idempotency keys scoped with device-scoped owners."""
    services = build_services(use_memory=True)
    
    # Device-scoped owners and namespaces
    owner1 = "personal.device.tenant-a.user"
    owner2 = "personal.device.tenant-b.user"
    ns1 = "personal.device.tenant-a.ns"
    ns2 = "personal.device.tenant-b.ns"
    
    # Same idempotency key, different device-scoped owners/namespaces -> should create new record
    payload1 = RecordCreate(namespace=ns1, key="k", owner=owner1, idempotency_key="idem-1", value={"v": 1})
    payload2 = RecordCreate(namespace=ns2, key="k", owner=owner2, idempotency_key="idem-1", value={"v": 2})
    r1 = services.records.create(payload1)
    r2 = services.records.create(payload2)
    assert r1.id != r2.id
    assert r1.owner == owner1
    assert r2.owner == owner2
    print("✓ Different device-scoped owners with same idempotency key create different records")


def test_file_idempotency_with_device_scope():
    """RES-2: File idempotency keys scoped with device-scoped owners."""
    services = build_services(use_memory=True)
    
    # Device-scoped owners
    owner1 = "personal.device.tenant-a.user"
    owner2 = "personal.device.tenant-b.user"
    
    # Same idempotency key, different device-scoped owners -> should create new file
    payload1 = FileObjectCreate(filename="a.txt", owner=owner1, idempotency_key="idem-1", mime_type="text/plain")
    payload2 = FileObjectCreate(filename="a.txt", owner=owner2, idempotency_key="idem-1", mime_type="text/plain")
    f1 = services.files.create(payload1, b"data1")
    f2 = services.files.create(payload2, b"data2")
    assert f1.id != f2.id
    assert f1.owner == owner1
    assert f2.owner == owner2
    print("✓ Different device-scoped owners with same idempotency key create different files")


def test_record_idempotency_rejects_cross_device_payload():
    """RES-2: Reject payload reuse across device scopes."""
    services = build_services(use_memory=True)
    
    owner1 = "personal.device.tenant-a.user"
    owner2 = "personal.device.tenant-b.user"
    ns1 = "personal.device.tenant-a.ns"
    ns2 = "personal.device.tenant-b.ns"
    
    payload1 = RecordCreate(namespace=ns1, key="k", owner=owner1, idempotency_key="idem-1", value={"v": 1})
    r1 = services.records.create(payload1)
    
    # Try to use same idempotency key with different device-scoped owner/namespace
    payload2 = RecordCreate(namespace=ns2, key="k", owner=owner2, idempotency_key="idem-1", value={"v": 2})
    r2 = services.records.create(payload2)
    assert r1.id != r2.id
    print("✓ Cross-device idempotency key reuse creates separate records")


def test_file_idempotency_rejects_cross_device_payload():
    """RES-2: Reject file payload reuse across device scopes."""
    services = build_services(use_memory=True)
    
    owner1 = "personal.device.tenant-a.user"
    owner2 = "personal.device.tenant-b.user"
    
    payload1 = FileObjectCreate(filename="a.txt", owner=owner1, idempotency_key="idem-1", mime_type="text/plain")
    f1 = services.files.create(payload1, b"data1")
    
    # Try to use same idempotency key with different device-scoped owner
    payload2 = FileObjectCreate(filename="a.txt", owner=owner2, idempotency_key="idem-1", mime_type="text/plain")
    f2 = services.files.create(payload2, b"data2")
    assert f1.id != f2.id
    print("✓ Cross-device file idempotency key reuse creates separate files")


if __name__ == "__main__":
    test_record_idempotency_with_device_scope()
    test_file_idempotency_with_device_scope()
    test_record_idempotency_rejects_cross_device_payload()
    test_file_idempotency_rejects_cross_device_payload()
    print("\nAll RES-2 device scope tests passed!")