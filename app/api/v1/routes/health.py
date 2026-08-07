"""Health check endpoint (composite — API + DB + Redis).

GET /health — Returns API status, version, available providers and the
state of the underlying dependencies (database and optional Redis).

HTTP semantics:
- 200 with ``status="ok"``        → API + DB ok (Redis ok or optional).
- 200 with ``status="degraded"``  → API + DB ok, Redis down/disabled.
- 503 with ``status="error"``     → database check failed.

The DB check runs ``SELECT 1`` through the shared ``DatabaseManager`` engine
with a short timeout so it never blocks the event loop for long; the Redis
check is a soft ``PING`` (see app/core/redis.py for the fail-soft semantics).
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Response, status

from app.api.v1.schemas.health import HealthResponse
from app.core.config import settings
from app.core.redis import get_redis
from app.database import db_manager
from app.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Short timeouts so /health stays lightweight under dependency hiccups.
_DB_CHECK_TIMEOUT_S = 2.0
_REDIS_CHECK_TIMEOUT_S = 2.0


async def _check_database() -> bool:
    """Run ``SELECT 1`` against the shared async engine with a short timeout.

    Returns True if the database answers, False otherwise (never raises).
    """
    try:
        async def _probe() -> None:
            async with db_manager.engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))

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
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar estado del servicio (API + DB + Redis)",
    description="Devuelve el estado actual de la API, la versión, la lista de "
    "proveedores registrados y el estado de los componentes database/redis.",
    responses={
        200: {"description": "Servicio operativo o degradado", "model": HealthResponse},
        503: {"description": "Database caída — servicio no operativo", "model": HealthResponse},
    },
)
async def get_health(response: Response) -> HealthResponse:
    """Endpoint de salud y metadatos de la API (composite)."""
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
        version=settings.app_version,
        providers=providers,
        checks=checks,
    )

