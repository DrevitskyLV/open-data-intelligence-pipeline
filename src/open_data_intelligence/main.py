from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from open_data_intelligence.api import router
from open_data_intelligence.config import settings
from open_data_intelligence.db import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Independent portfolio project for idempotent open-data ingestion, "
        "entity normalization, relationship discovery and explainable analytics."
    ),
    lifespan=lifespan,
)
app.include_router(router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(static_dir / "index.html")
