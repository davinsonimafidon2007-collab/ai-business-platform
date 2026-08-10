"""Negotiation Agent: preparar propuesta de negociación."""
from __future__ import annotations

from typing import Any

from app.services.negotiation_engine import NegotiationEngine


class NegotiationAgent:
    """Agent para preparar argumentos y precios objetivo en negociación.

    Delega en NegotiationEngine (motor real de estrategia de negociación).
    """

    def __init__(self, engine: NegotiationEngine | None = None) -> None:
        self._engine = engine or NegotiationEngine()

    async def prepare_offer(
        self,
        deal: dict[str, Any],
        defects: list[str],
        target_price: float,
        *,
        negotiation_input: Any | None = None,
    ) -> Any:
        """Prepara la propuesta de negociación delegando en NegotiationEngine.

        Args:
            deal: Datos del deal (contexto, se mantiene en el resultado).
            defects: Lista de defectos (contexto, se mantiene en el resultado).
            target_price: Precio objetivo (contexto, se mantiene en el resultado).
            negotiation_input: NegotiationInput del modelo
                ``app.models.negotiation`` con inspección, reparación,
                mercado y rentabilidad.

        Returns:
            Resultado del NegotiationEngine (NegotiationResult).

        Raises:
            ValueError: Si no se aporta negotiation_input.
        """
        if negotiation_input is None:
            raise ValueError(
                "prepare_offer requiere 'negotiation_input' (NegotiationInput de "
                "app.models.negotiation) para ejecutar la negociación real."
            )

        result = self._engine.analyze(negotiation_input)
        return {
            "deal": deal,
            "defects": defects,
            "target_price": target_price,
            "negotiation": result,
        }
