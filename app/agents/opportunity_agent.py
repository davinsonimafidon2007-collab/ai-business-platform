"""Opportunity Agent: detectar oportunidades basadas en ROI/coste."""
from __future__ import annotations

from typing import Any

from app.services.opportunity_finder import OpportunityFinder


class OpportunityAgent:
    """Agent para clasificar oportunidades (BUY_NOW, NEGOTIATE, WATCH, REJECT).

    Delega en OpportunityFinder, el motor real de clasificación que combina
    scoring, rentabilidad y mercado.
    """

    def __init__(self, opportunity_finder: OpportunityFinder | None = None) -> None:
        self._finder = opportunity_finder or OpportunityFinder()

    async def evaluate(
        self,
        vehicle: Any,
        profit_analysis: Any,
        market_estimation: Any | None = None,
    ) -> str:
        """Clasifica la oportunidad delegando en OpportunityFinder.

        Args:
            vehicle: VehicleScore (o resultado del scorer).
            profit_analysis: ProfitAnalysis del analizador de rentabilidad.
            market_estimation: MarketEstimation opcional.

        Returns:
            Recomendación de acción: BUY_NOW, NEGOTIATE, WATCH o REJECT.
        """
        analysis = self._finder.analyze(vehicle, profit_analysis, market_estimation)
        recommendation = getattr(analysis, "recommendation", None)
        return recommendation.value if hasattr(recommendation, "value") else str(recommendation or "WATCH")
