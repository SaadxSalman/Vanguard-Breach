"""Vanguard-Breach API server entrypoint.

Run:  uvicorn app.main:app --reload  (from backend/)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .api import campaigns, knowledge, stream, system
from .auth import ApiKeyMiddleware
from .config import get_settings
from .core.rag import get_kb

logging.basicConfig(level=get_settings().log_level.upper(),
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("vanguard")

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db.init_db()
    seeded = get_kb().bootstrap()
    log.info("knowledge base ready: %s", seeded)
    log.info("data dir: %s | env file: %s", settings.data_dir, settings.env_file_path)
    yield
    db.close_db()


app = FastAPI(title="Vanguard-Breach", version="1.0.0",
              description="Autonomous GenAI red-teaming platform: hierarchical adversarial "
                          "RAG + multi-agent reasoning against LLM deployments.",
              lifespan=lifespan)

app.add_middleware(ApiKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router)
app.include_router(knowledge.router)
app.include_router(system.router)
app.include_router(stream.router)


@app.get("/api")
def api_root() -> dict[str, str]:
    return {"service": "vanguard-breach", "docs": "/docs", "health": "/api/health"}


# ── serve the built frontend (production mode) ───────────────────────────────
if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse | JSONResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"detail": "frontend not built — run npm run build"})
