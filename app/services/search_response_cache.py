"""Caché Redis fail-soft para respuestas del endpoint POST /search.

SEARCH.ORCH.1 — la búsqueda es costosa (N providers × red + análisis por
vehículo). Peticiones idénticas repetidas en poco tiempo (usuario refrescando
la UI) pueden servirse de caché sin recalcular.

Diseño:
    - Clave = hash SHA-256 del request canónico (JSON ordenado).
    - Valor = respuesta serializada (SearchAPIResponse.model_dump_json()).
    - Fail-soft: si Redis no está o falla, se comporta como miss y la
      búsqueda se ejecuta normal. Jamás rompe el flujo.
    - Desactivada por defecto (``settings.search_cache_enabled``): en uso
      personal preferimos datos frescos; activar explícitamente.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import cache_get, cache_set

logger = get_logger(__name__)

_CACHE_KEY_PREFIX = "search:resp:v1:"


def build_search_cache_key(request: Any) -> str:
    """Clave estable a partir del contenido del request.

    Dos requests con los mismos campos (en cualquier orden de claves JSON)
    producen la misma clave.
    """
    payload = request.model_dump(mode="json")
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{_CACHE_KEY_PREFIX}{digest}"


async def get_cached_search_response(key: str) -> dict[str, Any] | None:
    """Devuelve la respuesta cacheada o ``None`` (miss / desactivada / error)."""
    if not bool(getattr(settings, "search_cache_enabled", False)):
        return None
    try:
        raw = await cache_get(key)
    except Exception:  # noqa: BLE001 — fail-soft: caché jamás rompe la búsqueda
        logger.warning("search_cache: GET falló para %s", key, exc_info=True)
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        logger.warning("search_cache: entrada corrupta para %s; ignorada", key)
        return None
    return data if isinstance(data, dict) else None


async def set_cached_search_response(key: str, payload_json: str, ttl_seconds: int | None = None) -> None:
    """Guarda la respuesta serializada. Silencioso si está desactivada o Redis cae."""
    if not bool(getattr(settings, "search_cache_enabled", False)):
        return
    ttl = int(ttl_seconds if ttl_seconds is not None else getattr(settings, "search_cache_ttl", 300))
    try:
        await cache_set(key, payload_json, ttl_seconds=max(1, ttl))
    except Exception:  # noqa: BLE001 — fail-soft
        logger.warning("search_cache: SET falló para %s", key, exc_info=True)
