"""Health check endpoints (Liveness + Readiness + Composite).

Endpoints:
- GET /health/live   — Liveness probe (verificación ligera del proceso).
- GET /health/ready  — Readiness probe (verificación de DB + Redis).
- GET /health        — Check compuesto de salud con metadatos.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Response, status

from app.api.v1.schemas.health import HealthResponse
from app.core.config import settings
from app.core.redis import get_redis
from app.database import db_manager
from app.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_DB_CHECK_TIMEOUT_S = 2.0
_REDIS_CHECK_TIMEOUT_S = 2.0


async def _check_database() -> bool:
    """Run ``SELECT 1`` against the shared async engine with a short timeout.

    Returns True if the database answers, False otherwise (never raises).
    """
    try:
        async def _probe() -> None:
            async with db_manager.get_session() as session:
                await session.execute(__import__("sqlalchemy").text("SELECT 1"))

        await asyncio.wait_for(_probe(), timeout=_DB_CHECK_TIMEOUT_S)
        return True
    except Exception:
        logger.warning("Health check database down", exc_info=True)
        return False


async def _check_redis() -> str:
    """Soft PING against the shared Redis client.

    Returns:
        - ``"ok"``       → client present and answers PING.
        - ``"error"``    → client present but PING failed.
        - ``"disabled"`` → no client (Redis optional / not initialized).
    """
    client = get_redis()
    if client is None:
        return "disabled"

    try:
        await asyncio.wait_for(client.ping(), timeout=_REDIS_CHECK_TIMEOUT_S)
        return "ok"
    except Exception:
        logger.warning("Health check redis down", exc_info=True)
        return "error"


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness — proceso vivo",
    description="Solo comprueba que el proceso responde, sin depender de DB o Redis.",
)
async def liveness_probe() -> dict[str, object]:
    """Liveness: el proceso está vivo."""
    return {"status": "ok", "checks": {"api": "ok"}, "timestamp": "now"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness — listo para recibir tráfico",
    description="Comprueba que dependencias críticas (DB, Redis) están disponibles.",
)
async def readiness_probe() -> dict[str, object]:
    """Readiness probe: Verifica DB y Redis."""
    db_ok = await _check_database()
    redis_state = await _check_redis()

    checks = {
        "database": db_ok,
        "redis": redis_state == "ok",
    }

    if not db_ok or redis_state == "error":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "checks": {
                    "database": "ok" if db_ok else "error",
                    "redis": redis_state,
                },
            },
        )

    return {
        "status": "healthy",
        "checks": {
            "database": "ok",
            "redis": redis_state,
        },
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar estado del servicio (API + DB + Redis)",
    description="Devuelve el estado actual de la API, la versión, proveedores y estado de componentes.",
    responses={
        200: {"description": "Servicio operativo o degradado", "model": HealthResponse},
        503: {"description": "Database caída — servicio no operativo", "model": HealthResponse},
    },
)
async def health_check(response: Response) -> HealthResponse:
    """Health check completo: Combina liveness + readiness."""
    providers = ProviderRegistry.list_providers()

    db_ok = await _check_database()
    redis_state = await _check_redis()

    checks: dict[str, str] = {
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "redis": redis_state,
    }

    if not db_ok:
        overall = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif redis_state in ("error", "disabled"):
        overall = "degraded"
    else:
        overall = "ok"

    return HealthResponse(
        status=overall,
        version=getattr(settings, "app_version", "1.0.0"),
        providers=providers,
        checks=checks,
    )
