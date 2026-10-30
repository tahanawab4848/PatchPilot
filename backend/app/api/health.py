"""
Health and readiness endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.database import DbSession
from app.sandbox.executor import ExecutionService
from app.services.nebius_client import NemotronClient

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness check — always returns 200 if the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    """
    Readiness check: verifies database connectivity and reports configuration status.
    Does NOT call the inference API (that would be too slow for a readiness probe).
    """
    # Quick DB check
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
        db_error = None
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    sandbox_svc = ExecutionService(settings)

    return {
        "status": "ready" if db_ok else "degraded",
        "database": {"ok": db_ok, "error": db_error},
        "nebius": {
            "configured": settings.nebius_configured,
            "model_id": settings.nebius_model_id,
            "base_url": settings.nebius_api_base_url,
        },
        "sandbox": {
            "enabled": settings.sandbox_enabled,
            "available": sandbox_svc.is_available(),
        },
    }


@router.get("/health/model")
async def model_health(settings: Settings = Depends(get_settings)):
    """
    Checks whether the configured Nebius model endpoint is reachable.
    Makes a real inference request — use sparingly.
    """
    client = NemotronClient(settings)
    result = await client.health_check()
    return result
