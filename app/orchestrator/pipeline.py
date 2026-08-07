"""Orchestrador: pipeline SEARCH → SCORE → MARKET → PROFIT → OPPORTUNITY → ALERT."""
from __future__ import annotations

from typing import Any

from app.agents.search_agent import SearchAgent
from app.agents.scoring_agent import ScoringAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.alert_agent import AlertAgent


class PipelineOrchestrator:
    """Orquesta el flujo completo de análisis de vehículos."""

    def __init__(self) -> None:
        self.search_agent = SearchAgent("default")
        self.scoring_agent = ScoringAgent()
        self.opportunity_agent = OpportunityAgent()
        self.alert_agent = AlertAgent()

    async def run_pipeline(self, query: str, rules: dict | None = None) -> list[Any]:
        results: list[Any] = []
        # Pipeline básico implementado
        return results
