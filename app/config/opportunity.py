"""Constantes configurables para el OpportunityFinder.

Todas las reglas de detección de oportunidades están centralizadas aquí.
Modificar estos valores cambia el comportamiento del finder
sin necesidad de tocar el código del mismo.
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# Pesos para el cálculo del overall_score (deben sumar 1.0)
# =============================================================================

VEHICLE_SCORE_WEIGHT: Final[float] = 0.30
"""Peso del VehicleScore en el overall_score (30% por defecto)."""

PROFIT_WEIGHT: Final[float] = 0.40
"""Peso del ProfitAnalysis en el overall_score (40% por defecto)."""

MARKET_CONFIDENCE_WEIGHT: Final[float] = 0.30
"""Peso del MarketEstimation en el overall_score (30% por defecto)."""


# =============================================================================
# Umbrales para OpportunityLevel
# =============================================================================

EXCELLENT_THRESHOLD: Final[float] = 85.0
"""Score mínimo para considerar EXCELLENT."""

GOOD_THRESHOLD: Final[float] = 70.0
"""Score mínimo para considerar GOOD."""

AVERAGE_THRESHOLD: Final[float] = 50.0
"""Score mínimo para considerar AVERAGE."""

POOR_THRESHOLD: Final[float] = 30.0
"""Score mínimo para considerar POOR. Por debajo es REJECT."""


# =============================================================================
# Umbrales para Recommendation
# =============================================================================

BUY_NOW_MIN_SCORE: Final[float] = 80.0
"""Score mínimo para recomendar BUY_NOW."""

BUY_NOW_MIN_ROI: Final[float] = 15.0
"""ROI mínimo (%) para recomendar BUY_NOW."""

BUY_NOW_MIN_CONFIDENCE: Final[float] = 70.0
"""Confianza mínima de mercado para BUY_NOW."""

WATCH_MAX_SCORE: Final[float] = 79.0
"""Score máximo para considerar WATCH (no es BUY_NOW pero es viable)."""

WATCH_MIN_SCORE: Final[float] = 55.0
"""Score mínimo para considerar WATCH."""

NEGOTIATE_MAX_SCORE: Final[float] = 69.0
"""Score máximo para NEGOTIATE."""

NEGOTIATE_MIN_SCORE: Final[float] = 40.0
"""Score mínimo para NEGOTIATE."""


# =============================================================================
# Normalización del ProfitAnalysis
# =============================================================================

PROFIT_ROI_HIGH_THRESHOLD: Final[float] = 20.0
"""ROI (%) por encima de este valor se considera excelente (score=100)."""

PROFIT_ROI_LOW_THRESHOLD: Final[float] = 0.0
"""ROI (%) por debajo de este valor se considera mínimo (score=0)."""

PROFIT_NET_PROFIT_HIGH_THRESHOLD: Final[float] = 5000.0
"""Beneficio neto (EUR) por encima se considera excelente."""

PROFIT_NET_PROFIT_LOW_THRESHOLD: Final[float] = 0.0
"""Beneficio neto (EUR) por debajo se considera mínimo."""


# =============================================================================
# Bonificaciones y penalizaciones
# =============================================================================

LOW_PRICE_BONUS: Final[float] = 10.0
"""Puntos extra si el vehículo tiene un precio muy competitivo (< 10,000 EUR)."""

HIGH_ROI_BONUS: Final[float] = 10.0
"""Puntos extra si el ROI supera el threshold alto."""

LOW_CONFIDENCE_PENALTY: Final[float] = 10.0
"""Penalización si la confianza de mercado es baja (< 40)."""

LOW_MARGIN_PENALTY: Final[float] = 5.0
"""Penalización si el margen es ajustado (ROI < 5%)."""

NEGATIVE_PROFIT_PENALTY: Final[float] = 20.0
"""Penalización fuerte si hay pérdidas."""

HIGH_RISK_PENALTY: Final[float] = 15.0
"""Penalización si el riesgo es HIGH."""


# =============================================================================
# Umbrales para explicaciones (strengths / weaknesses)
# =============================================================================

PRICE_COMPETITIVE_THRESHOLD: Final[float] = 10_000.0
"""Por debajo de este precio (EUR) se considera muy competitivo."""

LOW_MILEAGE_THRESHOLD: Final[float] = 50_000.0
"""Por debajo de este kilometraje se considera bajo."""

HIGH_MILEAGE_THRESHOLD: Final[float] = 150_000.0
"""Por encima de este kilometraje se considera alto."""

GOOD_ROI_THRESHOLD: Final[float] = 10.0
"""Por encima de este ROI (%) se considera bueno."""

LOW_CONFIDENCE_EXPLANATION_THRESHOLD: Final[float] = 40.0
"""Por debajo de esta confianza se muestra como debilidad."""

HIGH_CONFIDENCE_EXPLANATION_THRESHOLD: Final[float] = 70.0
"""Por encima de esta confianza se muestra como fortaleza."""

SATURATED_SUPPLY_THRESHOLD: Final[float] = 70.0
"""Por encima de este nivel de oferta, el mercado está saturado."""

HIGH_DEMAND_THRESHOLD: Final[float] = 70.0
"""Por encima de este nivel de demanda, el mercado es favorable."""

