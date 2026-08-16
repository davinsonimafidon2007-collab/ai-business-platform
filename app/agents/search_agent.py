"""Search Agent: buscar, normalizar, filtrar, guardar."""
from __future__ import annotations

from typing import Any

from app.models.search import SearchRequest
from app.services.search_engine import SearchEngineService


class SearchAgent:
    """Agent para ejecutar pipeline de búsqueda completa.

    Delega en SearchEngineService: el motor de búsqueda end-to-end construido
    por el DI de la app (``get_search_engine_service``).
    """

    def __init__(
        self,
        provider_name: str,
        search_engine: SearchEngineService | None = None,
    ) -> None:
        self.provider_name = provider_name
        self._search_engine = search_engine

    async def run(
        self,
        query: str,
        *,
        engine: SearchEngineService | None = None,
        max_results: int = 20,
        **kwargs: Any,
    ) -> Any:
        """Ejecuta una búsqueda completa y devuelve el SearchEngineResult.

        Args:
            query: Término de búsqueda.
            engine: SearchEngineService (opcional si se inyectó en el constructor).
            max_results: Número máximo de resultados.
            **kwargs: Puede incluir ``budget_max`` para acotar por presupuesto.

        Raises:
            ValueError: Si no hay motor de búsqueda disponible.
        """
        engine = engine or self._search_engine
        if engine is None:
            raise ValueError(
                "SearchAgent necesita un SearchEngineService: pásalo en 'engine' "
                "o inyéctalo en el constructor."
            )

        request = SearchRequest(
            query=query,
            max_results=max_results,
            budget_max=kwargs.get("budget_max"),
        )
        return await engine.search(request)
