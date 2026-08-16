"""VehicleScorer — Motor de puntuación objective de vehículos.

Completamente desacoplado del scraping. Recibe un objeto Vehicle
(o DTO equivalente) y devuelve una evaluación objetiva basada
en reglas configurables definidas en app/config/scoring.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from app.config.scoring import (
    AD_QUALITY_WEIGHT,
    AGE_WEIGHT,
    COMPLETENESS_WEIGHT,
    DESCRIPTION_BONUS_RATIO,
    DESCRIPTION_MIN_LENGTH,
    FUEL_TYPE_WEIGHT,
    FUEL_WEIGHTS,
    HIGH_MILEAGE_PENALTY_RATIO,
    HIGH_MILEAGE_THRESHOLD,
    IMAGE_BONUS_PER_IMAGE,
    IMPORTANT_FIELDS,
    LOW_MILEAGE_BONUS_RATIO,
    LOW_MILEAGE_THRESHOLD,
    MAX_IMAGE_BONUS_RATIO,
    MAX_MISSING_PENALTY_RATIO,
    MAX_RELEVANT_IMAGES,
    MILEAGE_WEIGHT,
    MODERATE_AGE_BONUS_RATIO,
    MODERATE_AGE_YEARS,
    MODERATE_POWER_MAX,
    MODERATE_POWER_MIN,
    NO_PRICE_PENALTY_RATIO,
    OLD_AGE_PENALTY_RATIO,
    OLD_AGE_YEARS,
    OPTIMAL_POWER_MAX,
    OPTIMAL_POWER_MIN,
    PER_FIELD_MISSING_PENALTY_RATIO,
    POWER_MODERATE_BONUS_RATIO,
    POWER_OPTIMAL_BONUS_RATIO,
    POWER_PENALTY_RATIO,
    POWER_WEIGHT,
    PRICE_COMPETITIVE_BONUS_RATIO,
    PRICE_WEIGHT,
    RECENT_AGE_BONUS_RATIO,
    RECENT_AGE_YEARS,
    SCORE_ACCEPTABLE,
    SCORE_EXCELLENT,
    SCORE_GOOD,
    SCORE_VERY_GOOD,
    SHORT_DESCRIPTION_BONUS_RATIO,
    SHORT_DESCRIPTION_MIN_LENGTH,
    TRANSMISSION_WEIGHT,
    TRANSMISSION_WEIGHTS,
    VERY_HIGH_MILEAGE_PENALTY_RATIO,
    VERY_HIGH_MILEAGE_THRESHOLD,
    VERY_OLD_AGE_YEARS,
    VERY_OLD_PENALTY_RATIO,
)

# =============================================================================
# Categorías de score (SCORE.1)
# =============================================================================

SCORE_CATEGORY_LABELS_ES: dict[str, str] = {
    "excellent": "Excelente",
    "very_good": "Muy bueno",
    "good": "Bueno",
    "acceptable": "Aceptable",
    "poor": "Malo",
}

SCORE_CATEGORY_KEY_FROM_ES: dict[str, str] = {
    v: k for k, v in SCORE_CATEGORY_LABELS_ES.items()
}


# =============================================================================
# Modelos de salida
# =============================================================================


@dataclass
class ScoreReason:
    """Razón individual que contribuye a la puntuación final.

    Attributes:
        reason: Descripción legible de la razón.
        impact: Impacto numérico en la puntuación (puede ser positivo o negativo).
        is_positive: True si es una bonificación, False si es penalización.
        category: Categoría a la que pertenece (precio, km, antigüedad, etc.).
    """

    reason: str
    impact: float
    is_positive: bool
    category: str


@dataclass
class VehicleScore:
    """Resultado completo de la evaluación de un vehículo.

    Attributes:
        score: Puntuación final de 0 a 100.
        category: Categoría textual (Excelente, Muy bueno, Bueno, Aceptable, Malo).
        reasons: Lista completa de razones que contribuyeron al score.
        strengths: Lista de fortalezas detectadas (razones positivas relevantes).
        weaknesses: Lista de debilidades detectadas (razones negativas relevantes).
    """

    score: int
    category: str  # legacy ES
    category_key: str = "poor"
    category_label_es: str = ""
    reasons: list[ScoreReason] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


# =============================================================================
# Protocolo para datos de entrada
# =============================================================================


class VehicleData(Protocol):
    """Protocolo que define los atributos mínimos que debe exponer
    un objeto para ser evaluado por VehicleScorer.

    Tanto el modelo SQLAlchemy Vehicle como los DTOs VehicleSearchResult
    y VehicleDetail cumplen con este protocolo.
    """

    @property
    def price(self) -> float | None: ...
    @property
    def mileage(self) -> int | None: ...
    @property
    def year(self) -> int | None: ...
    @property
    def fuel_type(self) -> str | None: ...
    @property
    def transmission(self) -> str | None: ...
    @property
    def power_hp(self) -> int | None: ...
    @property
    def description(self) -> str | None: ...
    @property
    def images(self) -> Any: ...  # Puede ser str, list[str] o None
    @property
    def brand(self) -> str | None: ...
    @property
    def model(self) -> str | None: ...


# =============================================================================
# VehicleScorer
# =============================================================================


class VehicleScorer:
    """Scorer de vehículos totalmente desacoplado del scraping.

    Evalúa un vehículo basándose exclusivamente en reglas configurables
    definidas en app/config/scoring.py.

    Uso:
        scorer = VehicleScorer()
        result = scorer.score(vehicle)
        print(result.category, result.score)
    """

    def __init__(self) -> None:
        self._current_year = date.today().year

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def score(self, vehicle: VehicleData) -> VehicleScore:
        """Evalúa un vehículo y devuelve su puntuación completa.

        Args:
            vehicle: Objeto que implementa VehicleData (Vehicle, DTO, etc.).

        Returns:
            VehicleScore con la puntuación, categoría y razones.
        """
        reasons: list[ScoreReason] = []

        # Evaluar cada categoría
        reasons.extend(self._evaluate_price(vehicle))
        reasons.extend(self._evaluate_mileage(vehicle))
        reasons.extend(self._evaluate_age(vehicle))
        reasons.extend(self._evaluate_fuel_type(vehicle))
        reasons.extend(self._evaluate_transmission(vehicle))
        reasons.extend(self._evaluate_power(vehicle))
        reasons.extend(self._evaluate_completeness(vehicle))
        reasons.extend(self._evaluate_ad_quality(vehicle))

        # Calcular puntuación total
        total_score = sum(r.impact for r in reasons)
        total_score = max(0.0, min(100.0, total_score))
        final_score = round(total_score)

        # Determinar categoría
        category_key = self._get_category_key(final_score)
        category_label = SCORE_CATEGORY_LABELS_ES[category_key]

        # Separar fortalezas y debilidades
        strengths = [r.reason for r in reasons if r.is_positive and r.impact > 0]
        weaknesses = [r.reason for r in reasons if not r.is_positive]

        return VehicleScore(
            score=final_score,
            category=category_label,
            category_key=category_key,
            category_label_es=category_label,
            reasons=reasons,
            strengths=strengths,
            weaknesses=weaknesses,
        )

    def score_from_dto(
        self,
        *,
        price: float | None = None,
        mileage: int | None = None,
        year: int | None = None,
        fuel_type: str | None = None,
        transmission: str | None = None,
        power_hp: int | None = None,
        description: str | None = None,
        images: list[str] | None = None,
        brand: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> VehicleScore:
        """Evalúa un vehículo a partir de campos individuales (estilo DTO).

        Útil cuando se tienen datos sueltos sin un objeto Vehicle completo.
        """
        # Creamos un objeto Duck-typed que cumple VehicleData
        class _VehicleProxy:
            def __init__(self) -> None:
                self.price = price
                self.mileage = mileage
                self.year = year
                self.fuel_type = fuel_type
                self.transmission = transmission
                self.power_hp = power_hp
                self.description = description
                self.images = images
                self.brand = brand
                self.model = model

        return self.score(_VehicleProxy())

    # ------------------------------------------------------------------
    # Evaluaciones por categoría
    # ------------------------------------------------------------------

    def _evaluate_price(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa el precio del vehículo.

        - Sin precio → penalización fuerte.
        - Precio competitivo (estimado) → bonificación.
        """
        reasons: list[ScoreReason] = []
        weight = PRICE_WEIGHT

        if vehicle.price is None or vehicle.price <= 0:
            penalty = weight * NO_PRICE_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason="Vehículo sin precio definido",
                impact=-penalty,
                is_positive=False,
                category="price",
            ))
        else:
            # Puntuación base por tener precio
            reasons.append(ScoreReason(
                reason="Precio definido",
                impact=weight * 0.3,
                is_positive=True,
                category="price",
            ))

            # Bonificar precios competitivos (por debajo de un umbral relativo)
            # Usamos una heurística simple: a menor precio relativo, mejor
            bonus = weight * PRICE_COMPETITIVE_BONUS_RATIO
            reasons.append(ScoreReason(
                reason="Precio competitivo",
                impact=bonus,
                is_positive=True,
                category="price",
            ))

        return reasons

    def _evaluate_mileage(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa el kilometraje del vehículo.

        - < 50.000 km → bonificación.
        - > 150.000 km → penalización.
        - > 250.000 km → penalización fuerte.
        """
        reasons: list[ScoreReason] = []
        weight = MILEAGE_WEIGHT

        if vehicle.mileage is None:
            reasons.append(ScoreReason(
                reason="Kilometraje no especificado",
                impact=-weight * 0.3,
                is_positive=False,
                category="mileage",
            ))
            return reasons

        if vehicle.mileage <= LOW_MILEAGE_THRESHOLD:
            bonus = weight * LOW_MILEAGE_BONUS_RATIO
            reasons.append(ScoreReason(
                reason=f"Bajo kilometraje: {vehicle.mileage:,} km",
                impact=bonus,
                is_positive=True,
                category="mileage",
            ))
        elif vehicle.mileage <= HIGH_MILEAGE_THRESHOLD:
            reasons.append(ScoreReason(
                reason=f"Kilometraje moderado: {vehicle.mileage:,} km",
                impact=weight * 0.3,
                is_positive=True,
                category="mileage",
            ))
        elif vehicle.mileage <= VERY_HIGH_MILEAGE_THRESHOLD:
            penalty = weight * HIGH_MILEAGE_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason=f"Kilometraje alto: {vehicle.mileage:,} km",
                impact=-penalty,
                is_positive=False,
                category="mileage",
            ))
        else:
            penalty = weight * VERY_HIGH_MILEAGE_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason=f"Kilometraje muy alto: {vehicle.mileage:,} km",
                impact=-penalty,
                is_positive=False,
                category="mileage",
            ))

        return reasons

    def _evaluate_age(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa la antigüedad del vehículo.

        - ≤ 3 años → bonificación máxima.
        - ≤ 6 años → bonificación moderada.
        - ≤ 10 años → neutro.
        - ≤ 15 años → penalización.
        - > 15 años → penalización fuerte.
        """
        reasons: list[ScoreReason] = []
        weight = AGE_WEIGHT

        if vehicle.year is None:
            reasons.append(ScoreReason(
                reason="Año de fabricación no especificado",
                impact=-weight * 0.3,
                is_positive=False,
                category="age",
            ))
            return reasons

        age = self._current_year - vehicle.year

        if age < 0:
            # Año futuro (posible error, tratar como reciente)
            reasons.append(ScoreReason(
                reason=f"Año de fabricación: {vehicle.year}",
                impact=weight * RECENT_AGE_BONUS_RATIO,
                is_positive=True,
                category="age",
            ))
        elif age <= RECENT_AGE_YEARS:
            reasons.append(ScoreReason(
                reason=f"Vehículo reciente ({age} año{'s' if age != 1 else ''})",
                impact=weight * RECENT_AGE_BONUS_RATIO,
                is_positive=True,
                category="age",
            ))
        elif age <= MODERATE_AGE_YEARS:
            reasons.append(ScoreReason(
                reason=f"Antigüedad moderada ({age} años)",
                impact=weight * MODERATE_AGE_BONUS_RATIO,
                is_positive=True,
                category="age",
            ))
        elif age <= OLD_AGE_YEARS:
            penalty = weight * OLD_AGE_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason=f"Vehículo antiguo ({age} años)",
                impact=-penalty,
                is_positive=False,
                category="age",
            ))
        elif age <= VERY_OLD_AGE_YEARS:
            penalty = weight * VERY_OLD_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason=f"Vehículo muy antiguo ({age} años)",
                impact=-penalty * 0.7,
                is_positive=False,
                category="age",
            ))
        else:
            penalty = weight * VERY_OLD_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason=f"Vehículo excesivamente antiguo ({age} años)",
                impact=-penalty,
                is_positive=False,
                category="age",
            ))

        return reasons

    def _evaluate_fuel_type(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa el tipo de combustible según pesos configurables."""
        reasons: list[ScoreReason] = []
        weight = FUEL_TYPE_WEIGHT

        if vehicle.fuel_type is None:
            reasons.append(ScoreReason(
                reason="Tipo de combustible no especificado",
                impact=-weight * 0.3,
                is_positive=False,
                category="fuel_type",
            ))
            return reasons

        fuel_norm = vehicle.fuel_type.strip().lower()
        fuel_weight = FUEL_WEIGHTS.get(fuel_norm, 0.5)

        impact = weight * fuel_weight
        reasons.append(ScoreReason(
            reason=f"Combustible: {vehicle.fuel_type}",
            impact=impact,
            is_positive=True,
            category="fuel_type",
        ))

        return reasons

    def _evaluate_transmission(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa el tipo de transmisión según pesos configurables."""
        reasons: list[ScoreReason] = []
        weight = TRANSMISSION_WEIGHT

        if vehicle.transmission is None:
            reasons.append(ScoreReason(
                reason="Tipo de transmisión no especificado",
                impact=-weight * 0.3,
                is_positive=False,
                category="transmission",
            ))
            return reasons

        trans_norm = vehicle.transmission.strip().lower()
        trans_weight = TRANSMISSION_WEIGHTS.get(trans_norm, 0.5)

        impact = weight * trans_weight
        reasons.append(ScoreReason(
            reason=f"Transmisión: {vehicle.transmission}",
            impact=impact,
            is_positive=True,
            category="transmission",
        ))

        return reasons

    def _evaluate_power(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa la potencia del vehículo según rango óptimo configurable."""
        reasons: list[ScoreReason] = []
        weight = POWER_WEIGHT

        if vehicle.power_hp is None:
            reasons.append(ScoreReason(
                reason="Potencia no especificada",
                impact=-weight * 0.2,
                is_positive=False,
                category="power",
            ))
            return reasons

        power = vehicle.power_hp

        if OPTIMAL_POWER_MIN <= power <= OPTIMAL_POWER_MAX:
            reasons.append(ScoreReason(
                reason=f"Potencia óptima: {power} HP",
                impact=weight * POWER_OPTIMAL_BONUS_RATIO,
                is_positive=True,
                category="power",
            ))
        elif MODERATE_POWER_MIN <= power <= MODERATE_POWER_MAX:
            reasons.append(ScoreReason(
                reason=f"Potencia moderada: {power} HP",
                impact=weight * POWER_MODERATE_BONUS_RATIO,
                is_positive=True,
                category="power",
            ))
        else:
            penalty = weight * POWER_PENALTY_RATIO
            reasons.append(ScoreReason(
                reason=f"Potencia fuera de rango óptimo: {power} HP",
                impact=-penalty,
                is_positive=False,
                category="power",
            ))

        return reasons

    def _evaluate_completeness(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa la completitud de la información del anuncio.

        Penaliza anuncios con muchos campos vacíos o nulos.
        """
        reasons: list[ScoreReason] = []
        weight = COMPLETENESS_WEIGHT

        missing = 0
        total_fields = len(IMPORTANT_FIELDS)

        for field_name in IMPORTANT_FIELDS:
            value = getattr(vehicle, field_name, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing += 1

        if missing == 0:
            reasons.append(ScoreReason(
                reason="Información completa en campos esenciales",
                impact=weight * 0.5,
                is_positive=True,
                category="completeness",
            ))
        else:
            penalty_ratio = min(missing / total_fields * PER_FIELD_MISSING_PENALTY_RATIO, MAX_MISSING_PENALTY_RATIO)
            penalty = weight * penalty_ratio
            reasons.append(ScoreReason(
                reason=f"{missing} campo{'s' if missing != 1 else ''} esencial{'es' if missing != 1 else ''} sin especificar",
                impact=-penalty,
                is_positive=False,
                category="completeness",
            ))

        return reasons

    def _evaluate_ad_quality(self, vehicle: VehicleData) -> list[ScoreReason]:
        """Evalúa la calidad del anuncio.

        - Bonifica varias imágenes.
        - Bonifica descripción completa.
        """
        reasons: list[ScoreReason] = []
        weight = AD_QUALITY_WEIGHT

        # --- Imágenes ---
        image_count = self._count_images(vehicle)

        if image_count == 0:
            reasons.append(ScoreReason(
                reason="Sin imágenes",
                impact=-weight * 0.4,
                is_positive=False,
                category="ad_quality",
            ))
        else:
            bonus_ratio = min(image_count * IMAGE_BONUS_PER_IMAGE, MAX_IMAGE_BONUS_RATIO)
            bonus = weight * bonus_ratio
            reasons.append(ScoreReason(
                reason=f"{image_count} imagen{'es' if image_count != 1 else ''} disponible{'s' if image_count != 1 else ''}",
                impact=bonus,
                is_positive=True,
                category="ad_quality",
            ))

        # --- Descripción ---
        desc = vehicle.description
        if desc is None or desc.strip() == "":
            reasons.append(ScoreReason(
                reason="Sin descripción",
                impact=-weight * 0.3,
                is_positive=False,
                category="ad_quality",
            ))
        elif len(desc) >= DESCRIPTION_MIN_LENGTH:
            reasons.append(ScoreReason(
                reason="Descripción detallada y completa",
                impact=weight * DESCRIPTION_BONUS_RATIO,
                is_positive=True,
                category="ad_quality",
            ))
        elif len(desc) >= SHORT_DESCRIPTION_MIN_LENGTH:
            reasons.append(ScoreReason(
                reason="Descripción breve pero informativa",
                impact=weight * SHORT_DESCRIPTION_BONUS_RATIO,
                is_positive=True,
                category="ad_quality",
            ))
        else:
            reasons.append(ScoreReason(
                reason="Descripción muy corta",
                impact=weight * 0.1,
                is_positive=True,
                category="ad_quality",
            ))

        return reasons

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------

    @staticmethod
    def _get_category_key(score: float) -> str:
        """Convierte una puntuación numérica en clave estable de categoría."""
        if score >= SCORE_EXCELLENT:
            return "excellent"
        if score >= SCORE_VERY_GOOD:
            return "very_good"
        if score >= SCORE_GOOD:
            return "good"
        if score >= SCORE_ACCEPTABLE:
            return "acceptable"
        return "poor"

    @classmethod
    def _get_category(cls, score: float) -> str:
        """Compat: label ES (comportamiento anterior)."""
        return SCORE_CATEGORY_LABELS_ES[cls._get_category_key(score)]

    @staticmethod
    def _count_images(vehicle: VehicleData) -> int:
        """Cuenta las imágenes del vehículo soportando distintos formatos."""
        images = vehicle.images

        if images is None:
            return 0

        if isinstance(images, list):
            return min(len(images), MAX_RELEVANT_IMAGES)

        if isinstance(images, str):
            images_str = images.strip()
            if not images_str:
                return 0
            # Puede ser una lista separada por comas o una única URL
            parts = [p.strip() for p in images_str.split(",") if p.strip()]
            return min(len(parts), MAX_RELEVANT_IMAGES)

        return 0

