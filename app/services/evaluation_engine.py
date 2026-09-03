"""Motor de evaluación de vehículos para calcular costes y rentabilidad.

El bloque económico se delega en ProfitAnalyzer (misma fuente de verdad
que search / simulate-profit). El engine conserva únicamente el scoring
propio (score, clasificación, advertencias y recomendación alineada).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings
from app.models.vehicle import Vehicle
from app.services.confidence import estimate_confidence
from app.services.profit_analyzer import ProfitAnalyzer, ProfitRecommendation


@dataclass
class EvaluationResult:
    """Resultado de la evaluación de un vehículo."""

    # Costes
    vehicle_cost: float  # Precio de compra del vehículo
    transport_cost: float  # Coste de transporte desde Alemania
    registration_cost: float  # Coste de matriculación
    itv_cost: float  # Coste de la ITV
    gestoria_cost: float  # Coste de gestoría
    taxes_cost: float  # Impuestos (IVA, etc.)
    total_cost: float  # Coste total

    # Estimaciones de venta
    estimated_sale_price_es: float  # Precio estimado de venta en España
    gross_profit: float  # Beneficio bruto
    profit_margin_percent: float  # Margen porcentual

    # Score y clasificación
    score: int  # Score de 0 a 100
    classification: str  # "verde", "amarillo", "rojo"
    warnings: list[str]  # Lista de advertencias
    recommendation: str  # Recomendación
    confidence: float = 0.0  # TASK 2: confianza 0-100, ver app/services/confidence.py


class EvaluationEngine:
    """Motor de evaluación de vehículos.

    Delega el bloque económico en ProfitAnalyzer con el perfil de costes
    por defecto (settings.default_import_cost_profile, SPAIN por defecto)
    y conserva el scoring propio (score, clasificación, advertencias).
    """

    # Margen mínimo aceptable
    MIN_PROFIT_MARGIN_PERCENT: float = 15.0
    WARNING_PROFIT_MARGIN_PERCENT: float = 8.0

    # Umbrales de score
    GREEN_SCORE_THRESHOLD: int = 70
    YELLOW_SCORE_THRESHOLD: int = 40

    def __init__(
        self,
        profit_analyzer: ProfitAnalyzer | None = None,
        import_cost_profile: str | None = None,
    ) -> None:
        """Inicializa el motor de evaluación.

        Args:
            profit_analyzer: Analizador económico (ProfitAnalyzer por defecto).
            import_cost_profile: Perfil de costes de importación
                (settings.default_import_cost_profile o "SPAIN" por defecto).
        """
        self._profit = profit_analyzer or ProfitAnalyzer()
        self._profile = (
            import_cost_profile
            or getattr(settings, "default_import_cost_profile", None)
            or "SPAIN"
        )

    @staticmethod
    def _current_year() -> int:
        return datetime.now().year

    def evaluate(
        self,
        vehicle: Vehicle,
        *,
        estimated_sale_price: float | None = None,
        seller_type: str | None = None,
        market_confidence: float | None = None,
    ) -> EvaluationResult:
        """Evalúa un vehículo y calcula todos los costes y rentabilidad.

        Args:
            vehicle: Vehículo a evaluar.
            estimated_sale_price: Precio de venta real (comparables de
                mercado), si el caller ya lo calculó. TASK 2 (AUD-008): sin
                esto, ProfitAnalyzer recurre a un multiplicador fijo (×1.4)
                sin ningún respaldo de mercado — se prefiere siempre pasar
                un valor real cuando esté disponible (p. ej. desde
                ComparableMarketEstimator).
            seller_type: Tipo de vendedor real (dealer/private/...), si el
                caller lo conoce; si no, se usa ``vehicle.seller_type``.
            market_confidence: Confianza 0-100 del ``MarketEstimation`` usado
                para ``estimated_sale_price``, si está disponible.

        Returns:
            EvaluationResult con todos los cálculos.
        """
        warnings: list[str] = []

        sale_price_override = (
            estimated_sale_price
            if estimated_sale_price is not None and estimated_sale_price > 0
            else getattr(vehicle, "estimated_sale_price", None)
        )
        market_grounded = bool(sale_price_override and sale_price_override > 0)
        seller = (
            seller_type if seller_type is not None else getattr(vehicle, "seller_type", None)
        )

        # --- Bloque económico delegado en ProfitAnalyzer ---
        try:
            analysis = self._profit.analyze(
                vehicle,
                profile_name=self._profile,
                estimated_sale_price=sale_price_override,
                seller_type=seller,
            )
        except ValueError:
            # Vehículo sin precio: ProfitAnalyzer no puede analizar.
            return self._empty_result(vehicle, warnings)

        # Mapear ProfitAnalysis → EvaluationResult
        vehicle_cost = analysis.purchase_price
        transport_cost = analysis.transport_cost
        registration_cost = analysis.registration_cost
        itv_cost = analysis.inspection_cost
        gestoria_cost = analysis.cost_breakdown.miscellaneous_cost
        taxes_cost = analysis.taxes
        total_cost = analysis.total_cost
        estimated_sale_price_es = analysis.estimated_sale_price
        gross_profit = analysis.net_profit
        profit_margin_percent = analysis.roi_percentage

        if vehicle_cost == 0:
            warnings.append("no tiene precio de compra definido")
        if estimated_sale_price_es == 0:
            warnings.append("No se pudo estimar el precio de venta en España")
        elif not market_grounded:
            warnings.append(
                "precio de venta estimado sin comparables de mercado "
                "(multiplicador por defecto); confianza reducida"
            )

        # --- Score y clasificación (scoring propio del engine) ---
        score = self._calculate_score(vehicle, profit_margin_percent, warnings)
        classification = self._classify(profit_margin_percent, score)

        # --- Recomendación alineada con ProfitAnalysis ---
        recommendation = self._generate_recommendation(
            classification, profit_margin_percent, warnings, analysis.recommendation
        )

        confidence = estimate_confidence(
            market_confidence=market_confidence,
            warnings=analysis.warnings,
            weaknesses=warnings,
            market_grounded=market_grounded,
        )

        return EvaluationResult(
            vehicle_cost=vehicle_cost,
            transport_cost=transport_cost,
            registration_cost=registration_cost,
            itv_cost=itv_cost,
            gestoria_cost=gestoria_cost,
            taxes_cost=taxes_cost,
            total_cost=total_cost,
            estimated_sale_price_es=estimated_sale_price_es,
            gross_profit=gross_profit,
            profit_margin_percent=profit_margin_percent,
            score=score,
            classification=classification,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
        )

    def _empty_result(self, vehicle: Vehicle, warnings: list[str]) -> EvaluationResult:
        """Construye un EvaluationResult vacío cuando no hay precio."""
        warnings.append("no tiene precio de compra definido")
        score = self._calculate_score(vehicle, 0.0, warnings)
        classification = self._classify(0.0, score)
        recommendation = self._generate_recommendation(
            classification, 0.0, warnings, ProfitRecommendation.REJECT
        )
        confidence = estimate_confidence(
            market_confidence=None,
            warnings=[],
            weaknesses=warnings,
            market_grounded=False,
        )
        return EvaluationResult(
            vehicle_cost=0.0,
            transport_cost=0.0,
            registration_cost=0.0,
            itv_cost=0.0,
            gestoria_cost=0.0,
            taxes_cost=0.0,
            total_cost=0.0,
            estimated_sale_price_es=0.0,
            gross_profit=0.0,
            profit_margin_percent=0.0,
            score=score,
            classification=classification,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
        )

    def _calculate_score(
        self, vehicle: Vehicle, profit_margin_percent: float, warnings: list[str]
    ) -> int:
        """Calcula el score de 0 a 100.

        Args:
            vehicle: Vehículo evaluado.
            profit_margin_percent: Margen de beneficio porcentual.
            warnings: Lista de advertencias.

        Returns:
            Score de 0 a 100.
        """
        score = 50  # Base

        # Ajustar por margen de beneficio (hasta +30 puntos)
        if profit_margin_percent >= self.MIN_PROFIT_MARGIN_PERCENT:
            score += 30
        elif profit_margin_percent >= self.WARNING_PROFIT_MARGIN_PERCENT:
            score += 15
        elif profit_margin_percent > 0:
            score += 5
        else:
            score -= 20  # Margen negativo

        # Ajustar por antigüedad (hasta +10 puntos)
        if vehicle.year:
            current_year = self._current_year()
            age = current_year - vehicle.year
            if age <= 3:
                score += 10
            elif age <= 5:
                score += 5
            elif age <= 10:
                score += 0
            else:
                score -= 10  # Vehículo muy antiguo

        # Ajustar por kilometraje (hasta +10 puntos)
        if vehicle.mileage and vehicle.mileage > 0:
            if vehicle.mileage < 50000:
                score += 10
            elif vehicle.mileage < 100000:
                score += 5
            elif vehicle.mileage < 150000:
                score += 0
            else:
                score -= 10  # Kilometraje alto

        # Penalizar por advertencias
        score -= len(warnings) * 5

        # Limitar score entre 0 y 100
        score = max(0, min(100, score))

        return score

    def _classify(self, profit_margin_percent: float, score: int) -> str:
        """Clasifica la evaluación como verde, amarillo o rojo.

        Args:
            profit_margin_percent: Margen de beneficio porcentual.
            score: Score de 0 a 100.

        Returns:
            Clasificación: "verde", "amarillo" o "rojo".
        """
        # Clasificación basada en score y margen
        if score >= self.GREEN_SCORE_THRESHOLD and profit_margin_percent >= self.MIN_PROFIT_MARGIN_PERCENT:
            return "verde"
        elif score >= self.YELLOW_SCORE_THRESHOLD and profit_margin_percent >= self.WARNING_PROFIT_MARGIN_PERCENT:
            return "amarillo"
        else:
            return "rojo"

    def _generate_recommendation(
        self,
        classification: str,
        profit_margin_percent: float,
        warnings: list[str],
        profit_recommendation: ProfitRecommendation | None = None,
    ) -> str:
        """Genera una recomendación alineada con ProfitAnalysis.

        Args:
            classification: Clasificación de la evaluación.
            profit_margin_percent: Margen de beneficio porcentual.
            warnings: Lista de advertencias.
            profit_recommendation: Recomendación económica de ProfitAnalyzer.

        Returns:
            Recomendación en texto.
        """
        if profit_recommendation == ProfitRecommendation.BUY:
            recommendation = "Vehículo recomendado para importación. El margen de beneficio es adecuado."
        elif profit_recommendation == ProfitRecommendation.CONSIDER:
            recommendation = "Vehículo con margen ajustado. Considerar negociar el precio de compra."
        elif profit_recommendation == ProfitRecommendation.REJECT:
            recommendation = "Vehículo no recomendado. El margen de beneficio es insuficiente o negativo."
        else:
            # Fallback al comportamiento basado en clasificación
            if classification == "verde":
                recommendation = "Vehículo recomendado para importación. El margen de beneficio es adecuado."
            elif classification == "amarillo":
                recommendation = "Vehículo con margen ajustado. Considerar negociar el precio de compra."
            else:
                recommendation = "Vehículo no recomendado. El margen de beneficio es insuficiente o negativo."

        if warnings:
            recommendation += f" Advertencias: {', '.join(warnings)}"

        return recommendation