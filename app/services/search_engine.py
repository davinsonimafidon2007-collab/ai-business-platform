"""SearchEngineService — Servicio principal de búsqueda end-to-end.

Es el punto de entrada único de la aplicación para ejecutar búsquedas
completas de vehículos a través de múltiples providers.

Flujo:
    1. Recibe un SearchRequest
    2. Ejecuta el SearchOrchestrator con los providers registrados
    3. Devuelve un SearchEngineResult con el resumen y los resultados

NO contiene lógica de negocio duplicada. Todo el pipeline de análisis
(scoring, mercado, beneficio, oportunidad) se delega en SearchOrchestrator
y sus servicios inyectados.

Arquitectura:
    - Inyección de dependencias en el constructor
    - Configuración centralizada de providers
    - Sin lógica duplicada
    - SOLID: responsabilidad única (orquestar la búsqueda de alto nivel)
"""

from __future__ import annotations

from typing import Any

from app.models.search import (
    SearchEngineResult,
    SearchRequest,
    SearchResult,
    SearchSummary,
)
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.mobile_de import MobileDeProvider
from app.providers.registry import ProviderRegistry
from app.services.market_estimator import MarketEstimator
from app.services.opportunity_finder import OpportunityFinder
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_orchestrator import SearchOrchestrator
from app.services.vehicle_scorer import VehicleScorer
from app.services.vehicle_service import VehicleService


class SearchEngineService:
    """Servicio principal de búsqueda end-to-end.

    Es el facade de alto nivel que coordina providers, orquestador
    y servicios de análisis.

    Uso:
        engine = SearchEngineService(
            vehicle_service=vehicle_service,
            mobile_de_provider=mobile_de,
            autoscout24_provider=autoscout24,
            vehicle_scorer=scorer,
            market_estimator=estimator,
            profit_analyzer=analyzer,
            opportunity_finder=finder,
        )
        result = await engine.search(request)
        print(result.summary)
    """

    def __init__(
        self,
        vehicle_service: VehicleService,
        mobile_de_provider: MobileDeProvider,
        autoscout24_provider: AutoScout24Provider,
        vehicle_scorer: VehicleScorer,
        market_estimator: MarketEstimator,
        profit_analyzer: ProfitAnalyzer,
        opportunity_finder: OpportunityFinder,
        orchestrator: SearchOrchestrator | None = None,
        provider_registry: type[ProviderRegistry] = ProviderRegistry,
    ) -> None:
        """Inicializa el SearchEngineService con todas las dependencias.

        Args:
            vehicle_service: Servicio de vehículos para búsquedas.
            mobile_de_provider: Provider de mobile.de.
            autoscout24_provider: Provider de AutoScout24.
            vehicle_scorer: Motor de puntuación de vehículos.
            market_estimator: Estimador de mercado (implementa MarketEstimator protocol).
            profit_analyzer: Analizador de rentabilidad.
            opportunity_finder: Detector de oportunidades.
            orchestrator: Orquestador de búsqueda (opcional, se crea uno por defecto).
            provider_registry: Registro de providers (clase, no instancia).
        """
        self._vehicle_service = vehicle_service
        self._mobile_de_provider = mobile_de_provider
        self._autoscout24_provider = autoscout24_provider
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._provider_registry = provider_registry

        # Registrar providers una sola vez durante la inicialización
        self._register_providers()

        # Crear orquestador si no se proporciona
        if orchestrator is not None:
            self._orchestrator = orchestrator
        else:
            self._orchestrator = SearchOrchestrator(
                vehicle_service=self._vehicle_service,
                vehicle_scorer=self._vehicle_scorer,
                market_estimator=self._market_estimator,
                profit_analyzer=self._profit_analyzer,
                opportunity_finder=self._opportunity_finder,
                provider_registry=self._provider_registry,
            )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def search(self, request: SearchRequest) -> SearchEngineResult:
        """Ejecuta una búsqueda completa y devuelve los resultados analizados.

        Args:
            request: Parámetros de la búsqueda.

        Returns:
            SearchEngineResult con el resumen y la lista completa de resultados.
        """
        # 1. Ejecutar el orquestador (pipeline completo)
        results: list[SearchResult] = await self._orchestrator.search(request)

        # 2. Generar resumen a partir de los resultados
        summary: SearchSummary = self._orchestrator.summarize(results)

        # 3. Devolver resultado completo
        return SearchEngineResult(
            summary=summary,
            results=results,
        )

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _register_providers(self) -> None:
        """Registra los providers en el ProviderRegistry.

        Es seguro llamar múltiples veces: si un provider ya está registrado,
        se omite (no se lanza excepción).
        """
        registry = self._provider_registry

        # Registrar mobile_de si no está ya registrado
        try:
            registry.get("mobile_de")
        except KeyError:
            registry.register(self._mobile_de_provider)

        # Registrar autoscout24 si no está ya registrado
        try:
            registry.get("autoscout24")
        except KeyError:
            registry.register(self._autoscout24_provider)

