from collections.abc import Awaitable, Callable
from time import perf_counter

import structlog
from fastapi import FastAPI, Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


def add_request_logging_middleware(app: FastAPI) -> None:
    """Add privacy-safe request logging to the FastAPI application."""

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "unhandled_exception",
                method=request.method,
                route=_route_template(request),
                duration_ms=_duration_ms(start_time),
            )
            raise

        logger.info(
            "http_request",
            method=request.method,
            route=_route_template(request),
            status_code=response.status_code,
            duration_ms=_duration_ms(start_time),
        )
        return response


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None:
        path = str(request.scope.get("path", ""))
        for name, value in request.path_params.items():
            path = path.replace(str(value), f"{{{name}}}")
        return path

    return "<unmatched>"


def _duration_ms(start_time: float) -> float:
    return round((perf_counter() - start_time) * 1000, 2)
