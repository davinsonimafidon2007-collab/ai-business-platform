"""Admin system status endpoints (Tasks G.1 + G.2 + G.4).

Expone si AS24 / mobile.de están sanos según la última ejecución del
ProviderCanaryJob, más un ping de Redis y métricas de jobs del scheduler.
Sirve para dashboard/ops sin leer logs.

- ``GET  /admin/status``        → snapshot actual (G.1 + G.4)
- ``POST /admin/status/canary`` → ejecuta ProviderCanaryJob ahora y
  devuelve el snapshot actualizado (G.2, admin only).

Admin-only: protegido por ``require_admin`` a nivel de ruta.
El middleware de auth ya skip-ea ``/api/v1/admin/`` (auth se enforce
en la dependencia de ruta).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.core.config import settings
from app.core.redis import get_redis
from app.database import db_manager
from app.dependencies.auth import require_admin
from app.jobs.base import JobContext
from app.jobs.canary_state import get_last_canary_result
from app.jobs.provider_canary import ProviderCanaryJob
from app.models.user import User

logger = logging.getLogger(__name__)
from app.providers.registry import ProviderRegistry
from app.schemas.admin_status import (
    AdminSystemStatus,
    JobMetricsRead,
    ProviderCanaryStatus,
    ProvidersStatus,
)

router = APIRouter(prefix="/admin/status", tags=["Admin System Status"])


def _build_jobs(request: Request) -> list[JobMetricsRead]:
    """Snapshot de métricas de los jobs registrados en el scheduler (G.4).

    Si el scheduler está desactivado o ausente (``ENABLE_SCHEDULER=false``),
    se devuelve una lista vacía — nunca un 500.
    """
    jobs: list[JobMetricsRead] = []
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return jobs

    for row in scheduler.list_jobs():
        jobs.append(
            JobMetricsRead(
                name=row["name"],
                interval=row["interval"],
                status=row["status"],
                last_execution=row.get("last_execution"),
                next_execution=row.get("next_execution"),
                last_duration=row.get("last_duration") or 0.0,
                execution_count=row.get("execution_count") or 0,
                success_count=row.get("success_count") or 0,
                failure_count=row.get("failure_count") or 0,
                consecutive_failures=row.get("consecutive_failures") or 0,
            )
        )
    return jobs


async def _build_admin_system_status(request: Request) -> AdminSystemStatus:
    """Construye el snapshot actual: Redis ping + último canary + jobs.

    Helper compartido por el GET (G.1) y el POST (G.2) para que ambos
    devuelvan exactamente el mismo shape.
    """
    redis_ok: bool | None = None
    client = get_redis()
    if client is not None:
        try:
            await client.ping()
            redis_ok = True
        except Exception as exc:  # noqa: BLE001 — fail-soft health reporting
            logger.warning("Redis ping failed for admin status: %s", exc)
            redis_ok = False

    raw = get_last_canary_result()
    if raw is None:
        canary = ProviderCanaryStatus()
    else:
        data = raw.get("data") or {}
        canary = ProviderCanaryStatus(
            success=raw.get("success"),
            message=raw.get("message"),
            finished_at=raw.get("finished_at"),
            policy=data.get("policy"),
            autoscout24=data.get("autoscout24"),
            mobile_de=data.get("mobile_de"),
            strict_mobile=data.get("strict_mobile"),
            mobile_status=data.get("mobile_status"),
        )

    providers = ProvidersStatus(
        providers=ProviderRegistry.list_providers(),
        default_import_cost_profile=getattr(settings, "default_import_cost_profile", ""),
        enable_es_market_fixture=getattr(settings, "enable_es_market_fixture", False),
        enable_coches_net_fixture=getattr(settings, "enable_coches_net_fixture", False),
        enable_autoscout24_es=getattr(settings, "enable_autoscout24_es", False),
    )

    return AdminSystemStatus(
        redis_ok=redis_ok,
        canary=canary,
        jobs=_build_jobs(request),
        providers=providers,
    )


@router.get("", response_model=AdminSystemStatus)
async def admin_system_status(
    request: Request,
    _: User = Depends(require_admin),
) -> AdminSystemStatus:
    """Devuelve el estado del sistema: Redis ping + último canary + jobs.

    - ``redis_ok``: ``True``/``False`` si hay cliente Redis; ``None`` si
      no se pudo comprobar (no hay cliente inicializado).
    - ``canary``: snapshot del último ``ProviderCanaryJob``; campos
      ``None`` si aún no se ha ejecutado.
    - ``jobs``: métricas de cada job registrado (incl. ``consecutive_failures``).
    """
    return await _build_admin_system_status(request)


@router.post("/canary", response_model=AdminSystemStatus)
async def run_provider_canary(
    request: Request,
    _: User = Depends(require_admin),
) -> AdminSystemStatus:
    """Ejecuta ProviderCanaryJob bajo demanda y devuelve el snapshot.

    - Admin only (``require_admin``).
    - Ejecuta el canary de forma síncrona: el admin espera el resultado,
      no se lanza en background.
    - ``ProviderCanaryJob.execute`` ya actualiza ``canary_state`` (G.1),
      así que tras ejecutar re-leemos el estado con el helper compartido.
    - Un FAIL de negocio (ej: AS24 0 listings) devuelve 200 con
      ``canary.success=false`` — no es un error HTTP.
    - Una excepción de programación inesperada se propaga al handler
      global → 500 (no se traga).
    - Devuelve el mismo shape que GET (incluye ``jobs``).
    """
    context = JobContext(db_manager=db_manager, settings=settings)
    job = ProviderCanaryJob()
    await job.execute(context)
    return await _build_admin_system_status(request)
