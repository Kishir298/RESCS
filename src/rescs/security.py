"""API key authentication and owner/scope enforcement."""

from __future__ import annotations

import hmac

from fastapi import Depends, Header, Request

from rescs.api.deps import get_settings
from rescs.config import Settings
from rescs.errors import ForbiddenError, UnauthorizedError

SYSTEM_OWNER = "system"

API_KEY_HEADER = "X-API-Key"


def authenticate_api_key(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """Verify the ``X-API-Key`` header and return the authenticated owner.

    A single shared key is configured via ``RESCS_API_KEY``. When
    ``RESCS_API_KEY_OWNER`` is set, requests are locked to that owner; the
    returned value is the principal later used for scoping.
    """
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise UnauthorizedError(
            f"a valid {API_KEY_HEADER} header is required",
            details={"header": API_KEY_HEADER},
        )
    return settings.api_key_owner or SYSTEM_OWNER


def enforce_owner(
    *,
    requested: str | None,
    principal: str,
    settings: Settings,
    field: str = "owner",
) -> str:
    """Resolve the effective owner for a write request, enforcing scope."""
    if settings.api_key_owner:
        if requested and requested != settings.api_key_owner:
            raise UnauthorizedError(
                f"cannot act as owner {requested!r}; locked to "
                f"{settings.api_key_owner!r}",
                details={field: requested},
            )
        return settings.api_key_owner
    return requested or principal


def scoped_query_owner(
    *,
    owner: str | None,
    principal: str,
    settings: Settings,
) -> str | None:
    """Resolve the owner filter for list requests, enforcing scope."""
    if settings.api_key_owner:
        if owner and owner != settings.api_key_owner:
            raise UnauthorizedError(
                f"cannot filter by owner {owner!r}; locked to "
                f"{settings.api_key_owner!r}",
                details={"owner": owner},
            )
        return settings.api_key_owner
    return owner or principal


def assert_principal_is_owner(
    *,
    record_owner: str,
    principal: str,
    settings: Settings,
) -> None:
    """Guard reads/deletes of another owner's resource when scoped."""
    if settings.api_key_owner and record_owner != settings.api_key_owner:
        raise ForbiddenError(
            f"this resource belongs to owner {record_owner!r}",
            details={"owner": record_owner},
        )


def require_api_key(principal: str = Depends(authenticate_api_key)) -> str:
    """FastAPI dependency marker for routes that must be authenticated."""
    return principal