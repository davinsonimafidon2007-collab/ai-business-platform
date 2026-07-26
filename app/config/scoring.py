"""Constantes configurables para el VehicleScorer.

Todas las reglas de puntuación están centralizadas aquí.
Modificar estos valores cambia el comportamiento del scorer
sin necesidad de tocar el código del mismo.
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# Pesos de cada categoría (la suma define la escala máxima de puntuación)
# =============================================================================
PRICE_WEIGHT: Final[float] = 20.0
MILEAGE_WEIGHT: Final[float] = 17.0
AGE_WEIGHT: Final[float] = 15.0
FUEL_TYPE_WEIGHT: Final[float] = 10.0
TRANSMISSION_WEIGHT: Final[float] = 8.0
POWER_WEIGHT: Final[float] = 12.0
COMPLETENESS_WEIGHT: Final[float] = 10.0
AD_QUALITY_WEIGHT: Final[float] = 8.0

# =============================================================================
# Bonificaciones (expresadas como fracción del peso de la categoría, 0..1)
# =============================================================================
# Precio
NO_PRICE_PENALTY_RATIO: Final[float] = 1.0       # Pierde todo el peso si no hay precio
PRICE_COMPETITIVE_BONUS_RATIO: Final[float] = 0.7  # 70% del peso si es competitivo

# Kilómetros
LOW_MILEAGE_BONUS_RATIO: Final[float] = 0.9
HIGH_MILEAGE_PENALTY_RATIO: Final[float] = 0.6
VERY_HIGH_MILEAGE_PENALTY_RATIO: Final[float] = 1.0

# Antigüedad
RECENT_AGE_BONUS_RATIO: Final[float] = 1.0
MODERATE_AGE_BONUS_RATIO: Final[float] = 0.6
OLD_AGE_PENALTY_RATIO: Final[float] = 0.5
VERY_OLD_PENALTY_RATIO: Final[float] = 1.0

# Potencia
POWER_OPTIMAL_BONUS_RATIO: Final[float] = 0.8
POWER_MODERATE_BONUS_RATIO: Final[float] = 0.4
POWER_PENALTY_RATIO: Final[float] = 0.3

# Imágenes
IMAGE_BONUS_PER_IMAGE: Final[float] = 0.15       # 15% del peso por imagen
MAX_IMAGE_BONUS_RATIO: Final[float] = 1.0        # Máximo 100% del peso

# Descripción
DESCRIPTION_BONUS_RATIO: Final[float] = 1.0      # 100% del peso si hay descripción larga
SHORT_DESCRIPTION_BONUS_RATIO: Final[float] = 0.4

# Información incompleta
PER_FIELD_MISSING_PENALTY_RATIO: Final[float] = 0.15  # 15% del peso por campo faltante
MAX_MISSING_PENALTY_RATIO: Final[float] = 1.0

# =============================================================================
# Umbrales
# =============================================================================
LOW_MILEAGE_THRESHOLD: Final[int] = 50_000
HIGH_MILEAGE_THRESHOLD: Final[int] = 150_000
VERY_HIGH_MILEAGE_THRESHOLD: Final[int] = 250_000

RECENT_AGE_YEARS: Final[int] = 3
MODERATE_AGE_YEARS: Final[int] = 6
OLD_AGE_YEARS: Final[int] = 10
VERY_OLD_AGE_YEARS: Final[int] = 15

OPTIMAL_POWER_MIN: Final[int] = 100
OPTIMAL_POWER_MAX: Final[int] = 250
MODERATE_POWER_MIN: Final[int] = 60
MODERATE_POWER_MAX: Final[int] = 350

DESCRIPTION_MIN_LENGTH: Final[int] = 100
SHORT_DESCRIPTION_MIN_LENGTH: Final[int] = 30

MAX_RELEVANT_IMAGES: Final[int] = 10

# =============================================================================
# Pesos configurables por tipo de combustible
# =============================================================================
FUEL_WEIGHTS: Final[dict[str, float]] = {
    "electric": 1.0,
    "hybrid": 0.9,
    "diesel": 0.7,
    "gasoline": 0.7,
    "petrol": 0.7,
    "lpg": 0.6,
    "cng": 0.6,
    "hydrogen": 0.9,
    "ethanol": 0.5,
}

# =============================================================================
# Pesos configurables por tipo de transmisión
# =============================================================================
TRANSMISSION_WEIGHTS: Final[dict[str, float]] = {
    "automatic": 1.0,
    "semi-automatic": 0.85,
    "manual": 0.6,
    "dsg": 0.95,
    "cvt": 0.8,
    "tiptronic": 0.9,
}

# =============================================================================
# Umbrales para categorías de puntuación
# =============================================================================
SCORE_EXCELLENT: Final[int] = 90
SCORE_VERY_GOOD: Final[int] = 75
SCORE_GOOD: Final[int] = 60
SCORE_ACCEPTABLE: Final[int] = 40

# =============================================================================
# Campos considerados para medir completitud
# =============================================================================
IMPORTANT_FIELDS: Final[list[str]] = [
    "brand",
    "model",
    "year",
    "mileage",
    "fuel_type",
    "transmission",
    "power_hp",
    "price",
]

