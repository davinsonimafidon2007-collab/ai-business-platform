"""Configuración del motor de negociación (NegotiationEngine).

Todos los umbrales y parámetros están centralizados aquí
siguiendo el mismo patrón que app/config/scoring.py, app/config/opportunity.py, etc.
"""

from __future__ import annotations

# =============================================================================
# Pesos para apalancamiento (leverage score)
# =============================================================================

LEVERAGE_DEFECT_WEIGHT: float = 0.30
"""Peso de los defectos en el leverage score (0-1)."""

LEVERAGE_REPAIR_COST_WEIGHT: float = 0.15
"""Peso del coste de reparación en el leverage score (0-1)."""

LEVERAGE_ACCIDENT_WEIGHT: float = 0.15
"""Peso del historial de accidentes en el leverage score (0-1)."""

LEVERAGE_MARKET_WEIGHT: float = 0.20
"""Peso de las condiciones de mercado en el leverage score (0-1)."""

LEVERAGE_VEHICLE_SCORE_WEIGHT: float = 0.10
"""Peso del score del vehículo en el leverage score (0-1)."""

LEVERAGE_PROFIT_WEIGHT: float = 0.10
"""Peso del beneficio/ROI en el leverage score (0-1)."""

# =============================================================================
# Umbrales de recomendación
# =============================================================================

BUY_MAX_DISCOUNT_NEEDED: float = 5.0
"""Si el descuento necesario es ≤ 5%, recomendar BUY."""

WALK_AWAY_MIN_DISCOUNT_NEEDED: float = 25.0
"""Si el descuento necesario es ≥ 25%, recomendar WALK_AWAY."""

BUY_MIN_LEVERAGE_SCORE: float = 0.0
"""No requerido para BUY (se basa en discount_needed)."""

NEGOTIATE_MIN_LEVERAGE_SCORE: float = 20.0
"""Leverage mínimo para poder negociar con posibilidades."""

# =============================================================================
# Límites de precio
# =============================================================================

COUNTER_OFFER_MULTIPLIER: float = 0.03
"""Incremento sobre initial_offer para la contraoferta (3%)."""

MAX_INITIAL_OFFER_PERCENT_OF_VALUE: float = 0.90
"""Oferta inicial máxima como porcentaje del valor estimado (90%)."""

MAX_PURCHASE_PRICE_MULTIPLIER: float = 1.05
"""Precio máximo que se puede pagar como multiplicador del valor estimado (105%)."""

# CRÍTICO: walk-away DEBE ser <= max purchase.
# El comprador abandona cuando el vendedor exige más que el techo de compra.
WALK_AWAY_MULTIPLIER: float = 1.05
"""Walk-away price = mismo techo que max purchase (105% del valor estimado)."""

# Suelo de oferta inicial: no bajar del X% del valor estimado (no del asking).
# Evita ofertas irreales cuando el asking está muy hinchado.
MIN_OFFER_PERCENT_OF_VALUE: float = 0.70
"""Oferta inicial mínima como porcentaje del valor estimado (70%)."""

# Descuento por historial de accidentes (único valor, usado en valor Y en argumentos)
ACCIDENT_DISCOUNT_PERCENT: float = 0.10
"""Descuento sobre market_price si hay historial de accidentes (10%)."""

# =============================================================================
# Umbrales de negociación
# =============================================================================

MIN_PROFIT_FOR_NEGOTIATE: float = 0.0
"""Beneficio mínimo para recomendar NEGOTIATE (EUR). Si es menor, WALK_AWAY."""

MIN_ROI_FOR_BUY: float = 5.0
"""ROI mínimo (%) para recomendar BUY directamente."""

MIN_MARGIN_FOR_BUY: float = 10.0
"""Margen mínimo (%) para recomendar BUY directamente."""

HIGH_SEVERITY_THRESHOLD: int = 7
"""A partir de qué severidad un defecto se considera grave."""

SAFETY_DEFECT_SEVERITY_BOOST: float = 1.5
"""Multiplicador de impacto económico para defectos de seguridad."""

# =============================================================================
# Generación de script de negociación
# =============================================================================

MAX_SCRIPT_DEFECT_POINTS: int = 5
"""Máximo de puntos basados en defectos en el script de negociación."""

MAX_SCRIPT_MARKET_POINTS: int = 3
"""Máximo de puntos basados en mercado en el script de negociación."""