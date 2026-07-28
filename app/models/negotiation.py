"""Modelos de datos para el motor de negociación (NegotiationEngine).

Define los DTOs de entrada (InspectionResult, RepairEstimate, NegotiationInput)
y de salida (NegotiationResult, NegotiationArgument, NegotiationScript).

Estos DTOs son independientes del motor de negociación y pueden ser
consumidos tanto por el SearchOrchestrator como por futuros endpoints.
No replican modelos existentes; reutilizan `MarketEstimation` y `ProfitAnalysis`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# =============================================================================
# Enumeraciones de salida
# =============================================================================


class NegotiationRecommendation(str, Enum):
    """Recomendación final de la estrategia de negociación.

    SOLO puede devolver uno de estos tres valores.
    """

    BUY = "BUY"
    """Comprar directamente sin negociar (precio ya es bueno)."""
    NEGOTIATE = "NEGOTIATE"
    """Negociar activamente para conseguir mejor precio."""
    WALK_AWAY = "WALK_AWAY"
    """Abandonar la operación (no hay margen para acuerdo)."""


# =============================================================================
# Modelos de entrada
# =============================================================================


@dataclass(frozen=True)
class DefectItem:
    """Defecto o reparación necesaria detectada en la inspección.

    Cada defecto se convierte en un argumento de negociación.

    Attributes:
        category: Categoría del defecto (mecánico, estético, eléctrico, etc.).
        description: Descripción legible del defecto.
        severity: Severidad estimada (1-10, mayor = más grave).
        estimated_repair_cost: Coste estimado de reparación en EUR.
        is_safety_relevant: True si afecta a la seguridad del vehículo.
        can_be_used_as_leverage: True si es argumento válido para negociar.
    """

    category: str
    description: str
    severity: int = 5
    estimated_repair_cost: float = 0.0
    is_safety_relevant: bool = False
    can_be_used_as_leverage: bool = True


@dataclass(frozen=True)
class InspectionResult:
    """Resultado de una inspección técnica de un vehículo.

    Representa los defectos y condiciones detectados durante la inspección.
    Se utiliza como entrada para generar argumentos de negociación y el script.

    Attributes:
        defects: Lista de defectos detectados.
        overall_condition: Valoración general (1-10, mayor = mejor estado).
        has_accident_history: True si el vehículo tiene historial de accidentes.
        accident_notes: Notas adicionales sobre accidentes.
        inspection_notes: Notas generales de la inspección.
    """

    defects: list[DefectItem] = field(default_factory=list)
    overall_condition: int = 10
    has_accident_history: bool = False
    accident_notes: str = ""
    inspection_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepairEstimate:
    """Estimación detallada de costes de reparación.

    Se utiliza como entrada para calcular el descuento necesario en negociación.

    Attributes:
        total_repair_cost: Coste total estimado de todas las reparaciones (EUR).
        parts_cost: Coste estimado de piezas (EUR).
        labor_cost: Coste estimado de mano de obra (EUR).
        paint_and_body_cost: Coste estimado de pintura y carrocería (EUR).
        diagnostic_cost: Coste estimado de diagnóstico (EUR).
        notes: Notas adicionales sobre la estimación.
    """

    total_repair_cost: float = 0.0
    parts_cost: float = 0.0
    labor_cost: float = 0.0
    paint_and_body_cost: float = 0.0
    diagnostic_cost: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class NegotiationInput:
    """Entrada completa para el motor de negociación.

    Agrupa toda la información que NegotiationEngine necesita.

    Attributes:
        inspection_result: Resultado de la inspección técnica.
        repair_estimate: Estimación de costes de reparación.
        market_estimation: Estimación de mercado (MarketEstimation).
        asking_price: Precio de venta solicitado por el vendedor (EUR).
        minimum_desired_profit: Beneficio mínimo deseado (EUR).
        target_margin: Margen objetivo sobre el coste total (0-100%).
        profit_analysis_data: Dict con datos de ProfitAnalysis (net_profit, roi, risk).
        vehicle_score_data: Dict con datos de VehicleScore (score, strengths, weaknesses).
    """

    inspection_result: InspectionResult
    repair_estimate: RepairEstimate
    market_estimation: Any  # MarketEstimation
    asking_price: float = 0.0
    minimum_desired_profit: float = 0.0
    target_margin: float = 15.0
    profit_analysis_data: dict[str, Any] = field(default_factory=dict)
    vehicle_score_data: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Modelos de salida
# =============================================================================


@dataclass(frozen=True)
class NegotiationArgument:
    """Argumento de negociación ordenado por impacto económico.

    Attributes:
        argument: Texto del argumento listo para usar en una negociación.
        economic_impact: Impacto económico estimado del argumento (EUR).
        category: Categoría del argumento (defect, market, profit, vehicle).
        severity: Severidad o importancia del argumento (1-10).
    """

    argument: str
    economic_impact: float
    category: str = "defect"
    severity: int = 5


@dataclass(frozen=True)
class NegotiationScript:
    """Script de negociación en lenguaje natural.

    Generado automáticamente a partir de los defectos detectados
    para ayudar al comprador en la negociación cara a cara.

    Attributes:
        opening: Frase de apertura para iniciar la negociación.
        defect_based_points: Puntos de conversación basados en defectos.
        market_based_points: Puntos basados en condiciones de mercado.
        closing: Frase de cierre con la oferta firme.
    """

    opening: str = ""
    defect_based_points: list[str] = field(default_factory=list)
    market_based_points: list[str] = field(default_factory=list)
    closing: str = ""


@dataclass(frozen=True)
class NegotiationResult:
    """Resultado completo del motor de negociación.

    Este es el único objeto de retorno de NegotiationEngine.analyze().

    Attributes:
        estimated_vehicle_value: Valor real estimado del vehículo en EUR.
        recommended_initial_offer: Primera oferta recomendada (EUR).
        recommended_counter_offer: Contraoferta recomendada si el vendedor rechaza (EUR).
        maximum_purchase_price: Precio máximo que se puede pagar (EUR).
        walk_away_price: Precio a partir del cual abandonar la negociación (EUR).
        expected_profit: Beneficio esperado si se cierra al precio recomendado (EUR).
        expected_roi: ROI esperado si se cierra al precio recomendado (%).
        negotiation_arguments: Argumentos ordenados por impacto económico descendente.
        negotiation_script: Script de negociación en lenguaje natural.
        recommendation: Recomendación final (BUY, NEGOTIATE, WALK_AWAY).
        leverage_score: Puntuación de apalancamiento del comprador (0-100).
        price_gap: Diferencia entre asking_price y estimated_vehicle_value (EUR).
        discount_needed: Descuento necesario sobre asking_price para ser rentable (%).
    """

    estimated_vehicle_value: float
    recommended_initial_offer: float
    recommended_counter_offer: float
    maximum_purchase_price: float
    walk_away_price: float
    expected_profit: float
    expected_roi: float
    negotiation_arguments: list[NegotiationArgument] = field(default_factory=list)
    negotiation_script: NegotiationScript = field(default_factory=NegotiationScript)
    recommendation: NegotiationRecommendation = NegotiationRecommendation.WALK_AWAY
    leverage_score: float = 50.0
    price_gap: float = 0.0
    discount_needed: float = 0.0