"""Re-scoring Agent: recalcular score/ROI cuando cambia el precio."""
from __future__ import annotations


class ReScoringAgent:
    """Agent para recalcular score tras cambios de precio/mercado."""

    async def rescore(self, vehicle_id: str, new_price: float) -> dict:
        return {}
