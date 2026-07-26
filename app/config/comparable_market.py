"""Configuración del ComparableMarketEstimator.

Todas las tolerancias, pesos y umbrales centralizados aquí.
Modificar estos valores cambia el comportamiento sin tocar el código.
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# Tolerancias para filtrar comparables
# =============================================================================

YEAR_TOLERANCE: Final[int] = 2
"""± años respecto al año del vehículo objetivo."""

MILEAGE_TOLERANCE_PERCENT: Final[float] = 20.0
"""± porcentaje de kilometraje respecto al vehículo objetivo."""

REQUIRE_SAME_BRAND: Final[bool] = True
"""Exigir misma marca en los comparables."""

REQUIRE_SAME_MODEL: Final[bool] = True
"""Exigir mismo modelo en los comparables."""

REQUIRE_SAME_FUEL: Final[bool] = True
"""Exigir mismo tipo de combustible."""

REQUIRE_SAME_TRANSMISSION: Final[bool] = True
"""Exigir misma transmisión."""

# =============================================================================
# Pesos de similitud para ponderar comparables
# =============================================================================

WEIGHT_SAME_BRAND: Final[float] = 0.20
"""Peso por coincidir en marca."""

WEIGHT_SAME_MODEL: Final[float] = 0.30
"""Peso por coincidir en modelo."""

WEIGHT_YEAR_SIMILARITY: Final[float] = 0.20
"""Peso por cercanía del año."""

WEIGHT_MILEAGE_SIMILARITY: Final[float] = 0.15
"""Peso por cercanía del kilometraje."""

WEIGHT_SAME_FUEL: Final[float] = 0.10
"""Peso por coincidir en combustible."""

WEIGHT_SAME_TRANSMISSION: Final[float] = 0.05
"""Peso por coincidir en transmisión."""

# =============================================================================
# Pesos para el cálculo de confianza
# =============================================================================

CONFIDENCE_MAX_COUNT: Final[int] = 10
"""Nº de comparables a partir del cual la confianza por conteo es máxima."""

CONFIDENCE_COUNT_WEIGHT: Final[float] = 0.25
"""Peso del número de comparables en la confianza."""

CONFIDENCE_DISPERSION_WEIGHT: Final[float] = 0.25
"""Peso de la dispersión (CV bajo → más confianza)."""

CONFIDENCE_DIVERSITY_WEIGHT: Final[float] = 0.10
"""Peso de la diversidad de providers."""

CONFIDENCE_FRESHNESS_WEIGHT: Final[float] = 0.10
"""Peso de la frescura de los datos."""

CONFIDENCE_SIMILARITY_WEIGHT: Final[float] = 0.15
"""Peso de la similitud media de los comparables."""

CONFIDENCE_DISCARDED_WEIGHT: Final[float] = 0.15
"""Peso de la proporción de descartados (menos descartados → más confianza)."""

# =============================================================================
# Cache TTL
# =============================================================================

CACHE_TTL_SECONDS: Final[int] = 86_400
"""TTL de la caché de estimaciones de mercado en segundos (1 día)."""

# =============================================================================
# Umbrales para detección de precio
# =============================================================================

OVERRICED_PERCENTILE: Final[float] = 80.0
"""Por encima de este percentil se considera sobreprecio."""

UNDERPRICED_PERCENTILE: Final[float] = 20.0
"""Por debajo de este percentil se considera infravalorado."""

# =============================================================================
# Hash
# =============================================================================

MARKET_HASH_YEAR_BUCKET: Final[int] = 2
"""Tamaño del bucket de año para el hash (agrupa ±2 años)."""

MARKET_HASH_MILEAGE_BUCKET: Final[int] = 20_000
"""Tamaño del bucket de kilometraje para el hash (agrupa ±20k km)."""

