"""
CYBER-20 — Federated Collaborative Threat Detection
FastAPI application entry point.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.init_db import init_db

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan (startup / shutdown) ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting CYBER-20 backend  [%s]", settings.environment)
    await init_db()
    logger.info(
        "API ready — http://%s:%d | Docs: http://%s:%d/docs",
        settings.host, settings.port,
        settings.host, settings.port,
    )
    yield
    logger.info("Shutting down CYBER-20 backend.")


# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for CYBER-20 — Federated Collaborative Threat Detection. "
        "Currently serving structured demo data. Real Flower FL and PyTorch ML "
        "integration will be added in later phases."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request logging middleware ────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d  (%.1f ms)",
        request.method, request.url.path,
        response.status_code, duration_ms,
    )
    return response

# ── Global error handler ──────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "detail": str(exc) if settings.debug else None,
        },
    )

# ── Routers ───────────────────────────────────────────────────

app.include_router(api_router)

# ── Health check (outside /api prefix) ───────────────────────

@app.get("/health", tags=["health"], summary="Basic health check")
async def health():
    """Lightweight liveness probe — returns 200 if server is up."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/", tags=["health"], include_in_schema=False)
async def root():
    return {
        "project": settings.app_name,
        "version": settings.app_version,
        "docs":    "/docs",
        "health":  "/health",
    }
