"""Opportunity Agent: detectar oportunidades basadas en ROI/coste."""
from __future__ import annotations


class OpportunityAgent:
    """Agent para clasificar oportunidades (BUY, NEGOTIATE, WATCH, PASS)."""

    async def evaluate(self, vehicle: dict, profit_analysis: dict) -> str:
        return "WATCH"
