"""NegotiationEngine — Motor de estrategia de negociación.

Convierte la información generada por la inspección, estimación de
reparación, valoración de mercado y análisis de rentabilidad en
una estrategia completa de negociación para la compra de un vehículo.

Dependencias:
    - app/models/negotiation.py (DTOs de entrada/salida)
    - app/config/negotiation.py (umbrales y pesos configurables)

No depende de:
    - Bases de datos.
    - Repositorios.
    - Internet.

Sigue el mismo patrón que ``OpportunityFinder`` y ``ProfitAnalyzer``.
"""

from __future__ import annotations

from app.config.negotiation import (
    ACCIDENT_DISCOUNT_PERCENT,
    BUY_MAX_DISCOUNT_NEEDED,
    COUNTER_OFFER_MULTIPLIER,
    HIGH_SEVERITY_THRESHOLD,
    LEVERAGE_ACCIDENT_WEIGHT,
    LEVERAGE_DEFECT_WEIGHT,
    LEVERAGE_MARKET_WEIGHT,
    LEVERAGE_PROFIT_WEIGHT,
    LEVERAGE_REPAIR_COST_WEIGHT,
    LEVERAGE_VEHICLE_SCORE_WEIGHT,
    MAX_INITIAL_OFFER_PERCENT_OF_VALUE,
    MAX_PURCHASE_PRICE_MULTIPLIER,
    MAX_SCRIPT_DEFECT_POINTS,
    MAX_SCRIPT_MARKET_POINTS,
    MIN_MARGIN_FOR_BUY,
    MIN_OFFER_PERCENT_OF_VALUE,
    MIN_PROFIT_FOR_NEGOTIATE,
    MIN_ROI_FOR_BUY,
    NEGOTIATE_MIN_LEVERAGE_SCORE,
    SAFETY_DEFECT_SEVERITY_BOOST,
    WALK_AWAY_MIN_DISCOUNT_NEEDED,
    WALK_AWAY_MULTIPLIER,
)
from app.models.negotiation import (
    NegotiationArgument,
    NegotiationInput,
    NegotiationRecommendation,
    NegotiationResult,
    NegotiationScript,
)


class NegotiationEngine:
    """Motor de estrategia de negociación para compra de vehículos.

    Consume los resultados de InspectionResult, RepairEstimate,
    MarketEstimation, ProfitAnalysis y VehicleScore para producir
    una estrategia completa de negociación.

    NO modifica el estado de ningún modelo existente.
    NO realiza operaciones de base de datos.
    NO depende de proveedores externos.

    Uso:
        engine = NegotiationEngine()
        result = engine.analyze(negotiation_input)
        print(result.recommendation, result.recommended_initial_offer)
    """

    def __init__(self) -> None:
        """Inicializa el motor de negociación."""
        pass

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def analyze(self, input_data: NegotiationInput) -> NegotiationResult:
        """Ejecuta el análisis completo de estrategia de negociación.

        Args:
            input_data: NegotiationInput con toda la información agregada.

        Returns:
            NegotiationResult con la estrategia completa de negociación.
        """
        # 1. Estimar el valor real del vehículo
        estimated_value = self._calculate_estimated_vehicle_value(input_data)

        # 2. Calcular apalancamiento (leverage del comprador)
        leverage_score = self._calculate_leverage(input_data)

        # 3. Calcular precios estratégicos
        initial_offer = self._calculate_initial_offer(
            estimated_value=estimated_value,
            leverage_score=leverage_score,
            asking_price=input_data.asking_price,
        )
        counter_offer = self._calculate_counter_offer(initial_offer)
        max_price = self._calculate_max_purchase_price(estimated_value)
        walk_away = self._calculate_walk_away_price(estimated_value)

        # 4. Calcular price gap y descuento necesario
        price_gap = input_data.asking_price - estimated_value
        discount_needed = (
            ((input_data.asking_price - initial_offer) / input_data.asking_price) * 100.0
            if input_data.asking_price > 0
            else 0.0
        )

        # 5. Generar argumentos de negociación
        arguments = self._generate_negotiation_arguments(input_data)

        # 6. Generar script de negociación
        script = self._generate_negotiation_script(
            input_data=input_data,
            arguments=arguments,
            initial_offer=initial_offer,
            estimated_value=estimated_value,
        )

        # 7. Calcular beneficio y ROI esperados
        expected_profit, expected_roi = self._calculate_expected_profit(
            input_data=input_data,
            purchase_price=initial_offer,
            estimated_value=estimated_value,
        )

        # 8. Determinar recomendación
        recommendation = self._get_recommendation(
            discount_needed=discount_needed,
            leverage_score=leverage_score,
            expected_profit=expected_profit,
            expected_roi=expected_roi,
            input_data=input_data,
        )

        return NegotiationResult(
            estimated_vehicle_value=round(estimated_value, 2),
            recommended_initial_offer=round(initial_offer, 2),
            recommended_counter_offer=round(counter_offer, 2),
            maximum_purchase_price=round(max_price, 2),
            walk_away_price=round(walk_away, 2),
            expected_profit=round(expected_profit, 2),
            expected_roi=round(expected_roi, 2),
            negotiation_arguments=arguments,
            negotiation_script=script,
            recommendation=recommendation,
            leverage_score=round(leverage_score, 2),
            price_gap=round(price_gap, 2),
            discount_needed=round(discount_needed, 2),
        )

    # ------------------------------------------------------------------
    # Cálculo del valor estimado del vehículo
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_estimated_vehicle_value(input_data: NegotiationInput) -> float:
        """Estima el valor real del vehículo ajustando el precio de mercado
        con los costes de reparación necesarios.

        Valor estimado = market_price - total_repair_cost - accident_discount
        """
        market_price = getattr(input_data.market_estimation, "market_price", input_data.asking_price)
        if not market_price or market_price <= 0:
            market_price = input_data.asking_price

        repair_cost = input_data.repair_estimate.total_repair_cost

        # Descuento por accidentes (mismo % que en argumentos de negociación)
        accident_discount = 0.0
        if input_data.inspection_result.has_accident_history:
            accident_discount = market_price * ACCIDENT_DISCOUNT_PERCENT

        estimated_value = market_price - repair_cost - accident_discount
        return max(estimated_value, 0.0)

    # ------------------------------------------------------------------
    # Cálculo de apalancamiento (leverage score)
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_leverage(input_data: NegotiationInput) -> float:
        """Calcula la puntuación de apalancamiento del comprador (0-100).

        Un leverage alto significa que el comprador tiene muchos argumentos
        para negociar a la baja.

        Componentes:
            - Defectos (severidad, cantidad, seguridad)
            - Coste de reparación
            - Historial de accidentes
            - Condiciones de mercado (baja demanda, alta oferta)
            - Score del vehículo (bajo score = más apalancamiento)
            - Beneficio/ROI (bajo ROI = más apalancamiento para pedir descuento)
        """
        # --- Score de defectos (0-100) ---
        defects = input_data.inspection_result.defects
        if defects:
            total_severity = sum(
                d.severity * (SAFETY_DEFECT_SEVERITY_BOOST if d.is_safety_relevant else 1.0)
                for d in defects
                if d.can_be_used_as_leverage
            )
            num_leverage_defects = sum(1 for d in defects if d.can_be_used_as_leverage)
            # Severidad máxima posible: 10 * num_defects
            max_severity = max(num_leverage_defects * 10, 1)
            defect_score = (total_severity / max_severity) * 100.0
            defect_score = min(defect_score, 100.0)
        else:
            defect_score = 0.0

        # --- Score de coste de reparación (0-100) ---
        repair_cost = input_data.repair_estimate.total_repair_cost
        asking_price = input_data.asking_price
        if asking_price > 0 and repair_cost > 0:
            repair_ratio = repair_cost / asking_price
            # Si repair_cost > 20% del asking_price → score 100
            # Si repair_cost < 1% del asking_price → score 0
            repair_score = min(repair_ratio / 0.20 * 100.0, 100.0)
        else:
            repair_score = 0.0

        # --- Score de accidentes (0-100) ---
        accident_score = 50.0 if input_data.inspection_result.has_accident_history else 0.0

        # --- Score de mercado (0-100) ---
        market_est = input_data.market_estimation
        supply = getattr(market_est, "supply_level", 50.0) or 50.0
        demand = getattr(market_est, "demand_level", 50.0) or 50.0
        trend = getattr(market_est, "market_trend", "stable") or "stable"

        # Alta oferta + baja demanda + tendencia a la baja = alto apalancamiento
        supply_score = supply  # 0-100, más oferta = más apalancamiento
        demand_score = 100.0 - demand  # Invertido: menos demanda = más apalancamiento
        trend_score = {"falling": 80.0, "stable": 50.0, "rising": 20.0}.get(trend, 50.0)
        market_score = (supply_score * 0.3 + demand_score * 0.4 + trend_score * 0.3)

        # --- Score del vehículo (0-100, invertido) ---
        vehicle_data = input_data.vehicle_score_data
        raw_score = vehicle_data.get("score", 50)
        if raw_score is None:
            raw_score = 50
        # Invertir: bajo score de vehículo = más apalancamiento
        vehicle_score = 100.0 - float(raw_score)

        # --- Score de rentabilidad (0-100, invertido) ---
        profit_data = input_data.profit_analysis_data
        roi = profit_data.get("roi_percentage", profit_data.get("roi", 0.0)) or 0.0
        net_profit = profit_data.get("net_profit", 0.0) or 0.0
        risk = profit_data.get("risk_level", "")

        # Bajo ROI + bajo beneficio + alto riesgo = más apalancamiento
        roi_component = max(0.0, 100.0 - (roi * 5.0))  # 20% ROI → 0 leverage
        profit_component = 0.0
        if net_profit <= 0:
            profit_component = 100.0
        else:
            profit_component = max(0.0, 100.0 - (net_profit / 100.0))  # 1000€ profit → 90
        risk_str = risk.value if hasattr(risk, "value") else str(risk or "")
        risk_component = {"HIGH": 100.0, "MEDIUM": 50.0, "LOW": 0.0}.get(risk_str, 50.0)
        profit_score = roi_component * 0.4 + profit_component * 0.3 + risk_component * 0.3

        # --- Combinación ponderada ---
        total_weight = (
            LEVERAGE_DEFECT_WEIGHT
            + LEVERAGE_REPAIR_COST_WEIGHT
            + LEVERAGE_ACCIDENT_WEIGHT
            + LEVERAGE_MARKET_WEIGHT
            + LEVERAGE_VEHICLE_SCORE_WEIGHT
            + LEVERAGE_PROFIT_WEIGHT
        )

        if total_weight <= 0:
            return 50.0

        leverage = (
            defect_score * LEVERAGE_DEFECT_WEIGHT
            + repair_score * LEVERAGE_REPAIR_COST_WEIGHT
            + accident_score * LEVERAGE_ACCIDENT_WEIGHT
            + market_score * LEVERAGE_MARKET_WEIGHT
            + vehicle_score * LEVERAGE_VEHICLE_SCORE_WEIGHT
            + profit_score * LEVERAGE_PROFIT_WEIGHT
        ) / total_weight

        return max(0.0, min(100.0, leverage))

    # ------------------------------------------------------------------
    # Cálculo de precios estratégicos
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_initial_offer(
        estimated_value: float,
        leverage_score: float,
        asking_price: float,
    ) -> float:
        """Calcula la oferta inicial recomendada.

        Base: 90% del valor estimado, menos descuento por leverage (hasta 15%).
        Suelo: MIN_OFFER_PERCENT_OF_VALUE del valor estimado (no del asking).
        Techo: nunca superar el asking_price ni el valor estimado.
        """
        if estimated_value <= 0:
            return asking_price * 0.80 if asking_price > 0 else 0.0

        # Base: 90% del valor estimado
        base_offer = estimated_value * MAX_INITIAL_OFFER_PERCENT_OF_VALUE

        # Ajuste por leverage: hasta 15% adicional de descuento sobre el valor
        leverage_discount = (leverage_score / 100.0) * 0.15 * estimated_value
        offer = base_offer - leverage_discount

        # Suelo: no bajar del % mínimo del valor estimado
        min_offer = estimated_value * MIN_OFFER_PERCENT_OF_VALUE
        offer = max(offer, min_offer)

        # Techo: no superar asking ni valor estimado
        if asking_price > 0:
            offer = min(offer, asking_price)
        offer = min(offer, estimated_value)

        return offer

    @staticmethod
    def _calculate_counter_offer(initial_offer: float) -> float:
        """Calcula la contraoferta como un pequeño incremento sobre la inicial."""
        return initial_offer * (1.0 + COUNTER_OFFER_MULTIPLIER)

    @staticmethod
    def _calculate_max_purchase_price(estimated_value: float) -> float:
        """Calcula el precio máximo que se puede pagar."""
        return estimated_value * MAX_PURCHASE_PRICE_MULTIPLIER

    @staticmethod
    def _calculate_walk_away_price(estimated_value: float) -> float:
        """Calcula el precio de walk-away (abandonar la negociación)."""
        return estimated_value * WALK_AWAY_MULTIPLIER

    # ------------------------------------------------------------------
    # Beneficio y ROI esperados
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_expected_profit(
        input_data: NegotiationInput,
        purchase_price: float,
        estimated_value: float,
    ) -> tuple[float, float]:
        """Calcula el beneficio y ROI esperados si se cierra al precio recomendado.

        El beneficio esperado es la diferencia entre el valor estimado de venta
        y el precio de compra, menos los costes de reparación y otros gastos.

        Se usa estimated_value como proxy del precio de venta estimado.
        Si hay datos de profit_analysis, se reutilizan para mayor precisión.
        """
        profit_data = input_data.profit_analysis_data
        sale_price = profit_data.get("estimated_sale_price", estimated_value)
        total_costs = profit_data.get("total_cost", purchase_price)

        # Si tenemos datos fiables de profit_analysis, usamos su lógica
        if profit_data.get("total_cost", 0) > 0:
            # Recalcular con el nuevo precio de compra
            cost_difference = purchase_price - profit_data.get("purchase_price", purchase_price)
            adjusted_total_cost = total_costs + cost_difference
            expected_profit = sale_price - adjusted_total_cost
            expected_roi = (
                (expected_profit / adjusted_total_cost) * 100.0
                if adjusted_total_cost > 0
                else 0.0
            )
        else:
            # Estimación simple
            repair_cost = input_data.repair_estimate.total_repair_cost
            total_investment = purchase_price + repair_cost
            expected_profit = sale_price - total_investment
            expected_roi = (
                (expected_profit / total_investment) * 100.0
                if total_investment > 0
                else 0.0
            )

        return expected_profit, expected_roi

    # ------------------------------------------------------------------
    # Generación de argumentos de negociación
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_negotiation_arguments(input_data: NegotiationInput) -> list[NegotiationArgument]:
        """Genera una lista de argumentos de negociación ordenados
        por impacto económico descendente.

        Los argumentos provienen de:
            1. Defectos detectados en la inspección
            2. Condiciones de mercado
            3. Score del vehículo
            4. Análisis de rentabilidad
        """
        arguments: list[NegotiationArgument] = []

        # --- Argumentos basados en defectos ---
        for defect in input_data.inspection_result.defects:
            if not defect.can_be_used_as_leverage:
                continue
            impact = defect.estimated_repair_cost
            if impact <= 0:
                # Si no hay coste estimado, asignar impacto basado en severidad
                impact = defect.severity * 50.0  # ~50 EUR por punto de severidad
            if defect.is_safety_relevant:
                impact *= SAFETY_DEFECT_SEVERITY_BOOST

            severity_label = "GRAVE" if defect.severity >= HIGH_SEVERITY_THRESHOLD else "moderado"
            safety_tag = " [SEGURIDAD]" if defect.is_safety_relevant else ""
            description = defect.description if defect.description else defect.category

            argument = NegotiationArgument(
                argument=(
                    f"{severity_label}: {description} "
                    f"(coste estimado: {impact:.0f} EUR){safety_tag}"
                ),
                economic_impact=round(impact, 2),
                category="defect",
                severity=defect.severity,
            )
            arguments.append(argument)

        # --- Argumentos basados en condiciones de mercado ---
        market = input_data.market_estimation
        supply = getattr(market, "supply_level", 50.0) or 50.0
        demand = getattr(market, "demand_level", 50.0) or 50.0
        trend = getattr(market, "market_trend", "stable") or "stable"
        market_price = getattr(market, "market_price", 0.0) or 0.0
        confidence = getattr(market, "confidence", 50.0) or 50.0

        # Mercado saturado
        if supply >= 70:
            impact = market_price * 0.05 if market_price > 0 else 500.0
            arguments.append(NegotiationArgument(
                argument=(
                    f"Mercado saturado para este modelo (oferta: {supply:.0f}/100). "
                    "Existen muchas alternativas disponibles."
                ),
                economic_impact=round(impact, 2),
                category="market",
                severity=6,
            ))

        # Demanda baja
        if demand <= 40:
            impact = market_price * 0.03 if market_price > 0 else 300.0
            arguments.append(NegotiationArgument(
                argument=(
                    f"Demanda baja en el mercado (demanda: {demand:.0f}/100). "
                    "El vehículo podría tardar en venderse."
                ),
                economic_impact=round(impact, 2),
                category="market",
                severity=5,
            ))

        # Tendencia a la baja
        if trend == "falling":
            impact = market_price * 0.04 if market_price > 0 else 400.0
            arguments.append(NegotiationArgument(
                argument="El mercado de este segmento está en tendencia a la baja. "
                "El valor del vehículo podría disminuir.",
                economic_impact=round(impact, 2),
                category="market",
                severity=5,
            ))

        # Confianza baja
        if confidence < 40:
            impact = market_price * 0.02 if market_price > 0 else 200.0
            arguments.append(NegotiationArgument(
                argument=(
                    f"Estimación de mercado con confianza baja ({confidence:.0f}%). "
                    "El precio de referencia no es fiable."
                ),
                economic_impact=round(impact, 2),
                category="market",
                severity=4,
            ))

        # --- Argumentos basados en score del vehículo ---
        vehicle_data = input_data.vehicle_score_data
        score = vehicle_data.get("score", None)
        if score is not None and score < 60:
            impact = (60 - score) * 20.0  # ~20 EUR por punto por debajo de 60
            # Debilidades específicas
            weaknesses = vehicle_data.get("weaknesses", [])
            if weaknesses:
                for w in weaknesses[:2]:
                    arguments.append(NegotiationArgument(
                        argument=f"Debilidad detectada: {w}",
                        economic_impact=round(impact / max(len(weaknesses), 1), 2),
                        category="vehicle",
                        severity=4,
                    ))
            else:
                arguments.append(NegotiationArgument(
                    argument=f"Puntuación general baja ({score}/100). "
                    "El vehículo presenta diversas carencias.",
                    economic_impact=round(impact, 2),
                    category="vehicle",
                    severity=4,
                ))

        # --- Argumentos basados en análisis de rentabilidad ---
        profit_data = input_data.profit_analysis_data
        roi = profit_data.get("roi_percentage", profit_data.get("roi", 0.0)) or 0.0
        net_profit = profit_data.get("net_profit", 0.0) or 0.0
        risk = profit_data.get("risk_level", "")

        if roi < 10.0 and roi > 0:
            impact = (10.0 - roi) * 100.0
            arguments.append(NegotiationArgument(
                argument=f"Margen de beneficio ajustado (ROI: {roi:.1f}%). "
                "Es necesario un descuento para garantizar la rentabilidad.",
                economic_impact=round(impact, 2),
                category="profit",
                severity=5,
            ))
        elif net_profit <= 0:
            impact = 500.0  # Impacto fijo para beneficio negativo
            risk_str = risk.value if hasattr(risk, "value") else str(risk or "")
            arguments.append(NegotiationArgument(
                argument=f"Beneficio neto negativo o nulo (riesgo: {risk_str}). "
                "Sin descuento sustancial, la operación no es rentable.",
                economic_impact=impact,
                category="profit",
                severity=8,
            ))

        # --- Historial de accidentes ---
        if input_data.inspection_result.has_accident_history:
            impact = market_price * ACCIDENT_DISCOUNT_PERCENT if market_price > 0 else 1500.0
            notes = f" {input_data.inspection_result.accident_notes}" if input_data.inspection_result.accident_notes else ""
            arguments.append(NegotiationArgument(
                argument=(
                    f"Historial de accidentes documentado.{notes} "
                    "Esto afecta significativamente al valor del vehículo."
                ),
                economic_impact=round(impact, 2),
                category="defect",
                severity=8,
            ))

        # --- Ordenar por impacto económico descendente ---
        arguments.sort(key=lambda a: a.economic_impact, reverse=True)

        return arguments

    # ------------------------------------------------------------------
    # Generación de script de negociación
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_negotiation_script(
        input_data: NegotiationInput,
        arguments: list[NegotiationArgument],
        initial_offer: float,
        estimated_value: float,
    ) -> NegotiationScript:
        """Genera un script de negociación en lenguaje natural a partir
        de los defectos detectados y las condiciones de mercado."""
        asking_price = input_data.asking_price
        defects = input_data.inspection_result.defects

        # --- Opening ---
        safety_defects = [d for d in defects if d.is_safety_relevant]
        total_repair = input_data.repair_estimate.total_repair_cost

        if safety_defects:
            safety_desc = safety_defects[0].description
            opening = (
                f"Buenos días, estoy interesado en el vehículo pero tras revisarlo "
                f"he detectado un problema importante de seguridad: {safety_desc}. "
                f"Además, el coste estimado de reparaciones asciende a {total_repair:.0f} EUR, "
                f"lo cual es un factor determinante en mi oferta."
            )
        elif total_repair > 0:
            opening = (
                f"Buenos días, me gusta el vehículo pero he identificado varias "
                f"reparaciones necesarias que suman {total_repair:.0f} EUR. "
                f"Por eso, mi oferta debe reflejar estos costes adicionales."
            )
        elif input_data.inspection_result.has_accident_history:
            opening = (
                "Buenos días, el vehículo me interesa pero tengo conocimiento "
                "de su historial de accidentes. Esto reduce significativamente "
                "su valor de mercado y mis expectativas de reventa."
            )
        else:
            opening = (
                "Buenos días, he analizado el vehículo y el mercado en detalle. "
                "Basándome en los datos objetivos, tengo una oferta que refleja "
                "el valor real del vehículo."
            )

        # --- Defect-based points (top N por impacto) ---
        defect_args = [a for a in arguments if a.category == "defect"]
        defect_points = []
        for arg in defect_args[:MAX_SCRIPT_DEFECT_POINTS]:
            defect_points.append(
                f"- {arg.argument} → impacto económico: {arg.economic_impact:.0f} EUR"
            )

        # --- Market-based points (top N por impacto) ---
        market_args = [a for a in arguments if a.category == "market"]
        market_points = []
        for arg in market_args[:MAX_SCRIPT_MARKET_POINTS]:
            market_points.append(
                f"- {arg.argument} → impacto: {arg.economic_impact:.0f} EUR"
            )

        # --- Closing ---
        if asking_price > initial_offer:
            discount_pct = ((asking_price - initial_offer) / asking_price) * 100.0
            closing = (
                f"Por todo ello, mi oferta es de {initial_offer:.0f} EUR, "
                f"lo que supone un descuento del {discount_pct:.1f}% sobre "
                f"el precio solicitado de {asking_price:.0f} EUR. "
                f"Creo que es una oferta justa basada en el valor real "
                f"del vehículo ({estimated_value:.0f} EUR). Quedo a la espera "
                f"de su respuesta."
            )
        else:
            closing = (
                f"Basándome en el análisis, el valor estimado del vehículo "
                f"es de {estimated_value:.0f} EUR. Mi oferta es de "
                f"{initial_offer:.0f} EUR, que considero un precio justo "
                f"y razonable para ambas partes."
            )

        return NegotiationScript(
            opening=opening.strip(),
            defect_based_points=defect_points,
            market_based_points=market_points,
            closing=closing.strip(),
        )

    # ------------------------------------------------------------------
    # Recomendación
    # ------------------------------------------------------------------

    @staticmethod
    def _get_recommendation(
        discount_needed: float,
        leverage_score: float,
        expected_profit: float,
        expected_roi: float,
        input_data: NegotiationInput,
    ) -> NegotiationRecommendation:
        """Determina la recomendación final basada en todos los factores.

        Reglas:
            - BUY: descuento necesario ≤ 5%, O ROI ≥ 5% y margen ≥ 10%.
            - WALK_AWAY: descuento necesario ≥ 25%, O beneficio negativo
(tanto original como recalculado).
            - NEGOTIATE: casos intermedios con apalancamiento suficiente.
        """
        # WALK_AWAY: descuento excesivo necesario
        if discount_needed >= WALK_AWAY_MIN_DISCOUNT_NEEDED:
            return NegotiationRecommendation.WALK_AWAY

        # WALK_AWAY: incluso con la oferta recomendada el beneficio es negativo/nulo
        if expected_profit < MIN_PROFIT_FOR_NEGOTIATE:
            return NegotiationRecommendation.WALK_AWAY

        # WALK_AWAY: cinturón de seguridad — el profit analysis ya es negativo
        # (pérdida económica domina sobre leverage / NEGOTIATE)
        profit_data = input_data.profit_analysis_data
        net_profit = profit_data.get("net_profit", 0.0) or 0.0
        if net_profit <= 0:
            return NegotiationRecommendation.WALK_AWAY

        # BUY: descuento pequeño necesario
        if discount_needed <= BUY_MAX_DISCOUNT_NEEDED:
            return NegotiationRecommendation.BUY

        roi = profit_data.get("roi_percentage", profit_data.get("roi", 0.0)) or 0.0
        margin = profit_data.get("profit_margin_percentage", 0.0) or 0.0

        # BUY: buen ROI y margen en el análisis de rentabilidad
        if roi >= MIN_ROI_FOR_BUY and margin >= MIN_MARGIN_FOR_BUY:
            return NegotiationRecommendation.BUY

        # NEGOTIATE: casos intermedios con apalancamiento suficiente
        if leverage_score >= NEGOTIATE_MIN_LEVERAGE_SCORE:
            return NegotiationRecommendation.NEGOTIATE

        # Sin apalancamiento y descuento alto → abandonar
        if discount_needed > 10.0:
            return NegotiationRecommendation.WALK_AWAY

        # Fallback: intentar negociar
        return NegotiationRecommendation.NEGOTIATE
