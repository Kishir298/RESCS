"""Resumable upload API: sessions, chunks, finalize, cancel."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response

from rescs.api.deps import get_services
from rescs.config import Settings
from rescs.api.deps import get_settings
from rescs.schemas.file_object import FileObjectRead
from rescs.schemas.upload import UploadCreate, UploadRead
from rescs.security import assert_principal_is_owner, enforce_owner, require_api_key
from rescs.services.factory import Services

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", status_code=201, response_model=UploadRead)
def create_upload(
    payload: UploadCreate,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> UploadRead:
    owner = enforce_owner(requested=payload.owner, principal=principal, settings=settings)
    session = services.uploads.create(
        owner=owner,
        filename=payload.filename,
        content_type=payload.content_type,
        total_size=payload.total_size,
        chunk_size=payload.chunk_size,
        checksum=payload.checksum,
        metadata=payload.metadata,
        tags=payload.tags,
        actor=principal,
    )
    return UploadRead.from_domain(session)


@router.get("/{session_id}", response_model=UploadRead)
def get_upload(
    session_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> UploadRead:
    session = services.uploads.get(session_id)
    assert_principal_is_owner(record_owner=session.owner, principal=principal, settings=settings)
    return UploadRead.from_domain(session)


@router.put("/{session_id}/chunks", response_model=UploadRead)
async def put_chunk(
    session_id: str,
    request: Request,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
    content_range: str | None = Header(default=None, alias="Content-Range"),
    offset: int | None = None,
) -> UploadRead:
    # Owner check before reading body.
    session = services.uploads.get(session_id)
    assert_principal_is_owner(record_owner=session.owner, principal=principal, settings=settings)
    if offset is None and content_range:
        # Accept "bytes <offset>-<end>/<total>" — use start offset.
        try:
            units, _, rng = content_range.partition(" ")
            start_end, _, _total = (rng or content_range).partition("/")
            start, _, _end = start_end.partition("-")
            offset = int(start.strip())
        except ValueError:
            offset = None
    query_offset = request.query_params.get("offset")
    if offset is None and query_offset is not None:
        try:
            offset = int(query_offset)
        except ValueError:
            offset = None
    if offset is None:
        from rescs.errors import InvalidRequestError

        raise InvalidRequestError("chunk offset required (?offset= or Content-Range)", details={})
    data = await request.body()
    updated = services.uploads.put_chunk(session_id, offset, data, actor=principal)
    return UploadRead.from_domain(updated)


@router.post("/{session_id}/finalize", response_model=FileObjectRead)
def finalize_upload(
    session_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> FileObjectRead:
    session = services.uploads.get(session_id)
    assert_principal_is_owner(record_owner=session.owner, principal=principal, settings=settings)
    file_obj = services.uploads.finalize(session_id, actor=principal)
    return FileObjectRead.from_domain(file_obj)


@router.delete("/{session_id}", status_code=204)
def cancel_upload(
    session_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> None:
    # Fetch for owner check; cancel is idempotent-ish (404 if unknown).
    # Never cancel blindly: an unknown/expired id must not delete another
    # owner's chunks as a side effect. If get fails, surface 404 without
    # touching storage.
    session = services.uploads.get(session_id)
    assert_principal_is_owner(record_owner=session.owner, principal=principal, settings=settings)
    services.uploads.cancel(session_id, actor=principal)
