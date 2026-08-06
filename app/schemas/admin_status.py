"""Schemas for the admin system status endpoint (Task G.1).

Expone el último resultado del ProviderCanaryJob y un ping de Redis
para que el dashboard/ops pueda verificar salud sin leer logs.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobMetricsRead(BaseModel):
    """Snapshot of a registered job's runtime metrics (Task G.4)."""

    name: str
    interval: int
    status: str
    last_execution: datetime | None = None
    next_execution: datetime | None = None
    last_duration: float = 0.0
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0


class ProviderCanaryStatus(BaseModel):
    """Último snapshot del ProviderCanaryJob.

    Todos los campos son ``None`` si aún no se ha ejecutado el canary
    (p. ej. justo después de reiniciar el proceso).
    """

    success: bool | None = None
    message: str | None = None
    finished_at: str | None = None
    autoscout24: dict | None = None
    mobile_de: dict | None = None
    strict_mobile: bool | None = None
    mobile_status: str | None = None


class ProviderInfo(BaseModel):
    """Resumen de un provider registrado."""

    name: str
    source: str | None = None


class ProvidersStatus(BaseModel):
    """Snapshot del registry de providers y flags ES relevantes."""

    providers: list[str] = []
    default_import_cost_profile: str = ""
    enable_es_market_fixture: bool = False
    enable_coches_net_fixture: bool = False
    enable_autoscout24_es: bool = False


class AdminSystemStatus(BaseModel):
    """Estado del sistema para admin: Redis + último canary + jobs."""

    redis_ok: bool | None = None
    canary: ProviderCanaryStatus
    jobs: list[JobMetricsRead] = []  # nuevo (G.4)
    providers: ProvidersStatus = ProvidersStatus()  # ADMIN.1
