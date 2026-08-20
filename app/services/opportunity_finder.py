"""OpportunityFinder — Motor de detección de oportunidades de importación.

Consume los resultados de VehicleScorer, ProfitAnalyzer y MarketEstimation
para producir un análisis consolidado que determina si un vehículo
es una oportunidad real de importación.

NO recalcula scoring, beneficios ni estimaciones de mercado.
Se limita a combinar los resultados de los servicios existentes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.config.opportunity import (
    AVERAGE_THRESHOLD,
    BUY_NOW_MIN_CONFIDENCE,
    BUY_NOW_MIN_ROI,
    BUY_NOW_MIN_SCORE,
    EXCELLENT_THRESHOLD,
    GOOD_ROI_THRESHOLD,
    GOOD_THRESHOLD,
    HIGH_CONFIDENCE_EXPLANATION_THRESHOLD,
    HIGH_DEMAND_THRESHOLD,
    HIGH_RISK_PENALTY,
    HIGH_ROI_BONUS,
    LOW_CONFIDENCE_EXPLANATION_THRESHOLD,
    LOW_CONFIDENCE_PENALTY,
    LOW_MARGIN_PENALTY,
    LOW_PRICE_BONUS,
    MARKET_CONFIDENCE_WEIGHT,
    NEGATIVE_PROFIT_PENALTY,
    NEGOTIATE_MAX_SCORE,
    NEGOTIATE_MIN_SCORE,
    POOR_THRESHOLD,
    PRICE_COMPETITIVE_THRESHOLD,
    PROFIT_NET_PROFIT_HIGH_THRESHOLD,
    PROFIT_NET_PROFIT_LOW_THRESHOLD,
    PROFIT_ROI_HIGH_THRESHOLD,
    PROFIT_ROI_LOW_THRESHOLD,
    PROFIT_WEIGHT,
    SATURATED_SUPPLY_THRESHOLD,
    VEHICLE_SCORE_WEIGHT,
    WATCH_MAX_SCORE,
    WATCH_MIN_SCORE,
)

# =============================================================================
# Enumeraciones de salida
# =============================================================================


class OpportunityLevel(str, Enum):
    """Nivel de oportunidad global del vehículo para importación."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    AVERAGE = "AVERAGE"
    POOR = "POOR"
    REJECT = "REJECT"


class Recommendation(str, Enum):
    """Recomendación de acción basada en el análisis completo de oportunidad."""

    BUY_NOW = "BUY_NOW"
    WATCH = "WATCH"
    NEGOTIATE = "NEGOTIATE"
    REJECT = "REJECT"


# =============================================================================
# Modelos de salida
# =============================================================================


@dataclass
class OpportunityReason:
    """Razón individual que contribuye al análisis de oportunidad.

    Attributes:
        reason: Descripción legible de la razón.
        impact: Impacto numérico en el overall_score (puntos).
        is_positive: True si es una fortaleza, False si es debilidad.
        category: Categoría de la razón (score, profit, market).
    """

    reason: str
    impact: float
    is_positive: bool
    category: str


@dataclass
class OpportunityAnalysis:
    """Análisis completo de oportunidad de importación.

    Attributes:
        overall_score: Puntuación combinada final (0-100).
        opportunity_level: Nivel de oportunidad.
        recommendation: Recomendación de acción.
        estimated_profit: Beneficio neto estimado (del ProfitAnalysis).
        roi: Retorno sobre la inversión (del ProfitAnalysis).
        market_confidence: Confianza de mercado (del MarketEstimation).
        risk_level: Nivel de riesgo (del ProfitAnalysis).
        strengths: Lista de fortalezas detectadas (texto legible).
        weaknesses: Lista de debilidades detectadas (texto legible).
        reasons: Lista completa de razones que contribuyeron al análisis.
    """

    overall_score: float
    opportunity_level: OpportunityLevel
    recommendation: Recommendation
    estimated_profit: float
    roi: float
    market_confidence: float
    risk_level: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    reasons: list[OpportunityReason] = field(default_factory=list)


# =============================================================================
# OpportunityFinder
# =============================================================================


class OpportunityFinder:
    """Detector de oportunidades de importación.

    Consume los resultados de VehicleScorer, ProfitAnalyzer y MarketEstimation
    para producir un análisis consolidado.

    Uso:
        finder = OpportunityFinder()
        analysis = finder.analyze(vehicle_score, profit_analysis, market_estimation)
        logger.debug("opportunity result: %s", analysis.recommendation)
    """

    def __init__(self) -> None:
        """Inicializa el detector de oportunidades."""
        pass

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def analyze(
        self,
        vehicle_score: Any,
        profit_analysis: Any,
        market_estimation: Any,
    ) -> OpportunityAnalysis:
        """Analiza un vehículo combinando score, beneficio y mercado.

        Args:
            vehicle_score: Resultado de VehicleScorer (debe tener .score, .strengths, .weaknesses).
            profit_analysis: Resultado de ProfitAnalyzer (debe tener .net_profit, .roi_percentage,
                .risk_level, .recommendation).
            market_estimation: MarketEstimation (debe tener .market_price, .confidence,
                .supply_level, .demand_level, .market_trend).

        Returns:
            OpportunityAnalysis con el análisis completo.
        """
        reasons: list[OpportunityReason] = []

        # --- Normalizar cada componente a score 0-100 ---
        normalized_vehicle_score = self._normalize_vehicle_score(vehicle_score)
        normalized_profit_score = self._normalize_profit_analysis(profit_analysis)
        normalized_market_score = self._normalize_market_estimation(market_estimation)

        # Añadir razones de cada normalización
        reasons.extend(self._get_vehicle_score_reasons(vehicle_score))
        reasons.extend(self._get_profit_reasons(profit_analysis))
        reasons.extend(self._get_market_reasons(market_estimation))

        # --- Calcular overall score ponderado ---
        overall_score = (
            normalized_vehicle_score * VEHICLE_SCORE_WEIGHT
            + normalized_profit_score * PROFIT_WEIGHT
            + normalized_market_score * MARKET_CONFIDENCE_WEIGHT
        )

        # Aplicar bonificaciones y penalizaciones
        bonus_penalty = self._calculate_bonus_penalty(
            vehicle_score, profit_analysis, market_estimation
        )
        overall_score = max(0.0, min(100.0, overall_score + bonus_penalty))

        # --- Generar fortalezas y debilidades ---
        strengths = [
            r.reason for r in reasons if r.is_positive
        ]
        weaknesses = [
            r.reason for r in reasons if not r.is_positive
        ]

        # --- Determinar opportunity level ---
        opportunity_level = self._get_opportunity_level(overall_score)

        # --- Determinar recomendación ---
        recommendation = self._get_recommendation(
            overall_score=overall_score,
            profit_analysis=profit_analysis,
            market_estimation=market_estimation,
            opportunity_level=opportunity_level,
        )

        # Extraer valores clave
        estimated_profit = getattr(profit_analysis, "net_profit", 0.0)
        roi = getattr(profit_analysis, "roi_percentage", 0.0)
        market_confidence = getattr(market_estimation, "confidence", 0.0)
        risk_level = getattr(profit_analysis, "risk_level", "UNKNOWN")
        if hasattr(risk_level, "value"):
            risk_level = risk_level.value

        return OpportunityAnalysis(
            overall_score=round(overall_score, 2),
            opportunity_level=opportunity_level,
            recommendation=recommendation,
            estimated_profit=estimated_profit,
            roi=roi,
            market_confidence=market_confidence,
            risk_level=risk_level,
            strengths=strengths,
            weaknesses=weaknesses,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Normalización de componentes
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_vehicle_score(vehicle_score: Any) -> float:
        """Normaliza el VehicleScore (0-100) a un valor 0-100.

        VehicleScore ya viene en escala 0-100, pero aplicamos
        una suave curva para que puntuaciones medias-altas tengan
        más impacto.
        """
        raw_score = getattr(vehicle_score, "score", 0.0)
        if raw_score is None:
            return 0.0
        # Escala lineal: el score ya está en 0-100
        return max(0.0, min(100.0, float(raw_score)))

    @staticmethod
    def _normalize_profit_analysis(profit_analysis: Any) -> float:
        """Normaliza el ProfitAnalysis a un valor 0-100.

        Combina ROI, beneficio neto y nivel de riesgo en un
        único score de 0-100.
        """
        roi = getattr(profit_analysis, "roi_percentage", 0.0) or 0.0
        net_profit = getattr(profit_analysis, "net_profit", 0.0) or 0.0
        risk_level = getattr(profit_analysis, "risk_level", None)

        # Score basado en ROI (0-100)
        if roi >= PROFIT_ROI_HIGH_THRESHOLD:
            roi_score = 100.0
        elif roi <= PROFIT_ROI_LOW_THRESHOLD:
            roi_score = 0.0
        else:
            roi_score = (roi / PROFIT_ROI_HIGH_THRESHOLD) * 100.0

        # Score basado en beneficio neto (0-100)
        if net_profit >= PROFIT_NET_PROFIT_HIGH_THRESHOLD:
            profit_score = 100.0
        elif net_profit <= PROFIT_NET_PROFIT_LOW_THRESHOLD:
            profit_score = 0.0
        else:
            profit_score = (net_profit / PROFIT_NET_PROFIT_HIGH_THRESHOLD) * 100.0

        # Penalización por riesgo
        risk_penalty = 0.0
        if risk_level is not None:
            risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
            if risk_str == "HIGH":
                risk_penalty = 30.0
            elif risk_str == "MEDIUM":
                risk_penalty = 10.0

        # Combinar: 60% ROI + 40% beneficio - penalización riesgo
        combined = (roi_score * 0.60 + profit_score * 0.40) - risk_penalty
        return max(0.0, min(100.0, combined))

    @staticmethod
    def _normalize_market_estimation(market_estimation: Any) -> float:
        """Normaliza la estimación de mercado a un valor 0-100.

        Usa la confianza directamente y ajusta por oferta/demanda.
        """
        confidence = getattr(market_estimation, "confidence", 50.0) or 50.0
        supply = getattr(market_estimation, "supply_level", 50.0) or 50.0
        demand = getattr(market_estimation, "demand_level", 50.0) or 50.0

        # Confianza base (0-100)
        confidence_score = max(0.0, min(100.0, float(confidence)))

        # Ajuste por oferta/demanda: mercado con más demanda que oferta es mejor
        supply_demand_balance = demand - supply  # Puede ser negativo
        balance_adjustment = max(-20.0, min(20.0, supply_demand_balance * 0.5))

        score = confidence_score + balance_adjustment
        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Bonificaciones y penalizaciones
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_bonus_penalty(
        vehicle_score: Any,
        profit_analysis: Any,
        market_estimation: Any,
    ) -> float:
        """Calcula bonificaciones y penalizaciones adicionales.

        Returns:
            Ajuste neto al overall_score (puede ser positivo o negativo).
        """
        adjustment = 0.0

        # --- Bonificaciones ---
        # Precio muy competitivo
        price = getattr(profit_analysis, "purchase_price", None)
        if price is not None and 0 < price < PRICE_COMPETITIVE_THRESHOLD:
            adjustment += LOW_PRICE_BONUS

        # ROI alto
        roi = getattr(profit_analysis, "roi_percentage", 0.0) or 0.0
        if roi >= PROFIT_ROI_HIGH_THRESHOLD:
            adjustment += HIGH_ROI_BONUS

        # --- Penalizaciones ---
        # Confianza baja
        confidence = getattr(market_estimation, "confidence", 50.0) or 50.0
        if confidence < 40.0:
            adjustment -= LOW_CONFIDENCE_PENALTY

        # Margen bajo (ROI < 5%)
        if 0 < roi < 5.0:
            adjustment -= LOW_MARGIN_PENALTY

        # Beneficio negativo
        net_profit = getattr(profit_analysis, "net_profit", 0.0) or 0.0
        if net_profit < 0:
            adjustment -= NEGATIVE_PROFIT_PENALTY

        # Riesgo alto
        risk_level = getattr(profit_analysis, "risk_level", None)
        if risk_level is not None:
            risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
            if risk_str == "HIGH":
                adjustment -= HIGH_RISK_PENALTY

        return adjustment

    # ------------------------------------------------------------------
    # Generación de razones explicativas
    # ------------------------------------------------------------------

    @staticmethod
    def _get_vehicle_score_reasons(vehicle_score: Any) -> list[OpportunityReason]:
        """Genera razones basadas en el VehicleScore."""
        reasons: list[OpportunityReason] = []
        score = getattr(vehicle_score, "score", 0)
        strengths = getattr(vehicle_score, "strengths", []) or []
        weaknesses = getattr(vehicle_score, "weaknesses", []) or []

        if score is not None and score >= 80:
            reasons.append(OpportunityReason(
                reason=f"Puntuación del vehículo excelente: {score}/100",
                impact=5.0,
                is_positive=True,
                category="score",
            ))
        elif score is not None and score >= 60:
            reasons.append(OpportunityReason(
                reason=f"Puntuación del vehículo buena: {score}/100",
                impact=2.0,
                is_positive=True,
                category="score",
            ))

        # Convertir fortalezas del scorer
        for s in strengths[:3]:  # Top 3 fortalezas
            reasons.append(OpportunityReason(
                reason=s,
                impact=2.0,
                is_positive=True,
                category="score",
            ))

        # Convertir debilidades del scorer
        for w in weaknesses[:3]:  # Top 3 debilidades
            reasons.append(OpportunityReason(
                reason=w,
                impact=-2.0,
                is_positive=False,
                category="score",
            ))

        return reasons

    @staticmethod
    def _get_profit_reasons(profit_analysis: Any) -> list[OpportunityReason]:
        """Genera razones basadas en el ProfitAnalysis."""
        reasons: list[OpportunityReason] = []
        roi = getattr(profit_analysis, "roi_percentage", 0.0) or 0.0
        net_profit = getattr(profit_analysis, "net_profit", 0.0) or 0.0
        risk_level = getattr(profit_analysis, "risk_level", None)
        purchase_price = getattr(profit_analysis, "purchase_price", 0.0) or 0.0

        # ROI
        if roi >= GOOD_ROI_THRESHOLD:
            reasons.append(OpportunityReason(
                reason=f"Excelente ROI: {roi:.1f}%",
                impact=5.0,
                is_positive=True,
                category="profit",
            ))
        elif roi > 0:
            reasons.append(OpportunityReason(
                reason=f"ROI aceptable: {roi:.1f}%",
                impact=1.0,
                is_positive=True,
                category="profit",
            ))
        else:
            reasons.append(OpportunityReason(
                reason=f"ROI bajo o negativo: {roi:.1f}%",
                impact=-5.0,
                is_positive=False,
                category="profit",
            ))

        # Beneficio neto
        if net_profit > 0:
            reasons.append(OpportunityReason(
                reason=f"Beneficio neto estimado: {net_profit:.2f} EUR",
                impact=3.0,
                is_positive=True,
                category="profit",
            ))
        else:
            reasons.append(OpportunityReason(
                reason="Beneficio neto negativo o nulo",
                impact=-10.0,
                is_positive=False,
                category="profit",
            ))

        # Riesgo
        if risk_level is not None:
            risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
            if risk_str == "LOW":
                reasons.append(OpportunityReason(
                    reason="Riesgo bajo de la operación",
                    impact=3.0,
                    is_positive=True,
                    category="profit",
                ))
            elif risk_str == "HIGH":
                reasons.append(OpportunityReason(
                    reason="Riesgo alto de la operación",
                    impact=-5.0,
                    is_positive=False,
                    category="profit",
                ))

        # Precio
        if purchase_price > 0 and purchase_price < PRICE_COMPETITIVE_THRESHOLD:
            reasons.append(OpportunityReason(
                reason=f"Precio muy competitivo: {purchase_price:.0f} EUR",
                impact=4.0,
                is_positive=True,
                category="profit",
            ))

        return reasons

    @staticmethod
    def _get_market_reasons(market_estimation: Any) -> list[OpportunityReason]:
        """Genera razones basadas en la estimación de mercado."""
        reasons: list[OpportunityReason] = []
        confidence = getattr(market_estimation, "confidence", 50.0) or 50.0
        supply = getattr(market_estimation, "supply_level", 50.0) or 50.0
        demand = getattr(market_estimation, "demand_level", 50.0) or 50.0
        trend = getattr(market_estimation, "market_trend", "stable") or "stable"
        market_price = getattr(market_estimation, "market_price", 0.0) or 0.0

        # Confianza
        if confidence >= HIGH_CONFIDENCE_EXPLANATION_THRESHOLD:
            reasons.append(OpportunityReason(
                reason=f"Confianza de mercado alta: {confidence:.0f}%",
                impact=4.0,
                is_positive=True,
                category="market",
            ))
        elif confidence <= LOW_CONFIDENCE_EXPLANATION_THRESHOLD:
            reasons.append(OpportunityReason(
                reason=f"Confianza de mercado baja: {confidence:.0f}%",
                impact=-4.0,
                is_positive=False,
                category="market",
            ))
        else:
            reasons.append(OpportunityReason(
                reason=f"Confianza de mercado media: {confidence:.0f}%",
                impact=0.0,
                is_positive=True,
                category="market",
            ))

        # Oferta / Demanda
        if supply >= SATURATED_SUPPLY_THRESHOLD:
            reasons.append(OpportunityReason(
                reason="Mercado saturado (alta oferta)",
                impact=-3.0,
                is_positive=False,
                category="market",
            ))
        if demand >= HIGH_DEMAND_THRESHOLD:
            reasons.append(OpportunityReason(
                reason="Mercado favorable (alta demanda)",
                impact=3.0,
                is_positive=True,
                category="market",
            ))

        # Tendencia
        if trend == "rising":
            reasons.append(OpportunityReason(
                reason="Tendencia de mercado al alza",
                impact=2.0,
                is_positive=True,
                category="market",
            ))
        elif trend == "falling":
            reasons.append(OpportunityReason(
                reason="Tendencia de mercado a la baja",
                impact=-2.0,
                is_positive=False,
                category="market",
            ))

        # Precio de mercado
        if market_price > 0:
            reasons.append(OpportunityReason(
                reason=f"Precio de mercado estimado: {market_price:.0f} EUR",
                impact=1.0,
                is_positive=True,
                category="market",
            ))

        return reasons

    # ------------------------------------------------------------------
    # Clasificación
    # ------------------------------------------------------------------

    @staticmethod
    def _get_opportunity_level(overall_score: float) -> OpportunityLevel:
        """Determina el nivel de oportunidad basado en el overall_score."""
        if overall_score >= EXCELLENT_THRESHOLD:
            return OpportunityLevel.EXCELLENT
        if overall_score >= GOOD_THRESHOLD:
            return OpportunityLevel.GOOD
        if overall_score >= AVERAGE_THRESHOLD:
            return OpportunityLevel.AVERAGE
        if overall_score >= POOR_THRESHOLD:
            return OpportunityLevel.POOR
        return OpportunityLevel.REJECT

    @staticmethod
    def _get_recommendation(
        overall_score: float,
        profit_analysis: Any,
        market_estimation: Any,
        opportunity_level: OpportunityLevel,
    ) -> Recommendation:
        """Determina la recomendación basada en todos los factores.

        Reglas:
        - BUY_NOW: score >= 80, ROI >= 15%, confianza >= 70%
        - WATCH: score entre 55-79, o buen score pero confianza media
        - NEGOTIATE: score entre 40-69, o buen vehículo pero margen bajo
        - REJECT: score < 40, o beneficio negativo, o riesgo alto
        """
        roi = getattr(profit_analysis, "roi_percentage", 0.0) or 0.0
        net_profit = getattr(profit_analysis, "net_profit", 0.0) or 0.0
        risk_level = getattr(profit_analysis, "risk_level", None)
        confidence = getattr(market_estimation, "confidence", 50.0) or 50.0

        # REJECT: beneficio negativo o nivel POOR/REJECT
        if net_profit <= 0:
            return Recommendation.REJECT

        if opportunity_level in (OpportunityLevel.POOR, OpportunityLevel.REJECT):
            return Recommendation.REJECT

        if risk_level is not None:
            risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
            if risk_str == "HIGH":
                return Recommendation.REJECT

        # BUY_NOW: todo en verde
        if (
            overall_score >= BUY_NOW_MIN_SCORE
            and roi >= BUY_NOW_MIN_ROI
            and confidence >= BUY_NOW_MIN_CONFIDENCE
        ):
            return Recommendation.BUY_NOW

        # NEGOTIATE: buen vehículo pero margen bajo (score decente pero ROI bajo)
        if (
            NEGOTIATE_MIN_SCORE <= overall_score <= NEGOTIATE_MAX_SCORE
            and roi < BUY_NOW_MIN_ROI
        ):
            return Recommendation.NEGOTIATE

        # WATCH: casos intermedios viables
        if WATCH_MIN_SCORE <= overall_score <= WATCH_MAX_SCORE:
            return Recommendation.WATCH

        # Fallback
        if overall_score >= BUY_NOW_MIN_SCORE:
            # Buen score pero no cumple todos los requisitos de BUY_NOW
            if roi >= BUY_NOW_MIN_ROI:
                return Recommendation.BUY_NOW
            return Recommendation.WATCH

        return Recommendation.REJECT

