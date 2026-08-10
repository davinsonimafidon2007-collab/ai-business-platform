"""Scoring Agent: calcular score de vehículo."""
from __future__ import annotations

from typing import Any

from app.services.vehicle_scorer import VehicleScorer


class ScoringAgent:
    """Agent para calcular score de vehículo.

    Delega en VehicleScorer, el motor real de puntuación por reglas.
    """

    def __init__(self, scorer: VehicleScorer | None = None) -> None:
        self._scorer = scorer or VehicleScorer()

    async def score(self, vehicle_data: dict[str, Any]) -> float:
        """Calcula el score (0-100) de un vehículo a partir de sus campos.

        Args:
            vehicle_data: Dict con los campos del vehículo
                (price, mileage, year, fuel_type, transmission, power_hp,
                description, images, brand, model).

        Returns:
            Puntuación final del vehículo (0-100).
        """
        return float(self._scorer.score_from_dto(**vehicle_data).score)
