"""Health endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud.

    Attributes:
        status: Estado del servicio ("ok").
        version: Versión de la API.
        providers: Lista de proveedores registrados.
    """

    status: str = Field("ok", description="Estado del servicio")
    version: str = Field(..., description="Versión de la API")
    providers: list[str] = Field(
        ..., description="Lista de proveedores disponibles"
    )

