"""Orchestrador: pipeline SEARCH → SCORE → MARKET → PROFIT → OPPORTUNITY → ALERT."""
from __future__ import annotations

from typing import Any

from app.agents.alert_agent import AlertAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.scoring_agent import ScoringAgent
from app.agents.search_agent import SearchAgent
from app.models.search import SearchRequest
from app.services.search_engine import SearchEngineService


class PipelineOrchestrator:
    """Orquesta el flujo completo de análisis de vehículos.

    El pipeline SEARCH → SCORE → MARKET → PROFIT → OPPORTUNITY → ALERT lo
    ejecuta SearchEngineService; este orquestador expone el acceso a través
    de los agentes del dominio.
    """

    def __init__(
        self,
        search_engine: SearchEngineService | None = None,
    ) -> None:
        self._engine = search_engine
        self.search_agent = SearchAgent("default", search_engine=search_engine)
        self.scoring_agent = ScoringAgent()
        self.opportunity_agent = OpportunityAgent()
        self.alert_agent = AlertAgent()

    async def run_pipeline(
        self,
        query: str,
        rules: dict | None = None,
        *,
        engine: SearchEngineService | None = None,
        max_results: int = 30,
        budget_max: float | None = None,
    ) -> Any:
        """Ejecuta el pipeline completo y devuelve el SearchEngineResult.

        Args:
            query: Término de búsqueda.
            rules: Reglas de alerta (se ignoran aquí; se aplican en AlertAgent).
            engine: SearchEngineService (opcional si se inyectó en el constructor).
            max_results: Número máximo de resultados.
            budget_max: Tope de presupuesto opcional.

        Raises:
            ValueError: Si no hay motor de búsqueda disponible.
        """
        engine = engine or self._engine
        if engine is None:
            raise ValueError(
                "run_pipeline necesita un SearchEngineService: pásalo en 'engine' "
                "o inyéctalo en el constructor."
            )

        request = SearchRequest(
            query=query,
            max_results=max_results,
            budget_max=budget_max,
        )
        return await engine.search(request)
