"""Orchestrador: pipeline SEARCH → ALERT compuesto con los agents reales.

AUDIT.AGENTS.1: la versión anterior ignoraba ScoringAgent/OpportunityAgent/
AlertAgent (SearchEngineService ya integra SCORE/MARKET/PROFIT/OPPORTUNITY
por resultado) y devolvía el resultado crudo. Ahora:

- SEARCH lo ejecuta ``SearchAgent`` (delegando en SearchEngineService).
- ALERT es real: cada resultado con análisis de oportunidad se evalúa contra
  las reglas configuradas mediante ``AlertAgent``.

Scoring y Opportunity por vehículo siguen siendo responsabilidad del motor de
búsqueda; los agents correspondientes (ScoringAgent, OpportunityAgent) quedan
disponibles en el orquestador para pasos puntuales fuera del pipeline batch.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.alert_agent import AlertAgent
from app.agents.base import BaseAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.schemas import (
    AlertAgentInput,
    AlertOpportunityInput,
    AlertRulesInput,
    SearchAgentInput,
    SearchAgentOutput,
)
from app.agents.scoring_agent import ScoringAgent
from app.agents.search_agent import SearchAgent
from app.services.search_engine import SearchEngineService


class PipelineInput(BaseModel):
    """Entrada del pipeline completo."""

    query: str = Field(..., min_length=1)
    max_results: int = Field(30, ge=1, le=100)
    budget_max: float | None = Field(None, ge=0)
    alert_rules: AlertRulesInput = Field(default_factory=AlertRulesInput)


class ResultAlert(BaseModel):
    """Alerta disparada para un resultado concreto."""

    external_id: str | None = None
    recommendation: str
    alerts: list[str] = Field(default_factory=list)


class PipelineOutput(BaseModel):
    """Salida del pipeline: búsqueda real + alertas por reglas."""

    search: SearchAgentOutput
    total_results: int
    alerts: list[ResultAlert] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class PipelineOrchestrator(BaseAgent[PipelineInput, PipelineOutput]):
    """Orquesta el flujo SEARCH → ALERT a través de los agents del dominio."""

    name = "pipeline_orchestrator"
    role = "orchestrator"
    description = (
        "Ejecuta el pipeline completo (búsqueda end-to-end) y aplica las reglas "
        "de alerta sobre cada oportunidad detectada."
    )
    input_type = PipelineInput
    output_type = PipelineOutput
    default_timeout_seconds = 180.0

    def __init__(
        self,
        search_engine: SearchEngineService | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.search_agent = SearchAgent(search_engine=search_engine)
        self.scoring_agent = ScoringAgent()
        self.opportunity_agent = OpportunityAgent()
        self.alert_agent = AlertAgent()

    async def _execute(self, input_data: PipelineInput) -> PipelineOutput:
        search_output = await self.search_agent.run(
            SearchAgentInput(
                query=input_data.query,
                max_results=input_data.max_results,
                budget_max=input_data.budget_max,
            )
        )

        alerts = await self._collect_alerts(search_output, input_data.alert_rules)

        return PipelineOutput(
            search=search_output,
            total_results=len(search_output.results),
            alerts=alerts,
        )

    async def _collect_alerts(
        self,
        search_output: SearchAgentOutput,
        rules: AlertRulesInput,
    ) -> list[ResultAlert]:
        """Aplica las reglas de alerta a cada resultado con oportunidad."""
        if not any((rules.min_level, rules.min_profit is not None, rules.min_roi is not None)):
            return []

        result_alerts: list[ResultAlert] = []
        for result in search_output.results:
            opportunity = getattr(result, "opportunity", None)
            if opportunity is None:
                continue
            alert_output = await self.alert_agent.run(
                AlertAgentInput(
                    opportunity=AlertOpportunityInput(
                        opportunity_level=getattr(opportunity, "opportunity_level", ""),
                        recommendation=getattr(opportunity, "recommendation", ""),
                        estimated_profit=float(
                            getattr(opportunity, "estimated_profit", 0.0) or 0.0
                        ),
                        roi=float(getattr(opportunity, "roi", 0.0) or 0.0),
                    ),
                    rules=rules,
                )
            )
            if not alert_output.triggered:
                continue
            vehicle = getattr(result, "vehicle", None)
            result_alerts.append(
                ResultAlert(
                    external_id=getattr(vehicle, "external_id", None),
                    recommendation=str(getattr(opportunity, "recommendation", "")),
                    alerts=alert_output.alerts,
                )
            )
        return result_alerts
