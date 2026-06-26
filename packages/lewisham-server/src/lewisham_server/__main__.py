import uvicorn

from lewisham_server.settings import get_settings


def main() -> None:
    """Run the API with uvicorn using environment-backed settings."""

    settings = get_settings()
    uvicorn.run(
        "lewisham_server.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
