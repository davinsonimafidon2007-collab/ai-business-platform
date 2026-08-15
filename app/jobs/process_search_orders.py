"""ProcessSearchOrdersJob — Ejecuta las órdenes de búsqueda en segundo plano.

Para cada ``SearchOrder`` PENDING/FAILED, corre el pipeline completo de
búsqueda (SearchEngineService), persiste los vehículos encontrados
(SearchPersistenceService) y los vincula a la orden con ``new_count`` para
que el frontend muestre el badge "X nuevos" (PERSONAL.NOAUTH).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.jobs.base import Job, JobContext, JobResult
from app.repositories.search_order_repository import SearchOrderRepository
from app.services.metrics_service import record_search_order_duration
from app.services.search_persistence import SearchPersistenceService

logger = get_logger(__name__)


class ProcessSearchOrdersJob(Job):
    """Job periódico que procesa las órdenes de búsqueda pendientes."""

    @property
    def name(self) -> str:
        return "process_search_orders"

    async def execute(self, context: JobContext) -> JobResult:
        logger = context.logger
        logger.info("Starting search orders processing...")

        try:
            async with context.db_manager.get_session() as session:
                order_repo = SearchOrderRepository(session)
                persistence = SearchPersistenceService(session)

                # Recovery: órdenes RUNNING huérfanas (crash/OOM/reinicio) se
                # reencolan a PENDING para reprocesarlas (AUDIT.PARALLEL.1).
                stale_minutes = int(getattr(settings, "search_order_stale_minutes", 15) or 0)
                recovered = 0
                if stale_minutes > 0:
                    stale_orders = await order_repo.stale_running_orders(stale_minutes)
                    for stale in stale_orders:
                        await order_repo.reset_to_pending(stale)
                        recovered += 1
                    if recovered:
                        logger.warning(
                            "Recovered %d stale RUNNING search order(s) back to PENDING",
                            recovered,
                        )

                orders = await order_repo.pending_orders(
                    limit=settings.search_orders_per_run,
                    max_attempts=int(
                        getattr(settings, "search_order_max_attempts", 5) or 0
                    ),
                    retry_cooldown_minutes=int(
                        getattr(settings, "search_order_retry_cooldown_minutes", 30)
                        or 0
                    ),
                )
                if not orders:
                    return JobResult(
                        success=True,
                        message=(
                            "No pending search orders"
                            + (f" ({recovered} recovered)" if recovered else "")
                        ),
                        data={"recovered": recovered},
                    )

                engine = self._build_search_engine(session)
                processed = 0
                completed = 0
                failed = 0
                skipped = 0
                total_found = 0

                for order in orders:
                    # Claim atómico: evita doble procesado si dos instancias
                    # del job corren a la vez (AUDIT.PARALLEL.1).
                    if not await order_repo.claim_order(order):
                        skipped += 1
                        continue
                    processed += 1

                    try:

                        start_ts = time.perf_counter()
                        domain_request = self._build_request(order)
                        engine_result = await engine.search(domain_request)

                        persist_info = await persistence.persist_engine_result(
                            user_id=order.user_id,
                            engine_result=engine_result,
                        )
                        # TASK-007: duración del procesado de la orden (histograma)
                        record_search_order_duration(time.perf_counter() - start_ts)
                        results = list(getattr(engine_result, "results", []) or [])
                        # persist_engine_result devuelve el vehicle_id por índice:
                        # vincula sin re-consultar por source/external_id (J3).
                        links = persist_info.get("links", {})

                        # Check only the batch's vehicle IDs instead of loading
                        # ALL IDs (AUDIT.PARALLEL.1 — badge optimization).
                        candidate_ids = set(links.values())
                        existing_ids = await order_repo.existing_vehicle_ids_batch(
                            order.id, candidate_ids
                        )

                        new_count = 0
                        unlinked = 0
                        for idx, search_result in enumerate(results):
                            vehicle_id = links.get(idx)
                            if vehicle_id is None:
                                # Sin source/external_id no se pudo persistir ni
                                # vincular: no contarlo como resultado de la orden.
                                unlinked += 1
                                continue
                            item_json = self._snapshot_item(search_result)
                            await order_repo.add_vehicle(
                                order, vehicle_id, seen=False, result_json=item_json
                            )
                            if vehicle_id not in existing_ids:
                                new_count += 1

                        if unlinked:
                            logger.warning(
                                "Order %s: %d result(s) without linkable vehicle "
                                "(missing source/external_id)",
                                order.id,
                                unlinked,
                            )

                        order.results_count = len(results) - unlinked
                        order.new_count = new_count
                        order.status = "COMPLETED"
                        order.error_message = None
                        order.last_run_at = datetime.now(UTC)
                        order.updated_at = datetime.now(UTC)
                        await order_repo.save(order)
                        completed += 1
                        total_found += order.results_count
                        logger.info(
                            "Search order %s completed: %d results (%d new)",
                            order.id,
                            order.results_count,
                            new_count,
                        )
                    except Exception as exc:
                        logger.exception("Search order %s failed", order.id)
                        order.status = "FAILED"
                        order.attempts = (order.attempts or 0) + 1
                        order.error_message = str(exc)[:2000]
                        order.last_run_at = datetime.now(UTC)
                        order.updated_at = datetime.now(UTC)
                        await order_repo.save(order)
                        failed += 1

                return JobResult(
                    success=failed == 0,
                    message=(
                        f"Processed {processed} search orders: {completed} completed, "
                        f"{failed} failed, {skipped} skipped (claimed elsewhere), "
                        f"{recovered} recovered, {total_found} vehicles found"
                    ),
                    data={
                        "processed": processed,
                        "completed": completed,
                        "failed": failed,
                        "skipped": skipped,
                        "recovered": recovered,
                        "found": total_found,
                    },
                )

        except Exception as exc:
            logger.exception("Search orders processing failed: %s", exc)
            return JobResult(
                success=False,
                message=f"Search orders processing failed: {exc}",
            )

    # ------------------------------------------------------------------

    def _build_search_engine(self, session: Any) -> Any:
        """Construye SearchEngineService con sus dependencias (mismo wiring que DI)."""
        from app.providers.autoscout24 import AutoScout24Provider
        from app.providers.autoscout24_es import AutoScout24EsProvider
        from app.providers.http_client import ProviderHttpClient
        from app.providers.mobile_de import MobileDeProvider
        from app.repositories.cached_market_repository import CachedMarketRepository
        from app.repositories.vehicle_repository import VehicleRepository
        from app.services.comparable_market_estimator import ComparableMarketEstimator
        from app.services.negotiation_engine import NegotiationEngine
        from app.services.opportunity_finder import OpportunityFinder
        from app.services.profit_analyzer import ProfitAnalyzer
        from app.services.search_engine import SearchEngineService
        from app.services.vehicle_scorer import VehicleScorer
        from app.services.vehicle_service import VehicleService

        vehicle_service = VehicleService(VehicleRepository(session))

        mobile_de_client = ProviderHttpClient(
            provider_name="mobile_de",
            base_url="https://suchen.mobile.de",
            timeout=settings.provider_http_timeout,
            max_retries=settings.provider_http_max_retries,
        )
        autoscout_client = ProviderHttpClient(
            provider_name="autoscout24",
            base_url="https://www.autoscout24.de",
            timeout=settings.provider_http_timeout,
            max_retries=settings.provider_http_max_retries,
        )
        autoscout_es_client = ProviderHttpClient(
            provider_name="autoscout24_es",
            base_url="https://www.autoscout24.es",
            timeout=settings.provider_http_timeout,
            max_retries=settings.provider_http_max_retries,
        )
        market_estimator = ComparableMarketEstimator(
            vehicle_service=vehicle_service,
            cached_market_repository=CachedMarketRepository(session),
        )
        return SearchEngineService(
            vehicle_service=vehicle_service,
            mobile_de_provider=MobileDeProvider(
                http_client=mobile_de_client,
                base_url="https://suchen.mobile.de",
            ),
            autoscout24_provider=AutoScout24Provider(
                http_client=autoscout_client,
                base_url="https://www.autoscout24.de",
            ),
            autoscout24_es_provider=AutoScout24EsProvider(
                http_client=autoscout_es_client,
                base_url="https://www.autoscout24.es",
            ),
            vehicle_scorer=VehicleScorer(),
            market_estimator=market_estimator,
            profit_analyzer=ProfitAnalyzer(),
            opportunity_finder=OpportunityFinder(),
            negotiation_engine=NegotiationEngine(),
            import_cost_profile=getattr(settings, "default_import_cost_profile", None),
        )

    def _build_request(self, order: Any) -> Any:
        from app.models.search import SearchRequest

        filters = order.filters_dict()
        query = order.query or filters.get("query") or "*"

        return SearchRequest(
            query=query,
            max_results=int(filters.get("max_results", 30)),
            providers=filters.get("providers")
            or [
                "mobile_de",
                "autoscout24",
                "autoscout24_es",
                "es_market_fixture",
                "coches_net_fixture",
            ],
            country=filters.get("country") or "ES",
            budget_max=order.max_purchase_price,
            brand=filters.get("brand"),
            model=filters.get("model"),
            min_year=filters.get("min_year"),
            max_year=filters.get("max_year"),
            min_mileage=filters.get("min_mileage"),
            max_mileage=filters.get("max_mileage"),
            fuel_type=filters.get("fuel_type"),
            transmission=filters.get("transmission"),
            comparable_providers=filters.get("comparable_providers"),
        )

    @staticmethod
    def _snapshot_item(search_result: Any) -> str | None:
        """Serializa el SearchResultItem del resultado para guardarlo como snapshot."""
        try:
            from app.api.v1.routes.search import _build_search_result_item

            return _build_search_result_item(search_result).model_dump_json()
        except Exception:  # noqa: BLE001 — snapshot is best-effort
            vehicle = getattr(search_result, "vehicle", None)
            ext_id = getattr(vehicle, "external_id", None) if vehicle is not None else None
            logger.exception(
                "No se pudo serializar el snapshot del resultado (external_id=%s)",
                ext_id,
            )
            return None
