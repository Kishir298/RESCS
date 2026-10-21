"""Test script for RES-3: Bulk Destructive Device Authorization"""

import pytest
from rescs.errors import ForbiddenError, UnauthorizedError
from rescs.schemas.record import RecordCreate
from rescs.services.factory import build_services


def test_bulk_delete_device_authorization():
    """RES-3: Bulk delete should apply per-object device authorization."""
    services = build_services(use_memory=True)
    
    # Create records with device-scoped owners
    owner_a = "personal.device.tenant-a.user"
    owner_b = "personal.device.tenant-b.user"
    ns_a = "personal.device.tenant-a.ns"
    ns_b = "personal.device.tenant-b.ns"
    
    # Create record as tenant-a
    payload_a = RecordCreate(namespace=ns_a, key="k1", owner=owner_a, value={"v": 1})
    record_a = services.records.create(payload_a)
    
    # Create record as tenant-b
    payload_b = RecordCreate(namespace=ns_b, key="k2", owner=owner_b, value={"v": 2})
    record_b = services.records.create(payload_b)
    
    # Try bulk delete as tenant-a - should succeed for tenant-a's record, fail for tenant-b's
    operations = [
        {"op": "delete", "id": record_a.id},
        {"op": "delete", "id": record_b.id},
    ]
    results = services.records.bulk(operations, actor="system", device_id="tenant-a")
    
    # First should succeed, second should fail with FORBIDDEN
    assert results[0]["status"] == "deleted"
    assert results[1]["status"] == "error"
    assert results[1]["code"] == "UNAUTHORIZED"  # or FORBIDDEN
    
    # Record A should be deleted, Record B should still exist
    with pytest.raises(Exception):
        services.records.get(record_a.id)
    fetched_b = services.records.get(record_b.id)
    assert fetched_b.id == record_b.id
    print("✓ Bulk delete applies per-object device authorization")


def test_bulk_restore_device_authorization():
    """RES-3: Bulk restore should apply per-object device authorization."""
    services = build_services(use_memory=True)
    
    owner_a = "personal.device.tenant-a.user"
    owner_b = "personal.device.tenant-b.user"
    ns_a = "personal.device.tenant-a.ns"
    ns_b = "personal.device.tenant-b.ns"
    
    # Create and delete record as tenant-a
    payload_a = RecordCreate(namespace=ns_a, key="k1", owner=owner_a, value={"v": 1})
    record_a = services.records.create(payload_a)
    services.records.delete(record_a.id)
    
    # Create and delete record as tenant-b
    payload_b = RecordCreate(namespace=ns_b, key="k2", owner=owner_b, value={"v": 2})
    record_b = services.records.create(payload_b)
    services.records.delete(record_b.id)
    
    # Try bulk restore as tenant-a
    operations = [
        {"op": "restore", "id": record_a.id},
        {"op": "restore", "id": record_b.id},
    ]
    results = services.records.bulk(operations, actor="system", device_id="tenant-a")
    
    # First should succeed, second should fail
    assert results[0]["status"] == "restored"
    assert results[1]["status"] == "error"
    assert results[1]["code"] in ("UNAUTHORIZED", "FORBIDDEN")
    
    # Record A should be restored, Record B should still be deleted
    restored_a = services.records.get(record_a.id)
    assert restored_a.deleted_at is None
    with pytest.raises(Exception):
        services.records.get(record_b.id)  # Still deleted
    print("✓ Bulk restore applies per-object device authorization")


def test_bulk_purge_device_authorization():
    """RES-3: Bulk purge should apply per-object device authorization."""
    services = build_services(use_memory=True)
    
    owner_a = "personal.device.tenant-a.user"
    owner_b = "personal.device.tenant-b.user"
    ns_a = "personal.device.tenant-a.ns"
    ns_b = "personal.device.tenant-b.ns"
    
    # Create and delete record as tenant-a
    payload_a = RecordCreate(namespace=ns_a, key="k1", owner=owner_a, value={"v": 1})
    record_a = services.records.create(payload_a)
    services.records.delete(record_a.id)
    
    # Create and delete record as tenant-b
    payload_b = RecordCreate(namespace=ns_b, key="k2", owner=owner_b, value={"v": 2})
    record_b = services.records.create(payload_b)
    services.records.delete(record_b.id)
    
    # Try bulk purge as tenant-a
    operations = [
        {"op": "purge", "id": record_a.id},
        {"op": "purge", "id": record_b.id},
    ]
    results = services.records.bulk(operations, actor="system", device_id="tenant-a")
    
    # First should succeed, second should fail
    assert results[0]["status"] == "purged"
    assert results[1]["status"] == "error"
    assert results[1]["code"] in ("UNAUTHORIZED", "FORBIDDEN")
    
    # Record A should be purged (not found even with get_including_deleted)
    with pytest.raises(Exception):
        services.records.get_including_deleted(record_a.id)
    # Record B should still exist (deleted)
    deleted_b = services.records.get_including_deleted(record_b.id)
    assert deleted_b.deleted_at is not None
    print("✓ Bulk purge applies per-object device authorization")


def test_bulk_preserves_unauthorized_records():
    """RES-3: Unauthorized records in bulk response should be preserved (not deleted/purged)."""
    services = build_services(use_memory=True)
    
    owner_a = "personal.device.tenant-a.user"
    owner_b = "personal.device.tenant-b.user"
    ns_a = "personal.device.tenant-a.ns"
    ns_b = "personal.device.tenant-b.ns"
    
    # Create records
    payload_a = RecordCreate(namespace=ns_a, key="k1", owner=owner_a, value={"v": 1})
    record_a = services.records.create(payload_a)
    payload_b = RecordCreate(namespace=ns_b, key="k2", owner=owner_b, value={"v": 2})
    record_b = services.records.create(payload_b)
    
    # Bulk delete as tenant-a
    operations = [
        {"op": "delete", "id": record_a.id},
        {"op": "delete", "id": record_b.id},
    ]
    results = services.records.bulk(operations, actor="system", device_id="tenant-a")
    
    # Unauthorized record should be preserved
    assert results[1]["status"] == "error"
    fetched_b = services.records.get(record_b.id)
    assert fetched_b.id == record_b.id
    assert fetched_b.value == {"v": 2}
    print("✓ Unauthorized records preserved in bulk response")


def test_bulk_delete_deleted_objects_device_authorization():
    """RES-3: Apply same checks to deleted objects (restore/purge)."""
    services = build_services(use_memory=True)
    
    owner_a = "personal.device.tenant-a.user"
    owner_b = "personal.device.tenant-b.user"
    ns_a = "personal.device.tenant-a.ns"
    ns_b = "personal.device.tenant-b.ns"
    
    # Create and delete records
    payload_a = RecordCreate(namespace=ns_a, key="k1", owner=owner_a, value={"v": 1})
    record_a = services.records.create(payload_a)
    services.records.delete(record_a.id)
    
    payload_b = RecordCreate(namespace=ns_b, key="k2", owner=owner_b, value={"v": 2})
    record_b = services.records.create(payload_b)
    services.records.delete(record_b.id)
    
    # Try bulk restore as tenant-a - should check device auth on deleted objects
    operations = [
        {"op": "restore", "id": record_a.id},
        {"op": "restore", "id": record_b.id},
    ]
    results = services.records.bulk(operations, actor="system", device_id="tenant-a")
    
    assert results[0]["status"] == "restored"
    assert results[1]["status"] == "error"
    print("✓ Device authorization applied to deleted objects in bulk restore")


if __name__ == "__main__":
    test_bulk_delete_device_authorization()
    test_bulk_restore_device_authorization()
    test_bulk_purge_device_authorization()
    test_bulk_preserves_unauthorized_records()
    test_bulk_delete_deleted_objects_device_authorization()
    print("\nAll RES-3 tests passed!")