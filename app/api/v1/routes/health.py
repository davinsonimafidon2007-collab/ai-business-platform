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
import socket
from urllib.parse import urlsplit

from fastapi import APIRouter, Response, status

from app.api.v1.schemas.health import HealthResponse, ReadyResponse
from app.core.config import settings
from app.core.redis import get_redis
from app.database import db_manager
from app.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Short timeouts so /health stays lightweight under dependency hiccups.
_DB_CHECK_TIMEOUT_S = 2.0
_REDIS_CHECK_TIMEOUT_S = 2.0
_TCP_PROBE_TIMEOUT_S = 1.0


def _host_port_from_url(url: str, default_port: int) -> tuple[str, int]:
    """Extrae (host, puerto) de una URL de conexión (DATABASE_URL/REDIS_URL).

    Soporta esquemas con driver (postgresql+asyncpg://, redis://) y hosts
    docker-compose (db, redis) o localhost. Nunca lanza: si no se puede
    parsear devuelve localhost + puerto por defecto.
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname or "localhost"
        port = parts.port or default_port
        return host, port
    except Exception:
        return "localhost", default_port


def _db_host_port() -> tuple[str, int]:
    return _host_port_from_url(settings.database_url, 5432)


def _redis_host_port() -> tuple[str, int]:
    return _host_port_from_url(settings.redis_url, 6379)


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
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness — proceso vivo",
    description="Solo comprueba que el proceso responde, sin depender de DB o "
    "Redis. Usado por el healthcheck del contenedor (docker-compose) para no "
    "reiniciar la API cuando las dependencias tardan en arrancar.",
)
async def get_health_live() -> dict[str, object]:
    """Liveness: el proceso está vivo (TASK-004)."""
    return {"status": "ok", "checks": {"api": "ok"}}


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
        # TASK 1 — modo del pipeline ES, visible para el banner de la UI.
        es_data_mode=getattr(settings, "es_data_mode", "fixture"),
    )


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar readiness",
    description="Comprueba dependencias críticas: PostgreSQL y Redis.",
    responses={
        200: {
            "description": "Servicio listo",
            "model": ReadyResponse,
        },
        500: {
            "description": "Servicio no listo",
            "model": ReadyResponse,
        },
    },
)
async def get_health_ready() -> ReadyResponse:
    db_ok = False
    redis_ok = False

    try:
        with socket.create_connection(_db_host_port(), timeout=_TCP_PROBE_TIMEOUT_S):
            pass
        db_ok = True
    except Exception:
        db_ok = False

    try:
        with socket.create_connection(
            _redis_host_port(), timeout=_TCP_PROBE_TIMEOUT_S
        ):
            pass
        redis_ok = True
    except Exception:
        redis_ok = False

    ready = db_ok and redis_ok
    status_value = "ok" if ready else "degraded"
    return ReadyResponse(
        status=status_value,
        db=db_ok,
        redis=redis_ok,
    )
