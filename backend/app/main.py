from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db import init_db
from app.routers.ideas import router as ideas_router
from app.schemas import LEGAL_DISCLAIMER


settings = get_settings()

app = FastAPI(
    title="Patent Troll API",
    version="0.1.0",
    description="Phase 1 invention intake, prior art search, and patentability analysis API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ideas_router)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "disclaimer": LEGAL_DISCLAIMER}
