"""ProcessSearchOrdersJob — Ejecuta las órdenes de búsqueda en segundo plano.

Para cada ``SearchOrder`` PENDING/FAILED, corre el pipeline completo de
búsqueda (SearchEngineService), persiste los vehículos encontrados
(SearchPersistenceService) y los vincula a la orden con ``new_count`` para
que el frontend muestre el badge "X nuevos" (PERSONAL.NOAUTH).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.jobs.base import Job, JobContext, JobResult
from app.repositories.search_order_repository import SearchOrderRepository
from app.services.search_persistence import SearchPersistenceService


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

                orders = await order_repo.pending_orders(limit=settings.search_orders_per_run)
                if not orders:
                    return JobResult(success=True, message="No pending search orders")

                engine = self._build_search_engine(session)
                processed = 0
                completed = 0
                failed = 0
                total_found = 0

                for order in orders:
                    order.status = "RUNNING"
                    order.updated_at = datetime.now(UTC)
                    await order_repo.save(order)
                    processed += 1

                    try:

                        existing_ids = {
                            v.vehicle_id
                            for v in await order_repo.list_order_vehicles(order.id, limit=10000)
                        }

                        domain_request = self._build_request(order)
                        engine_result = await engine.search(domain_request)

                        await persistence.persist_engine_result(
                            user_id=order.user_id,
                            engine_result=engine_result,
                        )
                        results = list(getattr(engine_result, "results", []) or [])

                        new_count = 0
                        for search_result in results:
                            dto = getattr(search_result, "vehicle", None)
                            vehicle_id = await self._find_vehicle_id(
                                session, order.user_id, dto
                            )
                            if vehicle_id is None:
                                continue
                            item_json = self._snapshot_item(search_result)
                            link = await order_repo.add_vehicle(
                                order, vehicle_id, seen=False, result_json=item_json
                            )
                            if vehicle_id not in existing_ids:
                                new_count += 1
                            session.add(link)

                        order.results_count = len(results)
                        order.new_count = new_count
                        order.status = "COMPLETED"
                        order.error_message = None
                        order.last_run_at = datetime.now(UTC)
                        order.updated_at = datetime.now(UTC)
                        await order_repo.save(order)
                        completed += 1
                        total_found += len(results)
                        logger.info(
                            "Search order %s completed: %d results (%d new)",
                            order.id,
                            len(results),
                            new_count,
                        )
                    except Exception as exc:
                        logger.exception("Search order %s failed", order.id)
                        order.status = "FAILED"
                        order.error_message = str(exc)[:2000]
                        order.last_run_at = datetime.now(UTC)
                        order.updated_at = datetime.now(UTC)
                        await order_repo.save(order)
                        failed += 1

                return JobResult(
                    success=failed == 0,
                    message=(
                        f"Processed {processed} search orders: {completed} completed, "
                        f"{failed} failed, {total_found} vehicles found"
                    ),
                    data={
                        "processed": processed,
                        "completed": completed,
                        "failed": failed,
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
            providers=filters.get("providers") or ["mobile_de", "autoscout24"],
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
        except Exception:
            return None

    async def _find_vehicle_id(self, session: Any, user_id: str, dto: Any) -> str | None:
        if dto is None:
            return None
        source = getattr(dto, "source", None)
        external_id = getattr(dto, "external_id", None)
        if not source or not external_id:
            return None
        from sqlalchemy import select

        from app.models.vehicle import Vehicle

        result = await session.execute(
            select(Vehicle.id).where(
                Vehicle.source == str(source),
                Vehicle.external_id == str(external_id),
                Vehicle.user_id == str(user_id),
            )
        )
        return result.scalar_one_or_none()
