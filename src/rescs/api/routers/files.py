"""File storage API endpoints.

Bytes are transported as multipart uploads / binary downloads; metadata is
JSON. Files are addressed by their stable id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from rescs.api.deps import get_services
from rescs.schemas.file_object import FileObjectCreate, FileObjectPage, FileObjectRead
from rescs.services.factory import Services

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=201, response_model=FileObjectRead)
async def upload_file(
    upload: UploadFile = File(...),
    services: Services = Depends(get_services),
) -> FileObjectRead:
    data = await upload.read()
    payload = FileObjectCreate(filename=upload.filename or "unnamed")
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
    owner: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> FileObjectPage:
    page = services.files.list(owner=owner, limit=limit, offset=offset)
    return FileObjectPage(
        items=[FileObjectRead.from_domain(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{file_id}", response_model=FileObjectRead)
def get_file_metadata(
    file_id: str,
    services: Services = Depends(get_services),
) -> FileObjectRead:
    return FileObjectRead.from_domain(services.files.get(file_id))


@router.get("/{file_id}/content")
def download_file(
    file_id: str,
    services: Services = Depends(get_services),
) -> Response:
    meta, data = services.files.download(file_id)
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
) -> None:
    services.files.delete(file_id)