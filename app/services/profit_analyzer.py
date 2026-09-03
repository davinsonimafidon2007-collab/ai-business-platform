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
from decimal import ROUND_DOWN, Decimal
from enum import Enum
from typing import Any, ClassVar, Final, Protocol

# =============================================================================
# Enumeraciones de salida
# =============================================================================


class ProfitRecommendation(str, Enum):
    """Recomendación de compra basada exclusivamente en la señal financiera
    aislada de ProfitAnalyzer (riesgo + ROI + beneficio de este vehículo).

    TASK 2: renombrado desde ``Recommendation`` para no colisionar
    conceptualmente con ``OpportunityFinder.Recommendation`` (BUY_NOW/WATCH/
    NEGOTIATE/REJECT), que es la recomendación de nivel Opportunity que se
    persiste y expone en la API/frontend. ``ProfitRecommendation`` es una
    señal más estrecha, consumida internamente por ``EvaluationEngine``.

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
    recommendation: ProfitRecommendation
    cost_breakdown: CostBreakdown = field(repr=False)
    warnings: list[str] = field(default_factory=list, repr=False)


@dataclass
class MaxPurchasePriceResult:
    """Resultado del cálculo inverso de precio máximo de compra (TASK 2).

    Dado un precio de venta esperado y unos requisitos mínimos de margen/ROI,
    ``max_purchase_price`` es el precio de compra más alto que sigue
    cumpliendo AMBOS requisitos simultáneamente (el más restrictivo de los
    dos, indicado en ``binding_constraint``).
    """

    max_purchase_price: float
    """Precio de compra máximo permitido (EUR), redondeado hacia abajo
    (conservador: nunca sugiere pagar más de lo que realmente cumple los
    requisitos)."""

    binding_constraint: str
    """Cuál de los dos requisitos determina el resultado: "margin" o "roi"."""

    effective_sale_price: float
    """Precio de venta tras aplicar el buffer de riesgo (más bajo que
    ``estimated_sale_price`` si ``risk_buffer_percentage`` > 0)."""

    estimated_sale_price: float
    """Precio de venta de entrada, sin el buffer de riesgo aplicado."""

    fixed_costs: float
    """Suma de costes fijos del perfil (transporte, matriculación, ITV,
    gestoría, otros) usados en el cálculo."""

    variable_rate: float
    """Tasa variable total aplicada sobre el precio de compra (impuestos +
    comisión + reparación estimada), como fracción (0..1)."""

    is_dealer: bool
    """Si se aplicó el régimen de IVA pleno (vendedor profesional) en vez
    del régimen de margen (particular) al calcular ``variable_rate``."""


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
        logger.debug("profit result: %s", result.recommendation)

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
        seller_type: str | None = None,
        **extra_costs: float,
    ) -> ProfitAnalysis:
        """Realiza el análisis económico completo de importación.

        Args:
            vehicle: Objeto que implementa VehicleData.
            profile_name: Nombre del perfil de costes a utilizar.
            estimated_sale_price: Precio de venta estimado (si se proporciona,
                se usa directamente; si no, se calcula como purchase_price * multiplier).
            sale_price_multiplier: Multiplicador para estimar precio de venta
                cuando no se proporciona estimated_sale_price. Solo se usa
                como último recurso: preferir siempre pasar un
                estimated_sale_price real (comparables de mercado).
            seller_type: Tipo de vendedor ("private"/"dealer"/"professional"/...).
                Si es ``None``, se usa ``getattr(vehicle, "seller_type", None)``.
                Un vendedor profesional/concesionario tributa IVA pleno (21%)
                en vez del régimen de margen simplificado del perfil
                (AUD-009): ver ``_is_dealer_seller``.
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
        seller_type_value = (
            seller_type if seller_type is not None else getattr(vehicle, "seller_type", None)
        )
        is_dealer = self._is_dealer_seller(seller_type_value)
        breakdown = self._compute_cost_breakdown(
            purchase_price=purchase_price,
            profile=profile,
            extra_costs=extra_costs,
            co2_gkm=co2_gkm,
            is_dealer=is_dealer,
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
            breakdown=breakdown,
            purchase_price=purchase_price,
            is_dealer=is_dealer,
            co2_gkm=co2_gkm,
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
        is_dealer: bool = False,
    ) -> CostBreakdown:
        """Calcula el desglose completo de costes.

        Args:
            purchase_price: Precio de compra del vehículo.
            profile: Perfil de costes ImportCostProfile.
            extra_costs: Costes adicionales opcionales.
            co2_gkm: Emisiones CO₂ del vehículo (para IEDMT, solo España).
            is_dealer: Si el vendedor es profesional/concesionario (AUD-009):
                tributa IVA pleno (21%) + IEDMT en vez del régimen de margen
                simplificado (``profile.tax_rate``) que asume vendedor
                particular.

        Returns:
            CostBreakdown con todos los costes calculados.
        """
        # Costes fijos (directamente del perfil)
        transport_cost = profile.transport_cost
        registration_cost = profile.registration_cost
        inspection_cost = profile.inspection_cost
        paperwork_cost = profile.paperwork_cost
        base_miscellaneous = profile.miscellaneous_cost

        # Impuestos: régimen de margen (particular, perfil) vs IVA pleno +
        # IEDMT (profesional/concesionario). GRAVE.008: el IEDMT es un % de
        # la base imponible (purchase_price), no un importe fijo por tramo.
        from app.services.iedmt import iedmt_plus_vat, iedmt_tax

        if is_dealer:
            vat_breakdown = iedmt_plus_vat(co2_gkm, purchase_price)
            iedmt = vat_breakdown["iedmt"]
            taxes = vat_breakdown["total_taxes"]
        else:
            iedmt = iedmt_tax(co2_gkm, purchase_price) if co2_gkm else 0.0
            # Costes variables (porcentaje sobre el precio de compra).
            # Si hay IEDMT, se suma al tax_rate base (régimen de margen).
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
    ) -> ProfitRecommendation:
        """Determina la recomendación final basada en el riesgo y la rentabilidad."""
        # Beneficio negativo → rechazar
        if net_profit <= 0:
            return ProfitRecommendation.REJECT

        # Riesgo bajo y ROI positivo → comprar
        if risk_level == RiskLevel.LOW and roi > 0:
            return ProfitRecommendation.BUY

        # Riesgo alto → rechazar
        if risk_level == RiskLevel.HIGH:
            return ProfitRecommendation.REJECT

        # Caso intermedio → considerar
        return ProfitRecommendation.CONSIDER

    # ------------------------------------------------------------------
    # Avisos (warnings) — enriquecen el breakdown sin ser errores
    # ------------------------------------------------------------------

    _COST_DISCLAIMER: Final[str] = (
        "Los valores del perfil son estimaciones de trabajo, no asesoramiento "
        "fiscal; contrastar con gestoría, ITV, DGT/ISV según el caso."
    )

    @staticmethod
    def _compute_warnings(
        breakdown: CostBreakdown,
        purchase_price: float,
        is_dealer: bool = False,
        co2_gkm: float | None = None,
    ) -> list[str]:
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
        if is_dealer and not co2_gkm:
            warnings.append(
                "Vendedor profesional/concesionario sin emisiones CO₂ disponibles: "
                "se aplicó IVA pleno (21%) sin IEDMT (no se pudo calcular el tramo)."
            )
        return warnings

    # ------------------------------------------------------------------
    # Tipo de vendedor (AUD-009: régimen de margen vs IVA pleno)
    # ------------------------------------------------------------------

    _DEALER_MARKERS: Final[tuple[str, ...]] = (
        "dealer",
        "professional",
        "profesional",
        "concesionario",
        "empresa",
        "comercial",
        "business",
        "trade",
        "händler",
        "handler",
    )

    @classmethod
    def _is_dealer_seller(cls, seller_type: str | None) -> bool:
        """Determina si ``seller_type`` corresponde a un vendedor profesional.

        Normaliza distintos vocabularios usados por las distintas fuentes de
        datos de vehículos (unas usan "dealer"/"private"; otras
        "professional"/"private", o valores en alemán/español). Cualquier
        valor no reconocido se trata como particular (régimen de margen),
        que es el comportamiento previo por defecto — no se asume IVA pleno
        sin evidencia explícita.
        """
        if not seller_type:
            return False
        normalized = str(seller_type).strip().lower()
        return any(marker in normalized for marker in cls._DEALER_MARKERS)

    # ------------------------------------------------------------------
    # Precio máximo de compra (cálculo inverso, TASK 2)
    # ------------------------------------------------------------------

    def calculate_max_purchase_price(
        self,
        estimated_sale_price: float,
        profile_name: str = "DEFAULT",
        *,
        min_margin_percentage: float = 15.0,
        min_roi_percentage: float = 15.0,
        risk_buffer_percentage: float = 0.0,
        seller_type: str | None = None,
        co2_gkm: float | None = None,
    ) -> MaxPurchasePriceResult:
        """Calcula el precio máximo de compra que sigue cumpliendo los
        requisitos mínimos de margen y ROI (cálculo inverso al de ``analyze``).

        Toda la aritmética se hace con ``Decimal`` para evitar arrastrar
        errores de redondeo de punto flotante en una cadena de divisiones;
        solo se convierte a ``float`` en el resultado final, igual que el
        resto de la API pública de este módulo (que trabaja en float).

        Modelo: dado un precio de compra P, los costes fijos F (transporte,
        matriculación, ITV, gestoría, otros — no dependen de P) y una tasa
        variable v (impuestos + comisión + reparación, como fracción de P):

            total_cost   = P * (1 + v) + F
            net_profit   = S_eff - total_cost
            margin       = net_profit / S_eff        >= min_margin
            roi          = net_profit / total_cost    >= min_roi

        Despejando P de cada restricción por separado y tomando el mínimo
        (la restricción más exigente gana):

            P_margin = (S_eff * (1 - min_margin) - F) / (1 + v)
            P_roi    = (S_eff / (1 + min_roi) - F) / (1 + v)

        Args:
            estimated_sale_price: Precio de venta esperado en destino (EUR).
            profile_name: Perfil de costes a usar para F y v.
            min_margin_percentage: Margen mínimo requerido (%), sobre el
                precio de venta efectivo.
            min_roi_percentage: ROI mínimo requerido (%), sobre el coste total.
            risk_buffer_percentage: Reduce el precio de venta usado en el
                cálculo en este porcentaje, para no depender de que el precio
                de venta estimado se cumpla exactamente (buffer de riesgo).
            seller_type: Tipo de vendedor; determina si se usa IVA pleno
                (profesional) o régimen de margen (particular) para la tasa
                variable, igual que en ``analyze``.
            co2_gkm: Emisiones CO₂, para el tramo de IEDMT si es vendedor
                profesional.

        Returns:
            MaxPurchasePriceResult con el precio máximo y el desglose usado.

        Raises:
            ValueError: Si ``estimated_sale_price`` no es positivo, o si los
                porcentajes están fuera de rangos razonables (0-99.99 para
                margen/buffer; ROI mínimo no puede ser negativo).
        """
        if estimated_sale_price is None or estimated_sale_price <= 0:
            raise ValueError(
                "estimated_sale_price debe ser un valor positivo para calcular "
                "el precio máximo de compra."
            )
        if not (0.0 <= min_margin_percentage < 100.0):
            raise ValueError("min_margin_percentage debe estar en [0, 100).")
        if min_roi_percentage < 0.0:
            raise ValueError("min_roi_percentage no puede ser negativo.")
        if not (0.0 <= risk_buffer_percentage < 100.0):
            raise ValueError("risk_buffer_percentage debe estar en [0, 100).")

        profile = self._get_profile(profile_name)
        is_dealer = self._is_dealer_seller(seller_type)

        sale_price = Decimal(str(estimated_sale_price))
        buffer_fraction = Decimal(str(risk_buffer_percentage)) / Decimal("100")
        effective_sale_price = sale_price * (Decimal("1") - buffer_fraction)

        margin_fraction = Decimal(str(min_margin_percentage)) / Decimal("100")
        roi_fraction = Decimal(str(min_roi_percentage)) / Decimal("100")

        fixed_costs = Decimal(
            str(
                profile.transport_cost
                + profile.registration_cost
                + profile.inspection_cost
                + profile.paperwork_cost
                + profile.miscellaneous_cost
            )
        )

        if is_dealer:
            from app.services.iedmt import VAT_RATE_SPAIN, iedmt_rate

            tax_rate = Decimal(str(iedmt_rate(co2_gkm))) + Decimal(str(VAT_RATE_SPAIN))
        else:
            tax_rate = Decimal(str(profile.tax_rate))

        variable_rate = (
            tax_rate + Decimal(str(profile.commission_rate)) + Decimal(str(profile.repair_estimate_rate))
        )
        rate_denominator = Decimal("1") + variable_rate

        price_from_margin = (
            effective_sale_price * (Decimal("1") - margin_fraction) - fixed_costs
        ) / rate_denominator
        price_from_roi = (
            effective_sale_price / (Decimal("1") + roi_fraction) - fixed_costs
        ) / rate_denominator

        if price_from_margin <= price_from_roi:
            max_price = price_from_margin
            binding = "margin"
        else:
            max_price = price_from_roi
            binding = "roi"

        max_price = max(Decimal("0"), max_price).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        return MaxPurchasePriceResult(
            max_purchase_price=float(max_price),
            binding_constraint=binding,
            effective_sale_price=float(effective_sale_price.quantize(Decimal("0.01"))),
            estimated_sale_price=float(estimated_sale_price),
            fixed_costs=float(fixed_costs),
            variable_rate=float(variable_rate),
            is_dealer=is_dealer,
        )
