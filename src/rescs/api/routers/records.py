"""Record storage API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from rescs.api.deps import get_settings, get_services
from rescs.config import Settings
from rescs.schemas.record import RecordCreate, RecordPage, RecordRead, RecordUpdate
from rescs.security import (
    assert_principal_is_owner,
    enforce_owner,
    require_api_key,
    scoped_query_owner,
)
from rescs.services.factory import Services

router = APIRouter(
    prefix="/records",
    tags=["records"],
    dependencies=[Depends(require_api_key)],
)


def _page(
    services: Services,
    *,
    namespace: str | None,
    key_prefix: str | None,
    owner: str | None,
    query: str | None,
    limit: int,
    offset: int,
) -> RecordPage:
    if query:
        page = services.records.search(
            query=query,
            namespace=namespace,
            owner=owner,
            limit=limit,
            offset=offset,
        )
    else:
        page = services.records.list(
            namespace=namespace,
            key_prefix=key_prefix,
            owner=owner,
            limit=limit,
            offset=offset,
        )
    return RecordPage(
        items=[RecordRead.from_domain(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", status_code=201, response_model=RecordRead)
def create_record(
    payload: RecordCreate,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> RecordRead:
    payload.owner = enforce_owner(
        requested=payload.owner, principal=principal, settings=settings
    )
    return RecordRead.from_domain(services.records.create(payload))


@router.put("", response_model=RecordRead, summary="Create or replace by namespace/key")
def put_record(
    payload: RecordCreate,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> RecordRead:
    payload.owner = enforce_owner(
        requested=payload.owner, principal=principal, settings=settings
    )
    return RecordRead.from_domain(services.records.put(payload))


@router.get("", response_model=RecordPage)
def list_records(
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
    namespace: str | None = Query(default=None),
    key_prefix: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    query: str | None = Query(default=None, description="Full-text-ish search"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> RecordPage:
    owner = scoped_query_owner(owner=owner, principal=principal, settings=settings)
    return _page(
        services,
        namespace=namespace,
        key_prefix=key_prefix,
        owner=owner,
        query=query,
        limit=limit,
        offset=offset,
    )


def _authorized_record(
    services: Services,
    record_id: str,
    *,
    principal: str,
    settings: Settings,
) -> Any:
    record = services.records.get(record_id)
    assert_principal_is_owner(
        record_owner=record.owner, principal=principal, settings=settings
    )
    return record


@router.get("/{record_id}", response_model=RecordRead)
def get_record(
    record_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> RecordRead:
    return RecordRead.from_domain(
        _authorized_record(
            services, record_id, principal=principal, settings=settings
        )
    )


@router.patch("/{record_id}", response_model=RecordRead)
def update_record(
    record_id: str,
    payload: RecordUpdate,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> RecordRead:
    _authorized_record(services, record_id, principal=principal, settings=settings)
    return RecordRead.from_domain(services.records.update(record_id, payload))


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> None:
    _authorized_record(services, record_id, principal=principal, settings=settings)
    services.records.delete(record_id)