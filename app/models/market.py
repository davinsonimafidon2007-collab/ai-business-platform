"""Modelos de datos para estimaciones de mercado.

Estos DTOs son independientes del motor de estimación y pueden ser
consumidos tanto por OpportunityFinder como por el futuro MarketPriceEstimator.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketEstimation:
    """Estimación del mercado para un vehículo específico.

    Representa el análisis de mercado independiente del scoring y
    del análisis económico. El futuro MarketPriceEstimator devolverá
    instancias de este mismo DTO.

    Attributes:
        market_price: Precio estimado de mercado en el país de destino (EUR).
        confidence: Nivel de confianza de la estimación (0-100).
        supply_level: Nivel de oferta en el mercado (0-100, mayor = más oferta).
        demand_level: Nivel de demanda en el mercado (0-100, mayor = más demanda).
        market_trend: Tendencia del mercado ("rising", "stable", "falling").
        comparable_count: Número de vehículos comparables encontrados.
        notes: Notas adicionales sobre la estimación (pares clave=valor machine-readable).
        explanation: Texto legible (ES) del diferencial de precio vs comparables.

    """

    market_price: float
    """Precio estimado de mercado en EUR."""

    confidence: float
    """Nivel de confianza de 0 (mínima) a 100 (máxima)."""

    supply_level: float = 50.0
    """Nivel de oferta (0 = escasez, 100 = abundancia)."""

    demand_level: float = 50.0
    """Nivel de demanda (0 = mínima, 100 = máxima)."""

    market_trend: str = "stable"
    """Tendencia: 'rising', 'stable', o 'falling'."""

    comparable_count: int = 0
    """Número de comparables encontrados."""

    notes: list[str] = field(default_factory=list)
    """Notas adicionales sobre la estimación (pares clave=valor machine-readable)."""

    explanation: str = ""
    """Texto legible (ES) del diferencial de precio vs comparables."""
