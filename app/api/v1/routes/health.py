"""Health check endpoint.

GET /health — Returns API status, version, and available providers.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.v1.schemas.health import HealthResponse
from app.core.config import settings
from app.providers.registry import ProviderRegistry

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar estado del servicio",
    description="Devuelve el estado actual de la API, la versión y la lista de "
    "proveedores registrados.",
    responses={
        200: {
            "description": "Servicio operativo",
            "model": HealthResponse,
        },
    },
)
def get_health() -> HealthResponse:
    """Endpoint de salud y metadatos de la API."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        providers=ProviderRegistry.list_providers(),
    )

