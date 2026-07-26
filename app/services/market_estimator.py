"""MarketEstimator — Interfaz para estimación de mercado.

Define el protocolo que debe implementar cualquier estimador de mercado.
El SearchOrchestrator depende de esta interfaz mediante inyección de dependencias,
permitiendo que futuras implementaciones (ComparableMarketEstimator, etc.)
se integren sin modificar el orquestador.
"""

from __future__ import annotations

from typing import Protocol

from app.models.market import MarketEstimation


class MarketEstimator(Protocol):
    """Protocolo para estimadores de mercado.

    Cualquier clase que implemente este protocolo debe proporcionar
    un método ``estimate`` que reciba un vehículo y devuelva una
    ``MarketEstimation``.
    """

    def estimate(self, vehicle: object) -> MarketEstimation:
        """Estima las condiciones de mercado para un vehículo.

        Args:
            vehicle: Objeto que implementa VehicleData (Vehicle, DTO, etc.).

        Returns:
            MarketEstimation con la estimación de mercado.
        """
        ...

