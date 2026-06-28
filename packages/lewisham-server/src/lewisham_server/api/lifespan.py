from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta

import structlog
from fastapi import FastAPI

from lewisham_server.clients.lewisham import LewishamClient, LewishamParser
from lewisham_server.services import LewishamService
from lewisham_server.settings import Settings

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]
logger = structlog.get_logger(__name__)


def create_lifespan(settings: Settings) -> Lifespan:
    """Create the FastAPI lifespan handler for app-scoped dependencies."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "app_starting",
            app_version=settings.app_version,
            log_level=settings.log_level,
            log_format=settings.log_format,
            host=settings.host,
            port=settings.port,
            workers=settings.workers,
            cache_schedule_ttl_seconds=settings.cache_schedule_ttl_seconds,
            cache_address_search_ttl_seconds=settings.cache_address_search_ttl_seconds,
            cache_uprn_ttl_seconds=settings.cache_uprn_ttl_seconds,
            cache_negative_ttl_seconds=settings.cache_negative_ttl_seconds,
            upstream_base_url=settings.upstream_base_url,
            upstream_timeout_seconds=settings.upstream_request_timeout_seconds,
        )
        lewisham_service = _create_lewisham_service(settings)
        app.state.settings = settings
        app.state.lewisham_service = lewisham_service
        logger.info("app_ready", app_version=settings.app_version)
        try:
            yield
        finally:
            await lewisham_service.aclose()
            logger.info("app_shutdown", app_version=settings.app_version)

    return lifespan


def _create_lewisham_service(settings: Settings) -> LewishamService:
    """Build the Lewisham service with environment-driven upstream and cache policy."""

    client = LewishamClient(
        base_url=settings.upstream_base_url,
        collection_page_url=settings.upstream_collection_page_url,
        rounds_information_item_guid=settings.upstream_rounds_information_item_guid,
        user_agent=settings.upstream_user_agent,
        timeout_seconds=settings.upstream_request_timeout_seconds,
    )
    parser = LewishamParser(
        include_raw_upstream=settings.log_include_raw_upstream,
        raw_upstream_max_chars=settings.log_raw_upstream_max_chars,
    )
    return LewishamService(
        client=client,
        parser=parser,
        schedule_cache_ttl=timedelta(seconds=settings.cache_schedule_ttl_seconds),
        address_search_cache_ttl=timedelta(
            seconds=settings.cache_address_search_ttl_seconds
        ),
        uprn_cache_ttl=timedelta(seconds=settings.cache_uprn_ttl_seconds),
        negative_cache_ttl=timedelta(seconds=settings.cache_negative_ttl_seconds),
    )
