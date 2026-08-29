"""File storage API endpoints.

Bytes are transported as multipart uploads / binary downloads; metadata is
JSON. Files are addressed by their stable id. All routes require a valid
``X-API-Key``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile

from rescs.api.deps import get_settings, get_services
from rescs.config import Settings
from rescs.schemas.file_object import FileObjectCreate, FileObjectPage, FileObjectRead
from rescs.security import (
    assert_principal_is_owner,
    enforce_owner,
    require_api_key,
    scoped_query_owner,
)
from rescs.services.factory import Services

router = APIRouter(
    prefix="/files",
    tags=["files"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", status_code=201, response_model=FileObjectRead)
async def upload_file(
    upload: UploadFile = File(...),
    owner: str = Form(default="system"),
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> FileObjectRead:
    data = await upload.read()
    payload = FileObjectCreate(filename=upload.filename or "unnamed")
    payload.owner = enforce_owner(
        requested=owner, principal=principal, settings=settings
    )
    mime_type = _sniff_mime(upload.content_type)
    if mime_type != "application/octet-stream":
        payload.mime_type = mime_type
    return FileObjectRead.from_domain(services.files.create(payload, data))


def _sniff_mime(content_type: str | None) -> str:
    if not content_type:
        return "application/octet-stream"
    return content_type.split(";")[0].strip()


@router.get("", response_model=FileObjectPage)
def list_files(
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
    owner: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> FileObjectPage:
    owner = scoped_query_owner(owner=owner, principal=principal, settings=settings)
    page = services.files.list(owner=owner, limit=limit, offset=offset)
    return FileObjectPage(
        items=[FileObjectRead.from_domain(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


def _authorized_file(
    services: Services,
    file_id: str,
    *,
    principal: str,
    settings: Settings,
) -> object:
    meta = services.files.get(file_id)
    assert_principal_is_owner(
        record_owner=meta.owner, principal=principal, settings=settings
    )
    return meta


@router.get("/{file_id}", response_model=FileObjectRead)
def get_file_metadata(
    file_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> FileObjectRead:
    return FileObjectRead.from_domain(
        _authorized_file(services, file_id, principal=principal, settings=settings)
    )


@router.get("/{file_id}/content")
def download_file(
    file_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> Response:
    meta = _authorized_file(
        services, file_id, principal=principal, settings=settings
    )
    _meta, data = services.files.download(file_id)
    return Response(
        content=data,
        media_type=meta.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{meta.filename}\"",
            "X-File-SHA256": meta.sha256,
            "X-File-Size": str(meta.size),
            "ETag": f'"{meta.etag}"',
        },
    )


@router.delete("/{file_id}", status_code=204)
def delete_file(
    file_id: str,
    services: Services = Depends(get_services),
    settings: Settings = Depends(get_settings),
    principal: str = Depends(require_api_key),
) -> None:
    _authorized_file(services, file_id, principal=principal, settings=settings)
    services.files.delete(file_id)