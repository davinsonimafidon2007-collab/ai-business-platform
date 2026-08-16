"""Re-scoring Agent: recalcular score/ROI cuando cambia el precio."""
from __future__ import annotations

from typing import Any

from app.services.vehicle_scorer import VehicleScorer


class ReScoringAgent:
    """Agent para recalcular score tras cambios de precio/mercado.

    Delega en VehicleScorer (motor real de puntuación por reglas).
    """

    def __init__(self, scorer: VehicleScorer | None = None) -> None:
        self._scorer = scorer or VehicleScorer()

    async def rescore(
        self,
        vehicle_id: str,
        new_price: float,
        vehicle_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Recalcula el score con el nuevo precio.

        Args:
            vehicle_id: Identificador del vehículo.
            new_price: Nuevo precio de compra (EUR).
            vehicle_data: Dict con los campos del vehículo
                (price, mileage, year, fuel_type, transmission, power_hp,
                description, images, brand, model).

        Returns:
            Dict con vehicle_id, new_price, score y categoría.

        Raises:
            ValueError: Si no se aporta vehicle_data.
        """
        if not vehicle_data:
            raise ValueError(
                "rescore requiere 'vehicle_data' (dict) con los campos del vehículo."
            )

        data = dict(vehicle_data)
        data["price"] = new_price
        score = self._scorer.score_from_dto(**data)
        return {
            "vehicle_id": vehicle_id,
            "new_price": new_price,
            "score": score.score,
            "category": score.category_key,
        }
