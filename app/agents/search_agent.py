"""Search Agent: buscar, normalizar, filtrar, guardar."""
from __future__ import annotations

from typing import Any


class SearchAgent:
    """Agent para ejecutar pipeline de búsqueda completa."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    async def run(self, query: str, **kwargs: Any) -> list[Any]:
        """Ejecuta búsqueda y devuelve resultados normalizados."""
        return []
