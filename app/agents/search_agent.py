"""Search Agent: buscar, normalizar, filtrar, guardar (AUDIT.AGENTS.1)."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import SearchAgentInput, SearchAgentOutput
from app.models.search import SearchRequest
from app.services.search_engine import SearchEngineService


class SearchAgent(BaseAgent[SearchAgentInput, SearchAgentOutput]):
    """Agent del pipeline SEARCH.

    Delega en SearchEngineService, el motor de búsqueda end-to-end construido
    por el DI de la app (``get_search_engine_service``).
    """

    name = "search_agent"
    role = "search"
    description = (
        "Ejecuta el pipeline completo de búsqueda contra los providers "
        "(scoring + mercado + rentabilidad + oportunidad incluidos)."
    )
    input_type = SearchAgentInput
    output_type = SearchAgentOutput
    default_timeout_seconds = 120.0

    def __init__(
        self,
        search_engine: SearchEngineService | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """Args:
        search_engine: Motor de búsqueda (obligatorio en ``run`` si es None aquí).
        timeout_seconds: Timeout en segundos (por defecto 120).

        Nota de compatibilidad: versiones previas aceptaban un ``provider_name``
        como primer argumento posicional; ya no se usa.
        """
        super().__init__(timeout_seconds=timeout_seconds)
        self._search_engine = search_engine

    async def _execute(self, input_data: SearchAgentInput) -> SearchAgentOutput:
        engine = self._require_engine()
        request = SearchRequest(
            query=input_data.query,
            max_results=input_data.max_results,
            country=input_data.country,
            budget_max=input_data.budget_max,
            **({"providers": input_data.providers} if input_data.providers else {}),
        )
        result = await engine.search(request)
        return SearchAgentOutput(
            summary=result.summary,
            results=result.results,
            provider_issues=result.provider_issues,
        )

    def _require_engine(self) -> SearchEngineService:
        if self._search_engine is None:
            raise ValueError(
                "SearchAgent necesita un SearchEngineService: inyéctalo en el "
                "constructor o usa get_search_agent() del DI."
            )
        return self._search_engine
