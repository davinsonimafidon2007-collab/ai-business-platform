"""Opportunity Integration Service — Conecta opportunity con deal pipeline."""
from __future__ import annotations

from typing import Any

from app.services.opportunity_finder import OpportunityFinder
from app.services.deal_service import DealService


class OpportunityIntegrationService:
    """Integra el análisis de oportunidades con el pipeline de deals."""

    def __init__(self, deal_service: DealService | None = None) -> None:
        self.opportunity_finder = OpportunityFinder()
        self.deal_service = deal_service

    async def analyze_and_create_deal(
        self, vehicle_data: dict, user_id: str
    ) -> dict[str, Any]:
        """Analiza oportunidad y crea deal asociado si aplica."""
        analysis = self.opportunity_finder.analyze(
            vehicle_score=vehicle_data,
            profit_analysis={},
            market_estimation=None,
        )
        deal_result = None
        if self.deal_service and analysis.get("recommendation") in (
            "BUY_NOW",
            "NEGOTIATE",
        ):
            deal_result = await self.deal_service.create(
                user_id=user_id,
                opportunity_id=str(vehicle_data.get("id", "unknown")),
                notes=f"Oportunidad: {analysis.get('recommendation', 'WATCH')}",
            )
        return {"analysis": analysis, "deal": deal_result}
