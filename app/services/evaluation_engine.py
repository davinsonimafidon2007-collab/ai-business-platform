"""Motor de evaluación de vehículos para calcular costes y rentabilidad."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.models.vehicle import Vehicle


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


class EvaluationEngine:
    """Motor de evaluación de vehículos.

    Calcula automáticamente todos los costes de importación,
    estima el precio de venta en España y determina la rentabilidad.
    """

    # Constantes configurables (valores por defecto)
    # Se pueden sobreescribir mediante Settings o variables de entorno

    # Costes fijos
    DEFAULT_ITV_COST: float = 150.0  # Coste base de la ITV
    DEFAULT_GESTORIA_COST: float = 350.0  # Coste base de gestoría
    DEFAULT_TRANSPORT_COST_PER_CUBIC_METER: float = 250.0  # €/m³

    # Impuestos
    IVA_RATE: float = 0.21  # 21% IVA en España
    IMPORT_TAX_RATE: float = 0.10  # 10% impuesto de importación (fuera de UE)

    # Matriculación
    REGISTRATION_TAX_RATE: float = 0.04  # 4% impuesto de matriculación
    REGISTRATION_FEE: float = 200.0  # Tasas de tráfico

    # Margen mínimo aceptable
    MIN_PROFIT_MARGIN_PERCENT: float = 15.0  # Margen mínimo para clasificación "verde"
    WARNING_PROFIT_MARGIN_PERCENT: float = 8.0  # Margen mínimo para clasificación "amarillo"

    # Umbrales de score
    GREEN_SCORE_THRESHOLD: int = 70  # Score mínimo para "verde"
    YELLOW_SCORE_THRESHOLD: int = 40  # Score mínimo para "amarillo"

    # Factores de depreciación por antigüedad
    AGE_DEPRECIATION_RATES: dict[int, float] = None  # Se inicializa en __init__

    def __init__(self) -> None:
        """Inicializa el motor de evaluación."""
        # Configurar tasas de depreciación por antigüedad
        self.AGE_DEPRECIATION_RATES = {
            1: 0.15,  # 1 año: 15% depreciación
            2: 0.25,  # 2 años: 25% depreciación
            3: 0.35,  # 3 años: 35% depreciación
            4: 0.45,  # 4 años: 45% depreciación
            5: 0.55,  # 5 años: 55% depreciación
        }
        # Para más de 5 años, usar 55% + 5% por año adicional

    def evaluate(self, vehicle: Vehicle) -> EvaluationResult:
        """Evalúa un vehículo y calcula todos los costes y rentabilidad.

        Args:
            vehicle: Vehículo a evaluar.

        Returns:
            EvaluationResult con todos los cálculos.
        """
        warnings: list[str] = []

        # 1. Coste del vehículo (precio de compra en Alemania)
        vehicle_cost = vehicle.price if vehicle.price and vehicle.price > 0 else 0.0
        if vehicle_cost == 0:
            warnings.append("no tiene precio de compra definido")

        # 2. Coste de transporte
        transport_cost = self._calculate_transport_cost(vehicle)

        # 3. Impuestos de importación (si viene de fuera de la UE)
        import_tax = self._calculate_import_tax(vehicle_cost)

        # 4. IVA
        iva = self._calculate_iva(vehicle_cost + import_tax)

        # 5. Impuesto de matriculación
        registration_tax = self._calculate_registration_tax(vehicle_cost)

        # 6. Tasas de matriculación
        registration_fee = self.REGISTRATION_FEE

        # 7. ITV
        itv_cost = self.DEFAULT_ITV_COST

        # 8. Gestoría
        gestoria_cost = self.DEFAULT_GESTORIA_COST

        # Coste total
        total_cost = (
            vehicle_cost
            + transport_cost
            + import_tax
            + iva
            + registration_tax
            + registration_fee
            + itv_cost
            + gestoria_cost
        )

        # 9. Precio estimado de venta en España
        estimated_sale_price_es = self._estimate_sale_price_in_spain(vehicle)
        if estimated_sale_price_es == 0:
            warnings.append("No se pudo estimar el precio de venta en España")

        # 10. Beneficio bruto
        gross_profit = estimated_sale_price_es - total_cost

        # 11. Margen porcentual
        if total_cost > 0:
            profit_margin_percent = (gross_profit / total_cost) * 100
        else:
            profit_margin_percent = 0.0
            warnings.append("El coste total es cero, no se puede calcular el margen")

        # 12. Score (0-100)
        score = self._calculate_score(vehicle, profit_margin_percent, warnings)

        # 13. Clasificación
        classification = self._classify(profit_margin_percent, score)

        # 14. Recomendación
        recommendation = self._generate_recommendation(classification, profit_margin_percent, warnings)

        return EvaluationResult(
            vehicle_cost=vehicle_cost,
            transport_cost=transport_cost,
            registration_cost=registration_tax + registration_fee,
            itv_cost=itv_cost,
            gestoria_cost=gestoria_cost,
            taxes_cost=import_tax + iva,
            total_cost=total_cost,
            estimated_sale_price_es=estimated_sale_price_es,
            gross_profit=gross_profit,
            profit_margin_percent=profit_margin_percent,
            score=score,
            classification=classification,
            warnings=warnings,
            recommendation=recommendation,
        )

    def _calculate_transport_cost(self, vehicle: Vehicle) -> float:
        """Calcula el coste de transporte desde Alemania.

        Args:
            vehicle: Vehículo a evaluar.

        Returns:
            Coste de transporte en euros.
        """
        # Coste base por tipo de vehículo
        base_cost = 500.0  # Coste base para coches estándar

        # Ajustar por tamaño (estimación basada en categoría)
        if vehicle.category:
            category_lower = vehicle.category.lower()
            if any(word in category_lower for word in ["suv", "pickup", "furgoneta", "van"]):
                base_cost = 750.0
            elif any(word in category_lower for word in ["compacto", "pequeño", "city"]):
                base_cost = 400.0

        # Ajustar por antigüedad (vehículos más antiguos pueden necesitar transporte especial)
        if vehicle.year:
            current_year = 2024  # Se puede hacer dinámico
            age = current_year - vehicle.year
            if age > 15:
                base_cost *= 1.2  # 20% más para vehículos muy antiguos

        return base_cost

    def _calculate_import_tax(self, vehicle_cost: float) -> float:
        """Calcula el impuesto de importación.

        Args:
            vehicle_cost: Coste del vehículo.

        Returns:
            Impuesto de importación en euros.
        """
        # Alemania está en la UE, pero si el vehículo viene de fuera,
        # se aplica este impuesto
        # Por defecto, asumimos que viene de Alemania (UE), así que 0
        # Pero dejamos la lógica preparada para futuros proveedores fuera de la UE
        return 0.0

    def _calculate_iva(self, base: float) -> float:
        """Calcula el IVA.

        Args:
            base: Base imponible.

        Returns:
            IVA en euros.
        """
        return base * self.IVA_RATE

    def _calculate_registration_tax(self, vehicle_cost: float) -> float:
        """Calcula el impuesto de matriculación.

        Args:
            vehicle_cost: Coste del vehículo.

        Returns:
            Impuesto de matriculación en euros.
        """
        return vehicle_cost * self.REGISTRATION_TAX_RATE

    def _estimate_sale_price_in_spain(self, vehicle: Vehicle) -> float:
        """Estima el precio de venta del vehículo en España.

        Args:
            vehicle: Vehículo a evaluar.

        Returns:
            Precio estimado de venta en euros.
        """
        if not vehicle.price or vehicle.price <= 0:
            return 0.0

        # Partir del precio de compra
        base_price = vehicle.price

        # Aplicar depreciación por antigüedad
        if vehicle.year:
            current_year = 2024
            age = current_year - vehicle.year

            if age in self.AGE_DEPRECIATION_RATES:
                depreciation = self.AGE_DEPRECIATION_RATES[age]
            elif age > 5:
                # Más de 5 años: 55% + 5% por año adicional
                depreciation = 0.55 + (age - 5) * 0.05
                # Limitar a 80% máximo de depreciación
                depreciation = min(depreciation, 0.80)
            else:
                depreciation = 0.0

            base_price = base_price * (1 - depreciation)

        # Ajustar por kilometraje
        if vehicle.mileage and vehicle.mileage > 0:
            # Depreciación adicional por kilometraje
            # Asumimos promedio de 15,000 km/año
            expected_mileage = max(0, (2024 - vehicle.year if vehicle.year else 0)) * 15000
            if vehicle.mileage > expected_mileage:
                excess_km = vehicle.mileage - expected_mileage
                mileage_penalty = (excess_km / 10000) * 0.02  # 2% por cada 10,000 km extra
                base_price = base_price * (1 - min(mileage_penalty, 0.15))  # Máximo 15% de penalización

        # Ajustar por marca (algunas marcas mantienen mejor el valor)
        brand_premium: dict[str, float] = {
            "porsche": 1.10,
            "mercedes-benz": 1.05,
            "bmw": 1.05,
            "audi": 1.03,
            "volkswagen": 1.00,
            "toyota": 1.08,
            "lexus": 1.10,
            "honda": 1.05,
        }

        if vehicle.brand:
            brand_lower = vehicle.brand.lower()
            if brand_lower in brand_premium:
                base_price = base_price * brand_premium[brand_lower]

        # Añadir margen de comercialización (10-15%)
        markup = 1.12  # 12% de margen
        estimated_price = base_price * markup

        return estimated_price

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
            current_year = 2024
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

    def _generate_recommendation(self, classification: str, profit_margin_percent: float, warnings: list[str]) -> str:
        """Genera una recomendación basada en la clasificación.

        Args:
            classification: Clasificación de la evaluación.
            profit_margin_percent: Margen de beneficio porcentual.
            warnings: Lista de advertencias.

        Returns:
            Recomendación en texto.
        """
        if classification == "verde":
            recommendation = "Vehículo recomendado para importación. El margen de beneficio es adecuado."
        elif classification == "amarillo":
            recommendation = "Vehículo con margen ajustado. Considerar negociar el precio de compra."
        else:
            recommendation = "Vehículo no recomendado. El margen de beneficio es insuficiente o negativo."

        if warnings:
            recommendation += f" Advertencias: {', '.join(warnings)}"

        return recommendation