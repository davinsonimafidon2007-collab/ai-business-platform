"""Schemas for the admin system status endpoint (Task G.1).

Expone el último resultado del ProviderCanaryJob y un ping de Redis
para que el dashboard/ops pueda verificar salud sin leer logs.
"""

from __future__ import annotations

from pydantic import BaseModel


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


class AdminSystemStatus(BaseModel):
    """Estado del sistema para admin: Redis + último canary."""

    redis_ok: bool | None = None
    canary: ProviderCanaryStatus