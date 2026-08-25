"""SearchOrchestrator — Coordinador del flujo completo de búsqueda, análisis y clasificación.

Este servicio NO contiene lógica de scoring, beneficio o mercado.
Únicamente COORDINA los servicios existentes mediante inyección de dependencias.

La lógica de análisis de cada vehículo (scoring → mercado → rentabilidad →
oportunidad → negociación) vive en ``SearchResultAnalyzer``; el orquestador
delega en él a través de ``_analyze_vehicle``.

Flujo:
    Providers
        │
        ▼
    VehicleService.search_from_provider(...)
        │
        ▼
    Resultados normalizados
        │
        ▼
    SearchResultAnalyzer.analyze()   (scoring / mercado / profit / opportunity / negotiation)
        │
        ▼
    filter / sort / summarize
        │
        ▼
    Lista ordenada de oportunidades
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.models.search import (
    ProviderIssue,
    SearchRequest,
    SearchResult,
    SearchSummary,
)
from app.providers.registry import ProviderRegistry
from app.services.negotiation_engine import NegotiationEngine
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityFinder,
    OpportunityLevel,
)
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_result_analyzer import SearchResultAnalyzer
from app.services.vehicle_scorer import VehicleScorer
from app.services.vehicle_service import VehicleService

logger = get_logger(__name__)


class _AnalysisOutcome:
    """Envoltorio del resultado de análisis: éxito o excepción registrada."""

    __slots__ = ("result",)

    def __init__(self, result: Any) -> None:
        self.result = result


class SearchOrchestrator:
    """Orquestador de búsqueda, análisis y clasificación de oportunidades.

    Dependencias inyectadas:
        - VehicleService: para buscar vehículos en providers.
        - VehicleScorer: para puntuar vehículos.
        - MarketEstimator: para estimar condiciones de mercado.
        - ProfitAnalyzer: para analizar rentabilidad.
        - OpportunityFinder: para detectar oportunidades.
        - ProviderRegistry: para resolver providers por nombre.

    El análisis por vehículo se delega en un :class:`SearchResultAnalyzer`,
    que se construye con las mismas dependencias inyectadas.
    """

    def __init__(
        self,
        vehicle_service: VehicleService,
        vehicle_scorer: VehicleScorer,
        market_estimator: Any,
        profit_analyzer: ProfitAnalyzer,
        opportunity_finder: OpportunityFinder,
        negotiation_engine: NegotiationEngine | None = None,
        provider_registry: type[ProviderRegistry] = ProviderRegistry,
        import_cost_profile: str | None = None,
    ) -> None:
        """Inicializa el orquestador con todas las dependencias.

        Args:
            vehicle_service: Servicio de vehículos para búsquedas.
            vehicle_scorer: Motor de puntuación de vehículos.
            market_estimator: Estimador de mercado (implementa MarketEstimator protocol).
            profit_analyzer: Analizador de rentabilidad.
            opportunity_finder: Detector de oportunidades.
            negotiation_engine: Motor de estrategia de negociación (opcional).
            provider_registry: Registro de providers (clase, no instancia).
            import_cost_profile: Perfil de costes de importación (default SPAIN).
        """
        self._vehicle_service = vehicle_service
        self._vehicle_scorer = vehicle_scorer
        self._market_estimator = market_estimator
        self._profit_analyzer = profit_analyzer
        self._opportunity_finder = opportunity_finder
        self._negotiation_engine = negotiation_engine or NegotiationEngine()
        self._provider_registry = provider_registry
        # Fallos de la última llamada a `search()` (SEARCH.DIAG.1).
        self._last_provider_issues: list[ProviderIssue] = []
        # SEARCH.ORCH.1: total de coincidencias antes de paginar.
        self._last_total_matches = 0
        # Semáforo para acotar análisis concurrentes (estimador de mercado
        # puede golpear providers externos).
        self._analysis_semaphore = asyncio.Semaphore(
            max(1, int(getattr(settings, "search_max_concurrent_analyses", 4) or 4))
        )
        self._import_cost_profile = (
            import_cost_profile
            or getattr(settings, "default_import_cost_profile", None)
            or "SPAIN"
        )
        self._analyzer = SearchResultAnalyzer(
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
            negotiation_engine=self._negotiation_engine,
            import_cost_profile=self._import_cost_profile,
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """Ejecuta una búsqueda completa sobre múltiples providers en paralelo.

        Fases (SEARCH.ORCH.1):
            1. Resuelve providers del registry (fallos → ProviderIssue).
            2. Lanza los fetch de todos los providers CONCURRENTEMENTE con
               timeout por provider (``settings.search_provider_timeout``).
               Un provider que falla o expira NO aborta los demás.
            3. Analiza los DTOs con concurrencia acotada (semáforo),
               preservando el orden determinista (providers en el orden de la
               petición, DTOs en el orden devuelto).
            4. Dedup cross-source e intra-source.
            5. Ordena por ``request.sort_by``/``sort_order`` y pagina con
               ``offset``/``max_results``.

        Args:
            request: Parámetros de la búsqueda.

        Returns:
            Lista de SearchResult ordenada y paginada.
        """
        # SEARCH.DIAG.1: se acumulan los fallos en vez de tragarlos, para que
        # la capa superior pueda distinguir "no hay coches" de "el provider
        # se cayó". Un fallo sigue sin abortar la búsqueda.
        self._last_provider_issues = []
        self._last_total_matches = 0

        if not request.providers:
            return []

        # --- Fase 1: resolver providers ---
        resolved: list[tuple[str, Any]] = []
        for provider_name in request.providers:
            try:
                resolved.append((provider_name, self._provider_registry.get(provider_name)))
            except KeyError as exc:
                logger.warning("Provider no registrado: %s", provider_name)
                self._last_provider_issues.append(
                    ProviderIssue(
                        provider=provider_name,
                        stage="registry",
                        error_type=type(exc).__name__,
                        message=f"Provider '{provider_name}' no está registrado",
                    )
                )

        if not resolved:
            return []

        # --- Fase 2: fetch concurrente con timeout por provider ---
        fetch_results = await asyncio.gather(
            *(
                self._fetch_provider(provider_name, provider, request)
                for provider_name, provider in resolved
            )
        )

        # Aplanar preservando el orden determinista: providers según la
        # petición, DTOs según el orden devuelto por cada uno.
        pending: list[tuple[str, Any]] = []
        for (provider_name, dtos) in fetch_results:
            if isinstance(dtos, BaseException):
                continue  # ya registrado como ProviderIssue en _fetch_provider
            for dto in dtos:
                if self._matches_filters(dto, request):
                    pending.append((provider_name, dto))

        if not pending:
            self._last_total_matches = 0
            return []

        # --- Fase 3: análisis concurrente acotado ---
        analyzed = await asyncio.gather(
            *(
                self._analyze_safe(provider_name, dto, request)
                for provider_name, dto in pending
            )
        )

        all_results: list[SearchResult] = []
        for item in analyzed:
            if isinstance(item.result, BaseException):
                continue  # ya registrado como ProviderIssue(stage="analyze")
            all_results.append(item.result)

        # --- Fase 4: dedup cross-source e intra-source ---
        deduped = self._dedup_autoscout24_cross_source(all_results)

        seen_keys: set[tuple[str, str]] = set()
        final_deduped: list[SearchResult] = []
        for r in deduped:
            vehicle = r.vehicle
            source = getattr(vehicle, "source", None) or ""
            ext_id = getattr(vehicle, "external_id", None)
            url = getattr(vehicle, "url", None)
            key: tuple[str, str] | None
            if ext_id:
                key = (source, ext_id)
            elif url:
                key = (source, url)
            else:
                key = None
            if key is None or key not in seen_keys:
                if key is not None:
                    seen_keys.add(key)
                final_deduped.append(r)

        # Total ANTES de paginar, para que el cliente pueda paginar sin perder
        # la noción de cuántos resultados hay.
        self._last_total_matches = len(final_deduped)

        # --- Fase 5: ordenar primero y paginar después ---
        ordered = self.sort(
            final_deduped,
            by=request.sort_by,
            reverse=request.sort_order != "asc",
        )
        if request.max_results > 0:
            ordered = ordered[request.offset : request.offset + request.max_results]
        elif request.offset > 0:
            ordered = ordered[request.offset :]
        return ordered

    async def _fetch_provider(
        self,
        provider_name: str,
        provider: Any,
        request: SearchRequest,
    ) -> tuple[str, list[Any]]:
        """Descarga los DTOs de un provider con timeout global.

        Nunca propaga excepciones: devuelve el nombre y los DTOs, o el nombre
        y la excepción (registrada antes como ProviderIssue) para que el
        resto de providers siga vivo.

        Raises:
            Nada. Los errores viajan dentro del valor devuelto.
        """
        kwargs: dict[str, Any] = {}
        if request.country:
            kwargs["country"] = request.country
        if request.budget_min is not None:
            kwargs["budget_min"] = request.budget_min
        if request.budget_max is not None:
            kwargs["budget_max"] = request.budget_max

        timeout = float(getattr(settings, "search_provider_timeout", 60.0) or 0)
        coro = self._vehicle_service.search_from_provider(provider, request.query, **kwargs)
        try:
            if timeout > 0:
                dtos = await asyncio.wait_for(coro, timeout=timeout)
            else:
                dtos = await coro
        except TimeoutError as exc:
            logger.error(
                "Timeout (%.1fs) del provider %s durante la búsqueda",
                timeout,
                provider_name,
            )
            self._last_provider_issues.append(
                ProviderIssue(
                    provider=provider_name,
                    stage="search",
                    error_type="TimeoutError",
                    message=(
                        f"El provider '{provider_name}' tardó más de {timeout:.0f}s "
                        "en responder"
                    ),
                )
            )
            return provider_name, exc
        except Exception as exc:  # noqa: BLE001 — multi-provider: must continue
            logger.exception("Error al buscar en provider %s", provider_name)
            self._last_provider_issues.append(
                ProviderIssue(
                    provider=provider_name,
                    stage="search",
                    error_type=type(exc).__name__,
                    message=str(exc) or type(exc).__name__,
                )
            )
            return provider_name, exc
        return provider_name, list(dtos or [])

    async def _analyze_safe(
        self,
        provider_name: str,
        dto: Any,
        request: SearchRequest,
    ) -> _AnalysisOutcome:
        """Analiza un DTO bajo semáforo sin propagar excepciones.

        Devuelve un ``_AnalysisOutcome`` con el ``SearchResult`` o la
        excepción registrada como ProviderIssue(stage="analyze"). El semáforo
        acota cuántos análisis (y por tanto estimaciones de mercado contra
        providers externos) corren a la vez.
        """
        async with self._analysis_semaphore:
            try:
                result = await self._analyze_vehicle(
                    dto,
                    comparable_providers=getattr(request, "comparable_providers", None),
                )
                return _AnalysisOutcome(result)
            except Exception as exc:  # noqa: BLE001 — analysis can raise diverse errors
                external_id = getattr(dto, "external_id", None)
                logger.exception("Error al analizar vehículo %s", external_id or "unknown")
                self._last_provider_issues.append(
                    ProviderIssue(
                        provider=provider_name,
                        stage="analyze",
                        error_type=type(exc).__name__,
                        message=str(exc) or type(exc).__name__,
                        external_id=str(external_id) if external_id else None,
                    )
                )
                return _AnalysisOutcome(exc)

    @property
    def last_total_matches(self) -> int:
        """Total de coincidencias (post-dedup, pre-paginación) de la última ``search()``."""
        return self._last_total_matches

    @property
    def last_provider_issues(self) -> list[ProviderIssue]:
        """Fallos de providers de la última ``search()`` (SEARCH.DIAG.1).

        Lista vacía = todos los providers respondieron. Se resetea en cada
        ``search()``.
        """
        return list(self._last_provider_issues)

    @staticmethod
    def summarize(results: list[SearchResult]) -> SearchSummary:
        """Genera un resumen de los resultados agrupados por nivel de oportunidad.

        Args:
            results: Lista de resultados a resumir.

        Returns:
            SearchSummary con los conteos por categoría.
        """
        summary = SearchSummary(total_results=len(results))

        for r in results:
            opportunity = r.opportunity
            if not isinstance(opportunity, OpportunityAnalysis):
                summary.rejected += 1
                continue

            level = opportunity.opportunity_level
            if level == OpportunityLevel.EXCELLENT:
                summary.excellent += 1
            elif level == OpportunityLevel.GOOD:
                summary.good += 1
            elif level == OpportunityLevel.AVERAGE:
                summary.average += 1
            elif level == OpportunityLevel.POOR:
                summary.poor += 1
            else:
                summary.rejected += 1

        return summary

    @staticmethod
    def top(results: list[SearchResult], n: int = 10) -> list[SearchResult]:
        """Devuelve los N mejores resultados (ya deben estar ordenados).

        Args:
            results: Lista de resultados ordenados.
            n: Número de resultados a devolver.

        Returns:
            Lista con los primeros N resultados.
        """
        return results[:n]

    @staticmethod
    def filter(
        results: list[SearchResult],
        *,
        recommendation: str | None = None,
        opportunity_level: str | None = None,
        risk_level: str | None = None,
    ) -> list[SearchResult]:
        """Filtra los resultados por recomendación, nivel de oportunidad o riesgo.

        Args:
            results: Lista de resultados a filtrar.
            recommendation: Recomendación (BUY_NOW, WATCH, NEGOTIATE, REJECT).
            opportunity_level: Nivel de oportunidad (EXCELLENT, GOOD, AVERAGE, POOR, REJECT).
            risk_level: Nivel de riesgo (LOW, MEDIUM, HIGH).

        Returns:
            Lista filtrada de resultados.
        """
        filtered: list[SearchResult] = []

        for r in results:
            opp = r.opportunity
            profit = r.profit_analysis

            if recommendation is not None:
                opp_rec = getattr(opp, "recommendation", None)
                rec_value = opp_rec.value if hasattr(opp_rec, "value") else str(opp_rec or "")
                if rec_value.upper() != recommendation.upper():
                    continue

            if opportunity_level is not None:
                opp_level = getattr(opp, "opportunity_level", None)
                level_value = opp_level.value if hasattr(opp_level, "value") else str(opp_level or "")
                if level_value.upper() != opportunity_level.upper():
                    continue

            if risk_level is not None:
                profit_risk = getattr(profit, "risk_level", None)
                risk_value = profit_risk.value if hasattr(profit_risk, "value") else str(profit_risk or "")
                if risk_value.upper() != risk_level.upper():
                    continue

            filtered.append(r)

        return filtered

    @staticmethod
    def sort(
        results: list[SearchResult],
        *,
        by: str = "score",
        reverse: bool = True,
    ) -> list[SearchResult]:
        """Ordena los resultados por un campo determinado.

        Args:
            results: Lista de resultados a ordenar.
            by: Campo por el que ordenar (score, ROI, beneficio, precio, kilómetros, año).
            reverse: True para orden descendente, False para ascendente.

        Returns:
            Lista ordenada de resultados.
        """
        def _sort_key(r: SearchResult) -> tuple[float, float, float, float]:
            """Genera clave de ordenación por defecto.

            Orden por defecto:
                1. Opportunity Score DESC
                2. ROI DESC
                3. Beneficio DESC
                4. Vehicle Score DESC
            """
            opp = r.opportunity
            profit = r.profit_analysis
            vs = r.vehicle_score

            opp_score = getattr(opp, "overall_score", 0.0) or 0.0
            roi = getattr(profit, "roi_percentage", 0.0) or 0.0
            net_profit = getattr(profit, "net_profit", 0.0) or 0.0
            vehicle_score = getattr(vs, "score", 0) or 0

            return (opp_score, roi, net_profit, float(vehicle_score))

        if reverse:
            results_sorted = sorted(results, key=_sort_key, reverse=True)
        else:
            results_sorted = sorted(results, key=_sort_key)

        # Si se especifica un campo distinto, reordenar
        if by != "score":
            # SEARCH.ORCH.1: alias EN/canónicos → claves soportadas.
            # Claves desconocidas caen al orden por defecto (score DESC) en
            # vez de ordenar todas por 0.0 (orden arbitrario).
            sort_map: dict[str, list[str]] = {
                "roi": ["roi_percentage", "roi"],
                "roi_percentage": ["roi_percentage", "roi"],
                "beneficio": ["net_profit", "estimated_profit"],
                "profit": ["net_profit", "estimated_profit"],
                "net_profit": ["net_profit", "estimated_profit"],
                "precio": ["purchase_price", "price"],
                "price": ["purchase_price", "price"],
                "kilómetros": ["mileage"],
                "kilometros": ["mileage"],
                "mileage": ["mileage"],
                "año": ["year"],
                "ano": ["year"],
                "year": ["year"],
            }
            attr_names = (
                sort_map.get(by.strip().lower(), None) if by else None
            )
            if attr_names is None:
                logger.debug("sort_by='%s' no soportado; se usa score DESC", by)
                return results_sorted

            def _alt_sort_key(r: SearchResult) -> float:
                opp = r.opportunity
                profit = r.profit_analysis
                vs = r.vehicle_score
                vehicle = r.vehicle

                # Buscar el primer atributo numérico real entre profit,
                # vehicle, opp y vehicle_score (MagicMocks autogenerados se
                # ignoran para no romper la ordenación).
                for attr_name in attr_names:
                    for obj in (profit, vehicle, opp, vs):
                        candidate = getattr(obj, attr_name, None)
                        if isinstance(candidate, bool):
                            continue
                        if isinstance(candidate, (int, float)):
                            return float(candidate)
                        if isinstance(candidate, str):
                            try:
                                return float(candidate.replace(",", "."))
                            except ValueError:
                                continue
                return 0.0

            results_sorted = sorted(results_sorted, key=_alt_sort_key, reverse=reverse)

        return results_sorted

    # ------------------------------------------------------------------
    # Dedup cross-source AutoScout24
    # ------------------------------------------------------------------

    # Providers que comparten external_id entre países (AutoScout24 global)
    _CROSS_SOURCE_FAMILIES: dict[str, set[str]] = {
        "autoscout24": {"autoscout24", "autoscout24_es"},
        "autoscout24_es": {"autoscout24", "autoscout24_es"},
    }

    @classmethod
    def _dedup_autoscout24_cross_source(
        cls, results: list[SearchResult]
    ) -> list[SearchResult]:
        """Detecta duplicados cross-source dentro de la familia AutoScout24.

        AutoScout24 usa el mismo ``external_id`` en todos los países.
        Si aparece el mismo ID en autoscout24 (DE) y autoscout24_es (ES),
        se conserva la versión ES (más relevante para el mercado español)
        y se descarta la DE.

        Returns:
            Lista filtrada manteniendo ES sobre DE para duplicados.
        """
        # Indexar por external_id, agrupando todas las fuentes
        by_ext_id: dict[str, list[SearchResult]] = {}
        no_ext_id: list[SearchResult] = []

        for r in results:
            ext_id = getattr(r.vehicle, "external_id", None)
            source = getattr(r.vehicle, "source", None) or ""
            if ext_id and source in cls._CROSS_SOURCE_FAMILIES:
                by_ext_id.setdefault(ext_id, []).append(r)
            else:
                no_ext_id.append(r)

        deduped: list[SearchResult] = []
        for _ext_id, candidates in by_ext_id.items():
            if len(candidates) == 1:
                deduped.append(candidates[0])
                continue

            # Preferir ES sobre DE para el mismo external_id
            preferred = None
            for c in candidates:
                src = getattr(c.vehicle, "source", None) or ""
                if src == "autoscout24_es":
                    preferred = c
                    break
            if preferred is None:
                preferred = candidates[0]

            # Tag con todos los sources donde apareció (trazabilidad)
            sources_seen = {
                s
                for c in candidates
                if (s := getattr(c.vehicle, "source", None)) is not None
            }
            preferred.vehicle.available_in_sources = sorted(sources_seen)
            deduped.append(preferred)

        return deduped + no_ext_id

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_filters(dto: Any, request: SearchRequest) -> bool:
        """Indica si un DTO cumple todos los filtros de la solicitud (CODE-001).

        Comportamiento idéntico al filtrado inline previo: si un filtro aplica
        y el DTO no lo cumple, se descarta. Si el filtro no aplica (None),
        no restringe.
        """
        # Presupuesto
        if request.budget_min is not None and (dto.price is None or dto.price < request.budget_min):
            return False
        if request.budget_max is not None and (dto.price is None or dto.price > request.budget_max):
            return False

        # Marca / modelo / año / km / combustible / transmisión
        if request.brand is not None and (dto.brand is None or dto.brand.lower() != request.brand.lower()):
            return False
        if request.model is not None and (dto.model is None or request.model.lower() not in dto.model.lower()):
            return False
        if request.min_year is not None and (dto.year is None or dto.year < request.min_year):
            return False
        if request.max_year is not None and (dto.year is None or dto.year > request.max_year):
            return False
        if request.min_mileage is not None and (dto.mileage is None or dto.mileage < request.min_mileage):
            return False
        if request.max_mileage is not None and (dto.mileage is None or dto.mileage > request.max_mileage):
            return False
        if request.fuel_type is not None and (dto.fuel_type is None or dto.fuel_type.lower() != request.fuel_type.lower()):
            return False
        if request.transmission is not None and (dto.transmission is None or dto.transmission.lower() != request.transmission.lower()):
            return False

        return True

    async def _analyze_vehicle(
        self,
        vehicle: Any,
        *,
        comparable_providers: list[str] | None = None,
    ) -> SearchResult:
        """Ejecuta el pipeline completo de análisis sobre un vehículo.

        Wrapper fino: delega en ``SearchResultAnalyzer`` (donde vive la
        lógica de scoring/mercado/rentabilidad/oportunidad/negociación).

        Args:
            vehicle: DTO del vehículo (VehicleSearchResult).
            comparable_providers: Allowlist opcional de sources para el
                estimador de mercado (comparables).

        Returns:
            SearchResult con todos los análisis.
        """
        return await self._analyzer.analyze(
            vehicle,
            comparable_providers=comparable_providers,
        )
