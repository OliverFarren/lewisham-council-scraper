import uvicorn

from lewisham_server.logging_config import configure_logging
from lewisham_server.settings import get_settings


def main() -> None:
    """Run the API with uvicorn using environment-backed settings."""

    settings = get_settings()
    configure_logging(settings)
    uvicorn.run(
        "lewisham_server.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
