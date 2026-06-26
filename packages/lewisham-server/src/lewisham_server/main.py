"""ASGI entrypoint for uvicorn and other ASGI servers."""

from lewisham_server.api.app import create_app

app = create_app()
