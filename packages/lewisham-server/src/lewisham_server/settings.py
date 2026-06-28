from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from lewisham_server.clients.lewisham.config import (
    BASE_URL,
    COLLECTION_PAGE_URL,
    REQUEST_TIMEOUT_SECONDS,
    ROUNDS_INFORMATION_ITEM_GUID,
    USER_AGENT,
)

LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]
LogFormat = Literal["text", "json"]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables.

    Service-specific variables use the LEWISHAM_SERVER_ prefix. PORT is also
    accepted because many container platforms inject it as the standard bind
    port; LEWISHAM_SERVER_PORT takes precedence when both are set.
    """

    model_config = SettingsConfigDict(
        env_prefix="LEWISHAM_SERVER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Lewisham Council Scraper API"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("LEWISHAM_SERVER_PORT", "PORT"),
    )
    workers: int = Field(default=1, ge=1)
    log_level: LogLevel = "info"
    log_format: LogFormat = "text"
    log_include_raw_upstream: bool = False
    log_raw_upstream_max_chars: int = Field(default=4_096, ge=0)

    upstream_base_url: str = BASE_URL
    upstream_collection_page_url: str = COLLECTION_PAGE_URL
    upstream_rounds_information_item_guid: str = ROUNDS_INFORMATION_ITEM_GUID
    upstream_user_agent: str = USER_AGENT
    upstream_request_timeout_seconds: float = Field(
        default=REQUEST_TIMEOUT_SECONDS,
        gt=0,
    )

    cache_schedule_ttl_seconds: int = Field(default=86_400, ge=1)
    cache_address_search_ttl_seconds: int = Field(default=604_800, ge=1)
    cache_uprn_ttl_seconds: int = Field(default=2_592_000, ge=1)
    cache_negative_ttl_seconds: int = Field(default=3_600, ge=1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings, cached after the first environment read."""

    return Settings()
