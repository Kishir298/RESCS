"""Pydantic schemas for file object metadata operations."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rescs.domain import FileObjectData

DEFAULT_MIME_TYPE = "application/octet-stream"


def _is_json_serializable(value: Any) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True


class _FileJsonMixin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _metadata_must_be_json(self):
        if not _is_json_serializable(self.metadata):
            raise ValueError("metadata contains values that are not JSON-serializable")
        return self


class FileObjectCreate(_FileJsonMixin):
    filename: str = Field(min_length=1, max_length=512)
    mime_type: str = Field(default=DEFAULT_MIME_TYPE, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="system", min_length=1, max_length=256)
    idempotency_key: str | None = Field(default=None, max_length=128)


class FileObjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime_type: str
    size: int
    storage_path: str
    sha256: str
    metadata: dict[str, Any]
    owner: str
    version: int
    idempotency_key: str | None = None
    etag: str
    created_at: Any
    updated_at: Any

    @classmethod
    def from_domain(cls, data: FileObjectData) -> FileObjectRead:
        return cls(**data.to_dict())


class FileObjectPage(BaseModel):
    items: list[FileObjectRead]
    total: int
    limit: int
    offset: int