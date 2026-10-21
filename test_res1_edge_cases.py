"""Test script for RES-1: Scoped PUT Authorization - edge cases"""

import pytest
from rescs.errors import ForbiddenError, ConflictError
from rescs.schemas.record import RecordCreate
from rescs.services.factory import build_services


def test_put_deleted_record_different_owner():
    """RES-1: PUT on deleted record with different owner should be forbidden."""
    services = build_services(use_memory=True)
    
    # Create a record as owner1
    payload1 = RecordCreate(namespace="ns", key="k", value={"v": 1}, owner="owner1")
    record1 = services.records.create(payload1)
    
    # Delete the record
    services.records.delete(record1.id)
    
    # Try to PUT as owner2 - should this be allowed or forbidden?
    # The issue says "Leave foreign content unchanged on conflict"
    # If the record is deleted, it's not "foreign content" anymore
    # But the tombstone still belongs to owner1
    payload2 = RecordCreate(namespace="ns", key="k", value={"v": 2}, owner="owner2")
    
    # Currently this might succeed because get_by_namespace_key returns None for deleted records
    # Let's see what happens
    try:
        record2 = services.records.put(payload2)
        print(f"PUT succeeded: {record2.id}, owner={record2.owner}, value={record2.value}")
        # Check if original tombstone is preserved or overwritten
        tombstone = services.records.get_including_deleted(record1.id)
        print(f"Original tombstone: deleted_at={tombstone.deleted_at}, owner={tombstone.owner}")
    except ForbiddenError as e:
        print(f"PUT forbidden: {e}")
    except ConflictError as e:
        print(f"PUT conflict: {e}")


def test_put_expired_record_different_owner():
    """RES-1: PUT on expired record with different owner."""
    services = build_services(use_memory=True)
    
    # Create a record with short TTL
    from datetime import datetime, timedelta
    expires_at = datetime.now() - timedelta(seconds=1)  # Already expired
    payload1 = RecordCreate(namespace="ns", key="k", value={"v": 1}, owner="owner1", expires_at=expires_at)
    record1 = services.records.create(payload1)
    
    # Wait a bit and try to PUT as owner2
    import time
    time.sleep(0.1)
    
    payload2 = RecordCreate(namespace="ns", key="k", value={"v": 2}, owner="owner2")
    
    try:
        record2 = services.records.put(payload2)
        print(f"PUT on expired record succeeded: {record2.id}, owner={record2.owner}")
    except ForbiddenError as e:
        print(f"PUT on expired record forbidden: {e}")
    except ConflictError as e:
        print(f"PUT on expired record conflict: {e}")


def test_bulk_put_deleted_record():
    """RES-1: Bulk PUT on deleted record with different owner."""
    services = build_services(use_memory=True)
    
    # Create a record as owner1
    payload1 = RecordCreate(namespace="ns", key="k", value={"v": 1}, owner="owner1")
    record1 = services.records.create(payload1)
    
    # Delete the record
    services.records.delete(record1.id)
    
    # Try bulk PUT as owner2
    operations = [
        {"op": "put", "record": {"namespace": "ns", "key": "k", "value": {"v": 2}, "owner": "owner2"}}
    ]
    results = services.records.bulk(operations, actor="system", device_id=None)
    
    print(f"Bulk PUT result: {results}")
    if results[0]["status"] == "error":
        print(f"Error code: {results[0]['code']}, message: {results[0]['message']}")
    else:
        print(f"Success: {results[0]}")
    
    # Check original tombstone
    tombstone = services.records.get_including_deleted(record1.id)
    print(f"Original tombstone: deleted_at={tombstone.deleted_at}, owner={tombstone.owner}")


if __name__ == "__main__":
    print("=== Test PUT on deleted record ===")
    test_put_deleted_record_different_owner()
    print("\n=== Test PUT on expired record ===")
    test_put_expired_record_different_owner()
    print("\n=== Test Bulk PUT on deleted record ===")
    test_bulk_put_deleted_record()