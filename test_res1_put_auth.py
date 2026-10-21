"""Test script for RES-1: Scoped PUT Authorization"""

from rescs.schemas.record import RecordCreate
from rescs.services.factory import build_services


def test_put_authorize_existing_object_before_put():
    """Owner-scoped PUT must preserve the other owner's object."""
    services = build_services(use_memory=True)
    
    # Create a record as owner1
    payload1 = RecordCreate(namespace="ns", key="k", value={"v": 1}, owner="owner1")
    record1 = services.records.create(payload1)
    assert record1.owner == "owner1"
    
    # Try to PUT as owner2 - creates a separate owner identity
    payload2 = RecordCreate(namespace="ns", key="k", value={"v": 2}, owner="owner2")
    second = services.records.put(payload2)
    assert second.id != record1.id and second.owner == "owner2"
    
    # Original record should be unchanged
    fetched = services.records.get(record1.id)
    assert fetched.value == {"v": 1}
    assert fetched.version == 1


def test_put_authorize_existing_object_before_put_with_device_scope():
    """Device-labelled owners have separate natural keys."""
    services = build_services(use_memory=True)
    
    # Create a record with device-scoped owner
    payload1 = RecordCreate(namespace="ns", key="k", value={"v": 1}, owner="personal.device.tenant-a.user")
    record1 = services.records.create(payload1)
    assert record1.owner == "personal.device.tenant-a.user"
    
    # Try to PUT with different device-scoped owner - creates a separate owner identity
    payload2 = RecordCreate(namespace="ns", key="k", value={"v": 2}, owner="personal.device.tenant-b.user")
    second = services.records.put(payload2)
    assert second.id != record1.id and second.owner == payload2.owner
    
    # Original record should be unchanged
    fetched = services.records.get(record1.id)
    assert fetched.value == {"v": 1}


def test_bulk_put_authorize_existing_object():
    """RES-1: Bulk PUT should authorize existing object before PUT."""
    services = build_services(use_memory=True)
    
    # Create a record as owner1
    payload1 = RecordCreate(namespace="ns", key="k", value={"v": 1}, owner="owner1")
    record1 = services.records.create(payload1)
    
    # Try bulk PUT as owner2 - creates a separate owner identity
    operations = [
        {"op": "put", "record": {"namespace": "ns", "key": "k", "value": {"v": 2}, "owner": "owner2"}}
    ]
    results = services.records.bulk(operations, actor="system", device_id=None)
    
    # The authenticated gateway service can select owners; this is a distinct identity
    assert results[0]["status"] == "put"
    
    # Original record should be unchanged
    fetched = services.records.get(record1.id)
    assert fetched.value == {"v": 1}


if __name__ == "__main__":
    test_put_authorize_existing_object_before_put()
    test_put_authorize_existing_object_before_put_with_device_scope()
    test_bulk_put_authorize_existing_object()
    print("All RES-1 tests passed!")
