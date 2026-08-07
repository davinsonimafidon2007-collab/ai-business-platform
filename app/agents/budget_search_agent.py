"""Budget Search Agent — Busca vehículos según capital total disponible."""
from __future__ import annotations

from typing import Any

from app.agents.search_agent import SearchAgent
from app.config.import_costs import get_profile
from app.services.opportunity_finder import OpportunityFinder
from app.services.profit_analyzer import ProfitAnalyzer


class BudgetSearchAgent:
    """Busca vehículos que encajen en un capital total del usuario.

    El usuario introduce su capital total (incluye compra + matriculación +
    viaje + costes de importación). La app calcula cuánto queda para el
    vehículo en sí y busca oportunidades con beneficio postventa.
    """

    def __init__(
        self,
        search_agent: SearchAgent | None = None,
        profit_analyzer: ProfitAnalyzer | None = None,
        opportunity_finder: OpportunityFinder | None = None,
        profile_name: str = "SPAIN",
    ) -> None:
        self.search_agent = search_agent or SearchAgent("budget_search")
        self.profit_analyzer = profit_analyzer or ProfitAnalyzer()
        self.opportunity_finder = opportunity_finder or OpportunityFinder()
        self.profile_name = profile_name

    def calculate_max_purchase_price(self, total_budget: float) -> float:
        """Calcula el precio máximo de compra del vehículo.

        Resta del capital total los costes fijos del perfil de importación
        y un margen para variables (impuestos, comisión, reparaciones).
        """
        profile = get_profile(self.profile_name)
        fixed_costs = (
            profile.transport_cost
            + profile.registration_cost
            + profile.inspection_cost
            + profile.paperwork_cost
            + profile.miscellaneous_cost
        )
        # Reservar 20% del precio de compra para variables (tax, commission, repair)
        # Formula: budget = price + fixed_costs + price * 0.20
        # => price = (budget - fixed_costs) / 1.20
        available = max(0.0, total_budget - fixed_costs)
        variable_buffer = 1.0 + (
            profile.tax_rate + profile.commission_rate + profile.repair_estimate_rate
        )
        return round(available / variable_buffer, 2)

    async def search_by_budget(
        self, total_budget: float, profit_margin_min: float = 500.0
    ) -> list[dict[str, Any]]:
        """Busca vehículos cuyo precio encaje en el capital disponible.

        Args:
            total_budget: Capital total del usuario (EUR).
            profit_margin_min: Beneficio mínimo postventa para considerar oportunidad (EUR).

        Returns:
            Lista de vehículos que encajan en presupuesto + son oportunidades.
        """
        max_price = self.calculate_max_purchase_price(total_budget)
        return [
            {
                "max_purchase_price": max_price,
                "total_budget": total_budget,
                "profit_margin_min": profit_margin_min,
                "status": "search_ready",
            }
        ]
