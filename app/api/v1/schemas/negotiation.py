"""Negotiation API schemas.

NegotiationResult schema exposed through the API.
These are stable API-facing DTOs, decoupled from internal dataclasses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NegotiationArgumentSchema(BaseModel):
    """Argumento de negociación ordenado por impacto económico."""

    argument: str = Field(..., description="Texto del argumento")
    economic_impact: float = Field(..., description="Impacto económico estimado (EUR)")
    category: str = Field("defect", description="Categoría del argumento")
    severity: int = Field(5, description="Severidad 1-10", ge=1, le=10)


class NegotiationScriptSchema(BaseModel):
    """Script de negociación en lenguaje natural."""

    opening: str = Field("", description="Frase de apertura")
    defect_based_points: list[str] = Field(default_factory=list, description="Puntos basados en defectos")
    market_based_points: list[str] = Field(default_factory=list, description="Puntos basados en mercado")
    closing: str = Field("", description="Frase de cierre")


class NegotiationResultSchema(BaseModel):
    """Resultado completo del motor de negociación."""

    estimated_vehicle_value: float = Field(..., description="Valor real estimado (EUR)")
    recommended_initial_offer: float = Field(..., description="Primera oferta recomendada (EUR)")
    recommended_counter_offer: float = Field(..., description="Contraoferta recomendada (EUR)")
    maximum_purchase_price: float = Field(..., description="Precio máximo a pagar (EUR)")
    walk_away_price: float = Field(..., description="Precio de abandono (EUR)")
    expected_profit: float = Field(..., description="Beneficio esperado (EUR)")
    expected_roi: float = Field(..., description="ROI esperado (%)")
    negotiation_arguments: list[NegotiationArgumentSchema] = Field(default_factory=list)
    negotiation_script: NegotiationScriptSchema = Field(default_factory=NegotiationScriptSchema)
    recommendation: str = Field(..., description="Recomendación (BUY, NEGOTIATE, WALK_AWAY)")
    leverage_score: float = Field(50.0, description="Apalancamiento 0-100")
    price_gap: float = Field(0.0, description="Diferencia precio solicitado vs valor (EUR)")
    discount_needed: float = Field(0.0, description="Descuento necesario (%)")