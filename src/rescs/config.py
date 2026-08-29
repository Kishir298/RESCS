"""Application configuration loaded from environment variables and ``.env``."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from rescs import __version__

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime configuration for the RESCS application.

    Every value is overridable through an environment variable prefixed
    with ``RESCS_`` (for example ``RESCS_API_KEY``) or through the local
    ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="RESCS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RESCS"
    version: str = __version__
    environment: str = Field(default="development", alias="RESCS_ENV")
    log_level: LogLevel = "INFO"

    api_key: str = ""
    database_url: str = "sqlite:///rescs_dev.db"
    storage_dir: str = "rescs_storage"
    auto_create_schema: bool = True
    request_id_header: str = "X-Request-ID"

    @field_validator("api_key")
    @classmethod
    def _validate_api_key(cls, value: str) -> str:
        if not value or len(value) < 16:
            raise ValueError(
                "RESCS_API_KEY must be set and at least 16 characters long"
            )
        return value

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        if value not in {"development", "test", "production"}:
            raise ValueError(
                f"unknown RESCS_ENV {value!r}; expected development, test or production"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()