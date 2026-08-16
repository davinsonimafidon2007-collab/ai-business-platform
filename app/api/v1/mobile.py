"""Mobile release support endpoints (MOB-P3-002).

Expone la versión mínima y la última disponible de la app móvil para que el
cliente (web/nativo) pueda decidir si debe forzar una actualización.

- ``GET /api/v1/mobile/version`` → ``{ min_version, latest_version, update_url }``

Los valores se leen de variables de entorno con fallback a 1.0.0 para que el
endpoint nunca devuelva un error por configuración incompleta:

- ``MOBILE_MIN_VERSION``     → versión mínima soportada (obligatoria)
- ``MOBILE_LATEST_VERSION``  → última versión publicada
- ``MOBILE_UPDATE_URL``      → URL de descarga/actualización (Play Store/GitHub)
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel


class MobileVersionResponse(BaseModel):
    """Shape de la respuesta de versión para el cliente móvil."""

    min_version: str
    latest_version: str
    update_url: str


router = APIRouter(prefix="/mobile", tags=["Mobile Release"])


@router.get("/version", response_model=MobileVersionResponse)
async def mobile_version() -> MobileVersionResponse:
    """Devuelve la configuración de versión de la app móvil.

    - ``min_version``: versión mínima que aún recibe soporte; si el cliente
      tiene una versión menor debe actualizarse (obligatorio).
    - ``latest_version``: última versión publicada; si el cliente tiene una
      versión menor (pero >= min) debe notificarse (recomendado).
    - ``update_url``: dónde descargar la actualización.
    """
    return MobileVersionResponse(
        min_version=os.getenv("MOBILE_MIN_VERSION", "1.0.0"),
        latest_version=os.getenv("MOBILE_LATEST_VERSION", "1.0.0"),
        update_url=os.getenv(
            "MOBILE_UPDATE_URL",
            "https://github.com/davinsonimafidon2007-collab/ai-business-platform/releases",
        ),
    )
