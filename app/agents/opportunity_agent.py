"""Opportunity Agent: clasificar oportunidades basadas en ROI/coste/mercado."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import OpportunityAgentInput, OpportunityAgentOutput
from app.services.opportunity_finder import OpportunityFinder


class _VehicleScoreShim:
    """Adaptador VehicleScoreData -> objeto duck-typed para OpportunityFinder."""

    def __init__(self, data: object) -> None:
        self.score = getattr(data, "score", 0)
        self.strengths = list(getattr(data, "strengths", []) or [])
        self.weaknesses = list(getattr(data, "weaknesses", []) or [])


class _MarketEstimationShim:
    """Adaptador MarketEstimationData -> objeto duck-typed para OpportunityFinder."""

    def __init__(self, data: object) -> None:
        self.market_price = getattr(data, "market_price", 0.0)
        self.confidence = getattr(data, "confidence", 50.0)
        self.supply_level = getattr(data, "supply_level", 50.0)
        self.demand_level = getattr(data, "demand_level", 50.0)
        self.market_trend = getattr(data, "market_trend", "stable")


class OpportunityAgent(BaseAgent[OpportunityAgentInput, OpportunityAgentOutput]):
    """Agent del pipeline OPPORTUNITY.

    Delega en OpportunityFinder, el motor real de clasificación que combina
    scoring, rentabilidad y mercado. Devuelve el análisis completo (no solo la
    recomendación, como hacía la versión anterior).
    """

    name = "opportunity_agent"
    role = "opportunity"
    description = (
        "Clasifica una oportunidad de importación (BUY_NOW / NEGOTIATE / WATCH "
        "/ REJECT) combinando score del vehículo, rentabilidad y mercado."
    )
    input_type = OpportunityAgentInput
    output_type = OpportunityAgentOutput
    default_timeout_seconds = 10.0

    def __init__(
        self,
        opportunity_finder: OpportunityFinder | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._finder = opportunity_finder or OpportunityFinder()

    async def _execute(self, input_data: OpportunityAgentInput) -> OpportunityAgentOutput:
        analysis = self._finder.analyze(
            _VehicleScoreShim(input_data.vehicle_score),
            input_data.profit_analysis,
            _MarketEstimationShim(input_data.market_estimation),
        )
        return OpportunityAgentOutput(
            overall_score=analysis.overall_score,
            opportunity_level=analysis.opportunity_level.value,
            recommendation=(
                analysis.recommendation.value
                if hasattr(analysis.recommendation, "value")
                else str(analysis.recommendation)
            ),
            estimated_profit=float(analysis.estimated_profit or 0.0),
            roi=float(analysis.roi or 0.0),
            market_confidence=float(analysis.market_confidence or 0.0),
            risk_level=str(analysis.risk_level),
            strengths=analysis.strengths,
            weaknesses=analysis.weaknesses,
        )
