"""Admin system status endpoints (Tasks G.1 + G.2).

Expone si AS24 / mobile.de están sanos según la última ejecución del
ProviderCanaryJob, más un ping de Redis. Sirve para dashboard/ops sin
leer logs.

- ``GET  /admin/status``        → snapshot actual (G.1)
- ``POST /admin/status/canary`` → ejecuta ProviderCanaryJob ahora y
  devuelve el snapshot actualizado (G.2, admin only).

Admin-only: protegido por ``require_admin`` a nivel de ruta.
El middleware de auth ya skip-ea ``/api/v1/admin/`` (auth se enforce
en la dependencia de ruta).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.redis import get_redis
from app.db.session import db_manager
from app.dependencies.auth import require_admin
from app.jobs.base import JobContext
from app.jobs.canary_state import get_last_canary_result
from app.jobs.provider_canary import ProviderCanaryJob
from app.models.user import User
from app.schemas.admin_status import AdminSystemStatus, ProviderCanaryStatus

router = APIRouter(prefix="/admin/status", tags=["Admin System Status"])


async def _build_admin_system_status() -> AdminSystemStatus:
    """Construye el snapshot actual: Redis ping + último canary.

    Helper compartido por el GET (G.1) y el POST (G.2) para que ambos
    devuelvan exactamente el mismo shape.
    """
    redis_ok: bool | None = None
    client = get_redis()
    if client is not None:
        try:
            await client.ping()
            redis_ok = True
        except Exception:
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
            autoscout24=data.get("autoscout24"),
            mobile_de=data.get("mobile_de"),
            strict_mobile=data.get("strict_mobile"),
            mobile_status=data.get("mobile_status"),
        )

    return AdminSystemStatus(redis_ok=redis_ok, canary=canary)


@router.get("", response_model=AdminSystemStatus)
async def admin_system_status(
    _: User = Depends(require_admin),
) -> AdminSystemStatus:
    """Devuelve el estado del sistema: Redis ping + último canary.

    - ``redis_ok``: ``True``/``False`` si hay cliente Redis; ``None`` si
      no se pudo comprobar (no hay cliente inicializado).
    - ``canary``: snapshot del último ``ProviderCanaryJob``; campos
      ``None`` si aún no se ha ejecutado.
    """
    return await _build_admin_system_status()


@router.post("/canary", response_model=AdminSystemStatus)
async def run_provider_canary(
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
    """
    context = JobContext(db_manager=db_manager, settings=settings)
    job = ProviderCanaryJob()
    await job.execute(context)
    return await _build_admin_system_status()