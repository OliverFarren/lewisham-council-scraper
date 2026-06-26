from fastapi import FastAPI

from lewisham_server.routers import bins

app = FastAPI(title="Lewisham Council Scraper API", version="0.1.0")

app.include_router(bins.router, prefix="/bins", tags=["bins"])
