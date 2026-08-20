"""Health endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud compuesto (DEVOPS-001).

    Attributes:
        status: Estado global del servicio ("ok" | "degraded" | "error").
        version: Versión de la API.
        providers: Lista de proveedores registrados.
        checks: Estado de cada componente (api / database / redis).
    """

    status: str = Field("ok", description="Estado global del servicio")
    version: str = Field(..., description="Versión de la API")
    providers: list[str] = Field(
        ..., description="Lista de proveedores disponibles"
    )
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="Estado de los sub-checks: api / database / redis",
    )


class ReadyResponse(BaseModel):
    """Respuesta del endpoint de readiness."""

    status: str = Field(..., description="Estado general: ok o degraded")
    db: bool = Field(..., description="PostgreSQL accesible")
    redis: bool = Field(..., description="Redis accesible")
