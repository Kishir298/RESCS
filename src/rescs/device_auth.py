"""Device-scoped access validation utilities.

This module provides device-scoped access validation utilities that can be
used across RESCS services without creating circular imports.
"""

from __future__ import annotations

from rescs.errors import UnauthorizedError

# Reserved namespace prefixes that cannot be accessed by devices
RESERVED_NAMESPACE_PREFIXES = ("core.", "rescs.", "asis.", "tiviss.")
# Device-scoped namespace prefix
DEVICE_NAMESPACE_PREFIX = "personal.device."


def extract_device_id_from_namespace(namespace: str) -> str | None:
    """Extract device_id from a device-scoped namespace, or None if not device-scoped."""
    if namespace.startswith(DEVICE_NAMESPACE_PREFIX):
        remainder = namespace[len(DEVICE_NAMESPACE_PREFIX):]
        device_id = remainder.split(".", 1)[0]
        return device_id if device_id else None
    return None


def extract_device_id_from_owner(owner: str) -> str | None:
    """Extract device_id from a device-scoped owner, or None if not device-scoped."""
    if owner.startswith(DEVICE_NAMESPACE_PREFIX):
        remainder = owner[len(DEVICE_NAMESPACE_PREFIX):]
        device_id = remainder.split(".", 1)[0]
        return device_id if device_id else None
    return None


def validate_device_namespace(
    namespace: str,
    device_id: str,
    operation: str = "access",
) -> str:
    """
    Validate and transform a namespace for device-scoped access.

    Args:
        namespace: The requested namespace
        device_id: The requesting device's ID
        operation: Description of operation for error messages

    Returns:
        The validated (possibly transformed) namespace

    Raises:
        UnauthorizedError: If access is denied
    """
    # Check for reserved namespace access
    for prefix in RESERVED_NAMESPACE_PREFIXES:
        if namespace.startswith(prefix):
            raise UnauthorizedError(
                f"cannot {operation} reserved namespace '{namespace}'",
                details={"namespace": namespace, "device_id": device_id},
            )

    expected_prefix = f"{DEVICE_NAMESPACE_PREFIX}{device_id}."

    # If already device-scoped, verify it matches this device
    if namespace.startswith(DEVICE_NAMESPACE_PREFIX):
        if not namespace.startswith(expected_prefix):
            raise UnauthorizedError(
                f"cannot {operation} another device's namespace",
                details={"namespace": namespace, "device_id": device_id},
            )
        return namespace

    # Otherwise, prefix with device scope
    return f"{expected_prefix}{namespace}"


def validate_device_owner(
    owner: str | None,
    device_id: str,
    operation: str = "access",
) -> str | None:
    """
    Validate and transform an owner for device-scoped access.

    Args:
        owner: The requested owner (or None)
        device_id: The requesting device's ID
        operation: Description of operation for error messages

    Returns:
        The validated (possibly transformed) owner, or None

    Raises:
        UnauthorizedError: If access is denied
    """
    if owner is None:
        return None

    expected_prefix = f"{DEVICE_NAMESPACE_PREFIX}{device_id}"

    # If already device-scoped, verify it matches this device
    if owner.startswith(DEVICE_NAMESPACE_PREFIX):
        if not owner.startswith(expected_prefix):
            raise UnauthorizedError(
                f"cannot {operation} another device's owner scope",
                details={"owner": owner, "device_id": device_id},
            )
        return owner

    # Otherwise, prefix with device scope
    return f"{expected_prefix}.{owner}"


def assert_device_ownership(
    *,
    resource_owner: str,
    resource_namespace: str,
    device_id: str,
    operation: str = "access",
) -> None:
    """
    Assert that a resource belongs to the requesting device.

    Both owner and namespace must be device-scoped for the same device.
    """
    # Extract device_id from namespace
    ns_device_id = extract_device_id_from_namespace(resource_namespace)
    if ns_device_id != device_id:
        raise UnauthorizedError(
            f"cannot {operation} resource from different device",
            details={
                "resource_namespace": resource_namespace,
                "resource_owner": resource_owner,
                "device_id": device_id,
                "namespace_device_id": ns_device_id,
            },
        )

    # Verify owner matches device scope
    if not resource_owner.startswith(f"{DEVICE_NAMESPACE_PREFIX}{device_id}"):
        raise UnauthorizedError(
            f"cannot {operation} resource with mismatched owner scope",
            details={
                "resource_namespace": resource_namespace,
                "resource_owner": resource_owner,
                "device_id": device_id,
            },
        )


def assert_device_ownership_by_owner(
    *,
    resource_owner: str,
    device_id: str,
    operation: str = "access",
) -> None:
    """
    Assert that a resource's owner belongs to the requesting device.

    Used for resources without a namespace (files, uploads).
    Only validates the owner field.
    """
    if not resource_owner.startswith(f"{DEVICE_NAMESPACE_PREFIX}{device_id}"):
        raise UnauthorizedError(
            f"cannot {operation} resource from different device",
            details={
                "resource_owner": resource_owner,
                "device_id": device_id,
            },
        )