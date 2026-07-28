"""NegotiationProvider — Interfaz para proveedores de estrategia de negociación.

Define el protocolo que debe implementar cualquier motor de negociación.
El SearchOrchestrator puede depender de esta interfaz mediante inyección
de dependencias, permitiendo que futuras implementaciones se integren
sin modificar el orquestador.

Sigue el mismo patrón que ``MarketEstimator`` (app/services/market_estimator.py).
"""

from __future__ import annotations

from typing import Protocol

from app.models.negotiation import NegotiationInput, NegotiationResult


class NegotiationProvider(Protocol):
    """Protocolo para proveedores de estrategia de negociación.

    Cualquier clase que implemente este protocolo debe proporcionar
    un método ``analyze`` que reciba un ``NegotiationInput`` y devuelva
    un ``NegotiationResult``.
    """

    def analyze(self, input_data: NegotiationInput) -> NegotiationResult:
        """Analiza y genera una estrategia de negociación completa.

        Args:
            input_data: NegotiationInput con toda la información agregada
                (inspección, reparación, mercado, rentabilidad, etc.).

        Returns:
            NegotiationResult con la estrategia completa de negociación
            (precios recomendados, argumentos, script, recomendación).
        """
        ...