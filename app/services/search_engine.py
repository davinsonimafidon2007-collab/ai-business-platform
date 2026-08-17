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

from app.core.config import settings
from app.models.search import (
    SearchEngineResult,
    SearchRequest,
    SearchResult,
    SearchSummary,
)
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.autoscout24_es import AutoScout24EsProvider
from app.providers.mobile_de import MobileDeProvider
from app.providers.registry import ProviderRegistry
from app.services.market_estimator import MarketEstimator
from app.services.negotiation_engine import NegotiationEngine
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
        negotiation_engine: NegotiationEngine | None = None,
        orchestrator: SearchOrchestrator | None = None,
        provider_registry: type[ProviderRegistry] = ProviderRegistry,
        import_cost_profile: str | None = None,
        autoscout24_es_provider: AutoScout24EsProvider | None = None,
    ) -> None:
        """Inicializa el SearchEngineService con todas las dependencias.

        Args:
            vehicle_service: Servicio de vehículos para búsquedas.
            mobile_de_provider: Provider de mobile.de.
            autoscout24_provider: Provider de AutoScout24 (DE).
            vehicle_scorer: Motor de puntuación de vehículos.
            market_estimator: Estimador de mercado (implementa MarketEstimator protocol).
            profit_analyzer: Analizador de rentabilidad.
            opportunity_finder: Detector de oportunidades.
            negotiation_engine: Motor de estrategia de negociación (opcional).
            orchestrator: Orquestador de búsqueda (opcional, se crea uno por defecto).
            provider_registry: Registro de providers (clase, no instancia).
            autoscout24_es_provider: Provider de AutoScout24 España (opcional).
        """
        self._vehicle_service = vehicle_service
        self._mobile_de_provider = mobile_de_provider
        self._autoscout24_provider = autoscout24_provider
        self._autoscout24_es_provider = autoscout24_es_provider
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._negotiation_engine = negotiation_engine
        self._provider_registry = provider_registry
        self._import_cost_profile = (
            import_cost_profile
            or getattr(settings, "default_import_cost_profile", None)
            or "SPAIN"
        )

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
                negotiation_engine=self._negotiation_engine,
                provider_registry=self._provider_registry,
                import_cost_profile=self._import_cost_profile,
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

        # 3. Devolver resultado completo, incluidos los providers que fallaron
        #    (SEARCH.DIAG.1): sin esto, "0 resultados" y "todo caído" se ven
        #    igual desde fuera.
        return SearchEngineResult(
            summary=summary,
            results=results,
            provider_issues=self._orchestrator.last_provider_issues,
        )

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _register_providers(self) -> None:
        """Registra los providers en el ProviderRegistry.

        Es seguro llamar multiples veces: si un provider ya esta registrado,
        se omite (no se lanza excepcion).
        """
        registry = self._provider_registry

        # Registrar mobile_de si no esta ya registrado y está habilitado
        # (CRIT.001: opcional, requiere proxy residencial anti-bot).
        if getattr(settings, "enable_mobile_de", True):
            try:
                registry.get("mobile_de")
            except KeyError:
                registry.register(self._mobile_de_provider)

        # Registrar autoscout24 si no esta ya registrado
        try:
            registry.get("autoscout24")
        except KeyError:
            registry.register(self._autoscout24_provider)

        # Registrar autoscout24_es si enabled
        if getattr(settings, "enable_autoscout24_es", False):
            try:
                registry.get("autoscout24_es")
            except KeyError:
                if self._autoscout24_es_provider is not None:
                    registry.register(self._autoscout24_es_provider)
                else:
                    from app.providers.autoscout24_es import AutoScout24EsProvider
                    from app.providers.http_client import ProviderHttpClient

                    client = ProviderHttpClient(
                        provider_name="autoscout24_es",
                        base_url="https://www.autoscout24.es",
                        timeout=settings.provider_http_timeout,
                        max_retries=settings.provider_http_max_retries,
                    )
                    registry.register(
                        AutoScout24EsProvider(
                            http_client=client, base_url="https://www.autoscout24.es"
                        )
                    )

        # Asegurar fixtures ES (auto-registro por perfil SPAIN)
        registry.ensure_es_market_fixture()
        registry.ensure_coches_net_fixture()

