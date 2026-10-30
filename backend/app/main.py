"""
PatchPilot FastAPI application.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.repositories import router as repos_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.debug)
    log.info("patchpilot_starting", version=settings.app_version)
    init_db()
    log.info("database_initialized")
    yield
    log.info("patchpilot_shutdown")


app = FastAPI(
    title="PatchPilot",
    description="Autonomous debugging and self-healing software engineer.",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request ID middleware ──────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", "unknown")
    log.error("unhandled_exception", path=request.url.path, error=str(exc), request_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred.",
            },
            "request_id": request_id,
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(repos_router, prefix="/api/v1")
