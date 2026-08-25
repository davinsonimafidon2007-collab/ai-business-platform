"""Budget Search Agent — Busca vehículos según capital total disponible."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import BudgetSearchAgentInput, BudgetSearchAgentOutput
from app.config.import_costs import get_profile
from app.models.search import SearchRequest, SearchResult
from app.services.search_engine import SearchEngineService


class BudgetSearchAgent(BaseAgent[BudgetSearchAgentInput, BudgetSearchAgentOutput]):
    """Busca vehículos que encajen en un capital total del usuario.

    El usuario introduce su capital total (incluye compra + matriculación +
    viaje + costes de importación). La app calcula cuánto queda para el
    vehículo en sí y busca oportunidades reales con el SearchEngineService,
    filtrando por beneficio neto postventa mínimo (``profit_margin_min``).
    """

    name = "budget_search_agent"
    role = "search"
    description = (
        "Convierte capital total disponible en un precio máximo de compra "
        "(restando costes de importación) y ejecuta una búsqueda real acotada, "
        "filtrando por beneficio neto mínimo."
    )
    input_type = BudgetSearchAgentInput
    output_type = BudgetSearchAgentOutput
    default_timeout_seconds = 120.0

    def __init__(
        self,
        search_engine: SearchEngineService | None = None,
        profile_name: str = "SPAIN",
        timeout_seconds: float | None = None,
    ) -> None:
        """Args:
        search_engine: Motor de búsqueda (obligatorio en ``run`` si es None aquí).
        profile_name: Perfil de costes de importación (SPAIN, GERMANY...).

        Nota (AUDIT.AGENTS.1): se eliminaron los parámetros muertos
        ``search_agent``, ``profit_analyzer`` y ``opportunity_finder``, que se
        instanciaban y nunca se usaban.
        """
        super().__init__(timeout_seconds=timeout_seconds)
        self._search_engine = search_engine
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
        # Reservar un buffer para variables (impuestos + comisión + reparación).
        # Formula: budget = price + fixed_costs + price * (tax + commission + repair)
        # => price = (budget - fixed_costs) / (1 + tax + commission + repair)
        available = max(0.0, total_budget - fixed_costs)
        variable_buffer = 1.0 + (
            profile.tax_rate + profile.commission_rate + profile.repair_estimate_rate
        )
        return round(available / variable_buffer, 2)

    async def _execute(self, input_data: BudgetSearchAgentInput) -> BudgetSearchAgentOutput:
        engine = self._require_engine()
        max_price = self.calculate_max_purchase_price(input_data.total_budget)

        if max_price <= 0:
            return BudgetSearchAgentOutput(
                status="budget_too_low",
                total_budget=input_data.total_budget,
                max_purchase_price=max_price,
                query=input_data.query,
            )

        request = SearchRequest(
            query=input_data.query,
            max_results=input_data.max_results,
            budget_max=max_price,
            country=input_data.country,
        )
        engine_result = await engine.search(request)
        results, filtered_out = self._filter_by_min_profit(
            engine_result.results, input_data.profit_margin_min
        )

        return BudgetSearchAgentOutput(
            status="ok",
            total_budget=input_data.total_budget,
            max_purchase_price=max_price,
            query=input_data.query,
            results=results,
            summary=engine_result.summary,
            provider_issues=engine_result.provider_issues,
            filtered_out_count=filtered_out,
        )

    def _filter_by_min_profit(
        self,
        results: list[SearchResult],
        profit_margin_min: float,
    ) -> tuple[list[SearchResult], int]:
        """Aplica el filtro de beneficio neto mínimo (parametro antes muerto).

        Devuelve (resultados que pasan, cantidad descartada). Un resultado sin
        análisis de rentabilidad no se descarta (no se puede evaluar).
        """
        if profit_margin_min <= 0:
            return results, 0
        kept: list[SearchResult] = []
        discarded = 0
        for result in results:
            net_profit = getattr(result.profit_analysis, "net_profit", None)
            if net_profit is None or float(net_profit) >= profit_margin_min:
                kept.append(result)
            else:
                discarded += 1
        if discarded:
            self._logger.info(
                "BudgetSearchAgent descartó %d resultado(s) con beneficio < %.2f EUR",
                discarded,
                profit_margin_min,
            )
        return kept, discarded

    def _require_engine(self) -> SearchEngineService:
        if self._search_engine is None:
            raise ValueError(
                "No hay SearchEngineService disponible: la búsqueda por presupuesto "
                "requiere un motor de búsqueda real (inyéctalo o usa "
                "get_budget_search_agent() del DI)."
            )
        return self._search_engine
