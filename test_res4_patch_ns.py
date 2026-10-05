"""Test script for RES-4: PATCH Namespace Validation"""

import pytest
from rescs.errors import UnauthorizedError, ForbiddenError
from rescs.schemas.record import RecordCreate, RecordUpdate
from rescs.services.factory import build_services


def test_patch_namespace_reserved_rejected():
    """RES-4: PATCH to reserved namespace rejected."""
    services = build_services(use_memory=True)
    
    # Create a record with non-system owner
    payload = RecordCreate(namespace="default", key="k", value={"v": 1}, owner="owner1")
    record = services.records.create(payload)
    
    # Try to move to reserved namespace
    update = RecordUpdate(namespace="core.private.secret")
    with pytest.raises(UnauthorizedError) as exc:
        services.records.update(record.id, update)
    assert "reserved namespace" in str(exc.value).lower()
    print("✓ PATCH to reserved namespace rejected")


def test_patch_namespace_device_scope_enforced():
    """RES-4: PATCH namespace validated against device scope."""
    services = build_services(use_memory=True)
    
    # Create record in device's namespace
    owner = "personal.device.tenant-a.user"
    ns = "personal.device.tenant-a.ns"
    payload = RecordCreate(namespace=ns, key="k", value={"v": 1}, owner=owner)
    record = services.records.create(payload)
    
    # Try to move to another device's namespace - should fail
    update = RecordUpdate(namespace="personal.device.other-device.new-ns")
    with pytest.raises(UnauthorizedError) as exc:
        services.records.update(record.id, update, device_id="tenant-a")
    assert "cannot update record namespace" in str(exc.value).lower() or "unauthorized" in str(exc.value).lower()
    print("✓ PATCH to another device's namespace rejected")
    
    # Move within same device's namespace - should succeed
    update2 = RecordUpdate(namespace="personal.device.tenant-a.allowed-ns")
    updated = services.records.update(record.id, update2, device_id="tenant-a")
    assert updated.namespace == "personal.device.tenant-a.allowed-ns"
    print("✓ PATCH within same device's namespace succeeds")


def test_patch_namespace_non_device_scoped():
    """RES-4: PATCH namespace for non-device-scoped records."""
    services = build_services(use_memory=True)
    
    # Create record with non-device-scoped owner
    payload = RecordCreate(namespace="default", key="k", value={"v": 1}, owner="owner1")
    record = services.records.create(payload)
    
    # Move to another non-reserved namespace - should succeed
    update = RecordUpdate(namespace="another-ns")
    updated = services.records.update(record.id, update)
    assert updated.namespace == "another-ns"
    print("✓ PATCH non-device-scoped namespace succeeds")
    
    # Move to reserved namespace - should fail
    update2 = RecordUpdate(namespace="core.private.secret")
    with pytest.raises(UnauthorizedError):
        services.records.update(record.id, update2)
    print("✓ PATCH non-device-scoped to reserved namespace rejected")


def test_patch_key_change_device_scope():
    """RES-4: PATCH key change should also be validated."""
    services = build_services(use_memory=True)
    
    # Create record in device's namespace
    owner = "personal.device.tenant-a.user"
    ns = "personal.device.tenant-a.ns"
    payload = RecordCreate(namespace=ns, key="k1", value={"v": 1}, owner=owner)
    record = services.records.create(payload)
    
    # Change key within same namespace - should succeed
    update = RecordUpdate(key="k2")
    updated = services.records.update(record.id, update, device_id="tenant-a")
    assert updated.key == "k2"
    assert updated.namespace == ns
    print("✓ PATCH key change within same namespace succeeds")


def test_patch_namespace_preserves_trusted_service():
    """RES-4: Preserve trusted-service semantics (system owner can access reserved)."""
    services = build_services(use_memory=True)
    
    # Create record as system owner
    payload = RecordCreate(namespace="default", key="k", value={"v": 1}, owner="system")
    record = services.records.create(payload)
    
    # System owner should be able to move to reserved namespace
    update = RecordUpdate(namespace="core.private.secret")
    updated = services.records.update(record.id, update)
    assert updated.namespace == "core.private.secret"
    print("✓ System owner can access reserved namespace")


if __name__ == "__main__":
    test_patch_namespace_reserved_rejected()
    test_patch_namespace_device_scope_enforced()
    test_patch_namespace_non_device_scoped()
    test_patch_key_change_device_scope()
    test_patch_namespace_preserves_trusted_service()
    print("\nAll RES-4 tests passed!")