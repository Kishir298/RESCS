"""Pydantic schemas for record storage operations."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rescs.domain import RecordData, ensure_utc


def _is_json_serializable(value: Any) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True


class _JsonFieldMixin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _payloads_must_be_json(self):
        for field_name in ("value", "metadata"):
            value = getattr(self, field_name, None)
            if value is not None and not _is_json_serializable(value):
                raise ValueError(
                    f"{field_name} contains values that are not JSON-serializable"
                )
        return self


class RecordCreate(_JsonFieldMixin):
    namespace: str = Field(default="default", max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    key: str = Field(min_length=1, max_length=512)
    value: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="system", min_length=1, max_length=256)
    idempotency_key: str | None = Field(default=None, max_length=128)


class RecordUpdate(_JsonFieldMixin):
    value: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    namespace: str | None = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    key: str | None = Field(default=None, min_length=1, max_length=512)


class RecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    namespace: str
    key: str
    value: dict[str, Any]
    metadata: dict[str, Any]
    owner: str
    version: int
    idempotency_key: str | None = None
    etag: str
    created_at: Any
    updated_at: Any

    @classmethod
    def from_domain(cls, data: RecordData) -> RecordRead:
        return cls(**data.to_dict())


class RecordPage(BaseModel):
    items: list[RecordRead]
    total: int
    limit: int
    offset: int