"""ProfitAnalyzer — Analizador económico de importación de vehículos.

Completamente independiente del scraping y del scoring.
Recibe un Vehicle (o cualquier objeto que implemente VehicleData)
y devuelve un análisis económico completo de una posible importación.

Dependencias:
    - VehicleData (Protocol) para los datos del vehículo.
    - app/config/import_costs.py para toda la configuración económica.

No depende de:
    - Proveedores de scraping.
    - Sistemas de puntuación (scoring).
    - Internet.
    - Bases de datos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Final, Protocol

# =============================================================================
# Enumeraciones de salida
# =============================================================================


class Recommendation(str, Enum):
    """Recomendación de compra basada en el análisis económico.

    Únicamente puede devolver uno de estos tres valores.
    """

    BUY = "BUY"
    CONSIDER = "CONSIDER"
    REJECT = "REJECT"


class RiskLevel(str, Enum):
    """Nivel de riesgo de la operación de importación."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =============================================================================
# Modelos de salida
# =============================================================================


@dataclass
class CostBreakdown:
    """Desglose detallado de todos los costes calculados.

    Cada campo representa un componente de coste individual.
    Todos los valores están en EUR.
    """

    purchase_price: float
    """Precio de compra del vehículo en origen."""

    transport_cost: float
    """Coste de transporte desde el país de origen."""

    registration_cost: float
    """Coste de matriculación en el país de destino."""

    taxes: float
    """Impuestos aplicables."""

    inspection_cost: float
    """Coste de ITV / inspección técnica."""

    repair_estimate: float
    """Estimación de costes de reparación."""

    commission_cost: float
    """Comisión del intermediario."""

    miscellaneous_cost: float
    """Otros costes no categorizados."""

    total_fixed_costs: float = 0.0
    """Suma de todos los costes fijos (transporte, matriculación, ITV, etc.)."""

    total_variable_costs: float = 0.0
    """Suma de todos los costes variables (impuestos, comisión, reparación)."""

    total_cost: float = 0.0
    """Coste total de la importación (purchase_price + fixed + variable)."""

    iedmt_amount: float = 0.0
    """Impuesto especial IEDMT basado en emisiones CO₂ (g/km). Solo España."""

    co2_gkm: float | None = None
    """Emisiones CO₂ parseadas del vehículo (None si no disponibles)."""

    # ------------------------------------------------------------------
    # Explicación por componente (labels legibles, domain en español)
    # ------------------------------------------------------------------
    # (key dentro del dataclass, label mostrable, agrupación fixed/variable)
    # MED.001: kind siempre en inglés ("fixed"/"variable") para que el API
    # y el frontend no dependan del idioma del backend.
    _COMPONENTS: ClassVar[tuple[tuple[str, str, str], ...]] = (
        ("purchase_price", "Precio de compra", "fixed"),
        ("transport_cost", "Transporte", "fixed"),
        ("registration_cost", "Matriculación", "fixed"),
        ("inspection_cost", "ITV / inspección", "fixed"),
        ("miscellaneous_cost", "Gestoría + otros", "fixed"),
        ("taxes", "Impuestos (sobre compra)", "variable"),
        ("commission_cost", "Comisión", "variable"),
        ("repair_estimate", "Reparaciones estimadas", "variable"),
    )

    def components(self) -> list[dict[str, Any]]:
        """Devuelve cada componente con clave, label legible, agrupación y
        amount (EUR). Cada elemento es dict con ``key``, ``label``, ``kind``
        (``fixed``/``variable``) y ``amount``. Útil para exponer el
        breakdown en APIs/front sin duplicar nombres técnicos.
        """
        return [
            {
                "key": key,
                "label": label,
                "kind": kind,
                "amount": float(getattr(self, key)),
            }
            for key, label, kind in self._COMPONENTS
        ]

    def as_dict(self) -> dict[str, Any]:
        """Serialización plana del breakdown (claves = nombres de campo)."""
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass
class ProfitAnalysis:
    """Análisis económico completo de una posible importación.

    Attributes:
        purchase_price: Precio de compra del vehículo.
        transport_cost: Coste de transporte.
        registration_cost: Coste de matriculación.
        taxes: Impuestos.
        inspection_cost: Coste de ITV.
        repair_estimate: Estimación de reparaciones.
        commission_cost: Comisión.
        miscellaneous_cost: Otros costes.
        total_cost: Coste total (suma de todos los anteriores).
        estimated_sale_price: Precio de venta estimado en destino.
        gross_profit: Diferencia entre estimated_sale_price y purchase_price.
        net_profit: Diferencia entre estimated_sale_price y total_cost.
        roi_percentage: Retorno sobre la inversión (net_profit / total_cost * 100).
        profit_margin_percentage: Margen de beneficio (net_profit / estimated_sale_price * 100).
        risk_level: Nivel de riesgo de la operación.
        recommendation: Recomendación final de compra.
        cost_breakdown: Desglose detallado de todos los costes.
    """

    purchase_price: float
    transport_cost: float
    registration_cost: float
    taxes: float
    inspection_cost: float
    repair_estimate: float
    commission_cost: float
    miscellaneous_cost: float
    total_cost: float
    estimated_sale_price: float
    gross_profit: float
    net_profit: float
    roi_percentage: float
    profit_margin_percentage: float
    risk_level: RiskLevel
    recommendation: Recommendation
    cost_breakdown: CostBreakdown = field(repr=False)
    warnings: list[str] = field(default_factory=list, repr=False)


# =============================================================================
# Protocolo de entrada
# =============================================================================


class VehicleData(Protocol):
    """Protocolo que define los atributos mínimos que debe exponer
    un objeto para ser analizado por ProfitAnalyzer.

    Compatible con el modelo Vehicle SQLAlchemy y los DTOs del proyecto.
    """

    @property
    def price(self) -> float | None: ...
    @property
    def brand(self) -> str | None: ...
    @property
    def model(self) -> str | None: ...
    @property
    def year(self) -> int | None: ...
    @property
    def mileage(self) -> int | None: ...
    @property
    def emissions(self) -> str | None: ...


# =============================================================================
# ProfitAnalyzer
# =============================================================================


class ProfitAnalyzer:
    """Analizador económico de importación de vehículos.

    Recibe un vehículo y un perfil de costes, y devuelve un análisis
    económico completo incluyendo costes, beneficio, ROI, riesgo y recomendación.

    Uso:
        analyzer = ProfitAnalyzer()
        result = analyzer.analyze(vehicle)
        print(result.recommendation, result.roi_percentage)

    Para usar un perfil específico:
        result = analyzer.analyze(vehicle, profile_name="GERMANY")
    """

    def __init__(self) -> None:
        from app.config.import_costs import (
            ADDITIONAL_COSTS_CATEGORIES,
            get_profile,
        )

        self._get_profile = get_profile
        self._additional_categories = ADDITIONAL_COSTS_CATEGORIES

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def analyze(
        self,
        vehicle: VehicleData,
        profile_name: str = "DEFAULT",
        *,
        estimated_sale_price: float | None = None,
        sale_price_multiplier: float = 1.4,
        **extra_costs: float,
    ) -> ProfitAnalysis:
        """Realiza el análisis económico completo de importación.

        Args:
            vehicle: Objeto que implementa VehicleData.
            profile_name: Nombre del perfil de costes a utilizar.
            estimated_sale_price: Precio de venta estimado (si se proporciona,
                se usa directamente; si no, se calcula como purchase_price * multiplier).
            sale_price_multiplier: Multiplicador para estimar precio de venta
                cuando no se proporciona estimated_sale_price.
            **extra_costs: Costes adicionales opcionales (insurance, customs, etc.).

        Returns:
            ProfitAnalysis con el análisis completo.

        Raises:
            ValueError: Si el vehículo no tiene precio.
            KeyError: Si el perfil especificado no existe.
        """
        profile = self._get_profile(profile_name)

        # Validar precio
        purchase_price = vehicle.price
        if purchase_price is None or purchase_price <= 0:
            raise ValueError(
                "El vehículo debe tener un precio válido para realizar el análisis."
            )

        # --- Calcular costes ---
        from app.services.iedmt import parse_co2_gkm

        co2_gkm = parse_co2_gkm(getattr(vehicle, "emissions", None))
        breakdown = self._compute_cost_breakdown(
            purchase_price=purchase_price,
            profile=profile,
            extra_costs=extra_costs,
            co2_gkm=co2_gkm,
        )

        # --- Precio de venta estimado ---
        if estimated_sale_price is not None and estimated_sale_price > 0:
            sale_price = estimated_sale_price
        else:
            sale_price = purchase_price * sale_price_multiplier

        # --- Beneficio bruto (sin costes de importación) ---
        gross_profit = sale_price - purchase_price

        # --- Beneficio neto (restando todos los costes) ---
        net_profit = sale_price - breakdown.total_cost

        # --- ROI (Return On Investment) ---
        roi_percentage = (
            (net_profit / breakdown.total_cost) * 100.0
            if breakdown.total_cost > 0
            else 0.0
        )

        # --- Margen de beneficio ---
        profit_margin_percentage = (
            (net_profit / sale_price) * 100.0 if sale_price > 0 else 0.0
        )

        # --- Clasificación de riesgo ---
        roi = net_profit / breakdown.total_cost if breakdown.total_cost > 0 else 0.0
        # cost_ratio = costes de importación / precio de compra (excluyendo el propio precio)
        import_costs = breakdown.total_cost - purchase_price
        cost_ratio = import_costs / purchase_price if purchase_price > 0 else 0.0

        risk_level = self._classify_risk(
            roi=roi,
            net_profit=net_profit,
            cost_ratio=cost_ratio,
            profile=profile,
        )

        # --- Recomendación ---
        recommendation = self._get_recommendation(
            risk_level=risk_level,
            roi=roi,
            net_profit=net_profit,
            profile=profile,
        )

        # --- Avisos (no errores) sobre el análisis ---
        warnings = self._compute_warnings(
            breakdown=breakdown, purchase_price=purchase_price
        )

        return ProfitAnalysis(
            purchase_price=purchase_price,
            transport_cost=breakdown.transport_cost,
            registration_cost=breakdown.registration_cost,
            taxes=breakdown.taxes,
            inspection_cost=breakdown.inspection_cost,
            repair_estimate=breakdown.repair_estimate,
            commission_cost=breakdown.commission_cost,
            miscellaneous_cost=breakdown.miscellaneous_cost,
            total_cost=breakdown.total_cost,
            estimated_sale_price=sale_price,
            gross_profit=gross_profit,
            net_profit=net_profit,
            roi_percentage=round(roi_percentage, 2),
            profit_margin_percentage=round(profit_margin_percentage, 2),
            risk_level=risk_level,
            recommendation=recommendation,
            cost_breakdown=breakdown,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Cálculo de costes
    # ------------------------------------------------------------------

    def _compute_cost_breakdown(
        self,
        purchase_price: float,
        profile: Any,
        extra_costs: dict[str, float],
        co2_gkm: float | None = None,
    ) -> CostBreakdown:
        """Calcula el desglose completo de costes.

        Args:
            purchase_price: Precio de compra del vehículo.
            profile: Perfil de costes ImportCostProfile.
            extra_costs: Costes adicionales opcionales.
            co2_gkm: Emisiones CO₂ del vehículo (para IEDMT, solo España).

        Returns:
            CostBreakdown con todos los costes calculados.
        """
        # Costes fijos (directamente del perfil)
        transport_cost = profile.transport_cost
        registration_cost = profile.registration_cost
        inspection_cost = profile.inspection_cost
        paperwork_cost = profile.paperwork_cost
        base_miscellaneous = profile.miscellaneous_cost

        # IEDMT: impuesto especial por CO₂ (solo España, co2 disponible)
        from app.services.iedmt import iedmt_tax

        iedmt = iedmt_tax(co2_gkm) if co2_gkm else 0.0

        # Costes variables (porcentaje sobre el precio de compra)
        # Si hay IEDMT, se suma al tax_rate base
        taxes = purchase_price * profile.tax_rate + iedmt
        commission_cost = purchase_price * profile.commission_rate
        repair_estimate = purchase_price * profile.repair_estimate_rate

        # Agregar costes adicionales opcionales
        for category, value in extra_costs.items():
            if category in ("insurance", "customs", "financing", "storage", "detailing"):
                base_miscellaneous += value

        # Totales
        total_fixed_costs = (
            transport_cost
            + registration_cost
            + inspection_cost
            + paperwork_cost
            + base_miscellaneous
        )
        total_variable_costs = taxes + commission_cost + repair_estimate

        total_cost = purchase_price + total_fixed_costs + total_variable_costs

        return CostBreakdown(
            purchase_price=purchase_price,
            transport_cost=transport_cost,
            registration_cost=registration_cost,
            taxes=taxes,
            inspection_cost=inspection_cost,
            repair_estimate=repair_estimate,
            commission_cost=commission_cost,
            miscellaneous_cost=base_miscellaneous + paperwork_cost,
            total_fixed_costs=total_fixed_costs,
            total_variable_costs=total_variable_costs,
            total_cost=total_cost,
            iedmt_amount=iedmt,
            co2_gkm=co2_gkm,
        )

    # ------------------------------------------------------------------
    # Clasificación de riesgo
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_risk(
        roi: float,
        net_profit: float,
        cost_ratio: float,
        profile: Any,
    ) -> RiskLevel:
        """Clasifica el nivel de riesgo de la operación.

        La clasificación se basa en umbrales configurables del perfil:

        - ROI muy alto + beneficio alto + costes bajos → LOW
        - ROI bajo + beneficio pequeño + costes altos → HIGH
        - Casos intermedios → MEDIUM
        """
        # Beneficio negativo → riesgo alto siempre
        if net_profit <= 0:
            return RiskLevel.HIGH

        # Factores positivos (reducen riesgo)
        high_roi = roi >= profile.risk_high_roi_threshold
        high_profit = net_profit >= profile.risk_high_profit_threshold
        low_costs = cost_ratio <= profile.risk_low_cost_ratio_threshold

        # Factores negativos (aumentan riesgo)
        low_roi = roi < profile.risk_low_roi_threshold
        low_profit = net_profit < profile.risk_low_profit_threshold
        high_costs = cost_ratio > profile.risk_high_cost_ratio_threshold

        positive_factors = sum([high_roi, high_profit, low_costs])
        negative_factors = sum([low_roi, low_profit, high_costs])

        # Todos o mayoría de factores negativos → riesgo alto
        if negative_factors >= 2:
            return RiskLevel.HIGH

        # Todos o mayoría de factores positivos → riesgo bajo
        if positive_factors >= 2:
            return RiskLevel.LOW

        # Caso intermedio
        return RiskLevel.MEDIUM

    # ------------------------------------------------------------------
    # Recomendación
    # ------------------------------------------------------------------

    @staticmethod
    def _get_recommendation(
        risk_level: RiskLevel,
        roi: float,
        net_profit: float,
        profile: Any,
    ) -> Recommendation:
        """Determina la recomendación final basada en el riesgo y la rentabilidad."""
        # Beneficio negativo → rechazar
        if net_profit <= 0:
            return Recommendation.REJECT

        # Riesgo bajo y ROI positivo → comprar
        if risk_level == RiskLevel.LOW and roi > 0:
            return Recommendation.BUY

        # Riesgo alto → rechazar
        if risk_level == RiskLevel.HIGH:
            return Recommendation.REJECT

        # Caso intermedio → considerar
        return Recommendation.CONSIDER

    # ------------------------------------------------------------------
    # Avisos (warnings) — enriquecen el breakdown sin ser errores
    # ------------------------------------------------------------------

    _COST_DISCLAIMER: Final[str] = (
        "Los valores del perfil son estimaciones de trabajo, no asesoramiento "
        "fiscal; contrastar con gestoría, ITV, DGT/ISV según el caso."
    )

    @staticmethod
    def _compute_warnings(breakdown: CostBreakdown, purchase_price: float) -> list[str]:
        """Genera avisos (no errores) sobre el análisis económico.

        Incluye un disclaimer de estimación y avisos ante costes anómalos
        (p. ej. importación que supera el 50% del precio de compra).
        """
        warnings: list[str] = [ProfitAnalyzer._COST_DISCLAIMER]
        import_costs = breakdown.total_cost - purchase_price
        if import_costs > 0.5 * purchase_price:
            warnings.append(
                "Los costes de importación superan el 50% del precio de compra; "
                "revisa el perfil de costes."
            )
        return warnings
