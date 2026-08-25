"""SearchPersistenceService — persiste los resultados de una búsqueda.

Convierte los ``SearchResult`` del pipeline (VehicleSearchResult + análisis)
en registros de BD: ``vehicles``, ``vehicle_evaluations`` y ``opportunities``.
La búsqueda en background guarda así los vehículos encontrados para que el
dashboard los muestre al usuario sin volver a buscarlos (PERSONAL.NOAUTH).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import ACTIVE_STATUSES, Deal, DealStatus
from app.models.opportunity import Opportunity
from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation

logger = logging.getLogger(__name__)


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_text(values: list[Any] | None) -> str | None:
    if not values:
        return None
    return "\n".join(_stringify(v) for v in values if v is not None)


class SearchPersistenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def persist_engine_result(
        self,
        user_id: str,
        engine_result: Any,
    ) -> dict[str, Any]:
        """Persiste vehículos + evaluaciones + oportunidades de un resultado.

        Cada vehículo se procesa dentro de un savepoint (``begin_nested``) para
        que un fallo en evaluación/opportunidad **no** deshaga los vehículos
        ya flusheados con éxito en el mismo batch.

        Args:
            user_id: Dueño (en modo personal, el usuario local).
            engine_result: ``SearchEngineResult`` con ``results: list[SearchResult]``.

        Returns:
            dict con contadores (``saved``, ``created``, ``updated``) y
            ``links: dict[int, str]`` que mapea el índice de cada resultado al
            ``vehicle_id`` persistido. Permite al job vincular los vehículos a
            la orden sin volver a consultarlos por source/external_id (J3).
        """
        results = list(getattr(engine_result, "results", []) or [])
        saved = created = updated = 0
        links: dict[int, str] = {}
        failed = 0

        for idx, search_result in enumerate(results):
            dto = getattr(search_result, "vehicle", None)
            if dto is None:
                continue

            try:
                async with self.session.begin_nested():
                    vehicle = await self._upsert_vehicle(user_id, dto)
                    if vehicle is None:
                        continue
                    links[idx] = vehicle.id
                    saved += 1

                    await self._upsert_evaluation(vehicle.id, search_result)
                    opp = await self._upsert_opportunity(vehicle.id, search_result)
                    # Pipeline OPPORTUNITY→DEAL: auto-crea Deal en NEW si BUY y no existe activo
                    if opp is not None:
                        await self._ensure_deal(user_id, vehicle.id, opp)
            except Exception:
                failed += 1
                logger.warning(
                    "Failed to persist vehicle idx=%d, skipping",
                    idx,
                    exc_info=True,
                )
                continue

        await self.session.commit()
        if failed:
            logger.warning(
                "persist_engine_result: %d/%d vehicles failed in batch",
                failed,
                len(results),
            )
        return {
            "saved": saved,
            "created": created,
            "updated": updated,
            "links": links,
        }

    # ------------------------------------------------------------------
    # Vehículos
    # ------------------------------------------------------------------

    async def _upsert_vehicle(self, user_id: str, dto: Any) -> Vehicle | None:
        source = _stringify(getattr(dto, "source", None))
        external_id = _stringify(getattr(dto, "external_id", None))
        if not source or not external_id:
            return None

        result = await self.session.execute(
            select(Vehicle).where(
                Vehicle.source == source,
                Vehicle.external_id == external_id,
                Vehicle.user_id == str(user_id),
            )
        )
        vehicle = result.scalar_one_or_none()

        if vehicle is not None:
            self._apply_dto_fields(vehicle, dto)
            vehicle.updated_at = datetime.now(UTC)
            return vehicle

        vehicle = Vehicle(user_id=str(user_id), source=source, external_id=external_id)
        self._apply_dto_fields(vehicle, dto)
        self.session.add(vehicle)
        await self.session.flush()
        return vehicle

    @staticmethod
    def _apply_dto_fields(vehicle: Vehicle, dto: Any) -> None:
        mapping: dict[str, str] = {
            "url": "url",
            "brand": "brand",
            "model": "model",
            "category": "category",
            "version": "version",
            "year": "year",
            "mileage": "mileage",
            "fuel_type": "fuel_type",
            "transmission": "transmission",
            "power_hp": "power_hp",
            "displacement_cc": "displacement_cc",
            "doors": "doors",
            "color": "color",
            "emissions": "emissions",
            "location": "location",
            "seller_type": "seller_type",
            "first_registration": "first_registration",
            "price": "price",
            "currency": "currency",
            "vin": "vin",
            "description": "description",
        }
        for dto_attr, model_attr in mapping.items():
            value = getattr(dto, dto_attr, None)
            if value is not None:
                setattr(vehicle, model_attr, value)

        images = getattr(dto, "images", None)
        if images:
            vehicle.images = [str(i) for i in images if i]

        equipment = getattr(dto, "equipment", None)
        if equipment:
            vehicle.equipment = ",".join(_stringify(e) for e in equipment if e)

    # ------------------------------------------------------------------
    # Evaluaciones
    # ------------------------------------------------------------------

    async def _upsert_evaluation(self, vehicle_id: str, search_result: Any) -> None:
        result = await self.session.execute(
            select(VehicleEvaluation)
            .where(VehicleEvaluation.vehicle_id == vehicle_id)
            .order_by(VehicleEvaluation.created_at.desc())
            .limit(1)
        )
        evaluation = result.scalar_one_or_none()
        if evaluation is None:
            evaluation = VehicleEvaluation(vehicle_id=vehicle_id)
            self.session.add(evaluation)

        score = getattr(search_result, "vehicle_score", None)
        market = getattr(search_result, "market_estimation", None)
        profit = getattr(search_result, "profit_analysis", None)
        opportunity = getattr(search_result, "opportunity", None)
        negotiation = getattr(search_result, "negotiation", None)

        if market is not None:
            evaluation.estimated_market_price_es = (
                getattr(market, "market_price", None) or evaluation.estimated_market_price_es
            )
        if profit is not None:
            evaluation.estimated_import_cost = (
                getattr(profit, "total_cost", None) or evaluation.estimated_import_cost
            )
            evaluation.estimated_registration_cost = (
                getattr(profit, "registration_cost", None)
                or evaluation.estimated_registration_cost
            )
            evaluation.estimated_total_cost = (
                getattr(profit, "total_cost", None) or evaluation.estimated_total_cost
            )
            evaluation.estimated_profit = (
                getattr(profit, "net_profit", None) or evaluation.estimated_profit
            )
            evaluation.profit_margin_percent = (
                getattr(profit, "profit_margin_percentage", None)
                or evaluation.profit_margin_percent
            )
        if score is not None:
            evaluation.score = getattr(score, "score", None) or evaluation.score
            category_key = getattr(score, "category_key", None)
            category = getattr(score, "category", None)
            evaluation.classification = (
                _stringify(category_key)
                or _stringify(category)
                or evaluation.classification
            )
            weaknesses = getattr(score, "weaknesses", None)
            evaluation.warnings = _as_text(weaknesses) or evaluation.warnings
        if opportunity is not None:
            rec = getattr(opportunity, "recommendation", None)
            evaluation.recommendation = (
                rec.value if hasattr(rec, "value") else _stringify(rec)
            ) or evaluation.recommendation
        evaluation.negotiation = negotiation if negotiation is not None else evaluation.negotiation
        evaluation.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Oportunidades
    # ------------------------------------------------------------------

    async def _upsert_opportunity(self, vehicle_id: str, search_result: Any) -> Opportunity | None:
        opportunity = getattr(search_result, "opportunity", None)
        if opportunity is None:
            return None

        # Validate critical data before creating/updating opportunity
        if not self._validate_opportunity_data(vehicle_id, search_result, opportunity):
            logger.warning(
                "Skipping opportunity creation for vehicle %s: critical data missing",
                vehicle_id,
            )
            return None

        result = await self.session.execute(
            select(Opportunity)
            .where(Opportunity.vehicle_id == vehicle_id)
            .order_by(Opportunity.created_at.desc())
            .limit(1)
        )
        opp = result.scalar_one_or_none()
        if opp is None:
            opp = Opportunity(vehicle_id=vehicle_id)

        rec = getattr(opportunity, "recommendation", None)
        opp.opportunity_score = (
            getattr(opportunity, "overall_score", None) or opp.opportunity_score
        )
        opp.recommendation = (
            rec.value if hasattr(rec, "value") else _stringify(rec)
        ) or opp.recommendation
        opp.roi = getattr(opportunity, "roi", None) or opp.roi
        opp.risk = getattr(opportunity, "risk_level", None) or opp.risk
        opp.profit = getattr(opportunity, "estimated_profit", None) or opp.profit
        opp.analyzed_at = datetime.now(UTC)

        self.session.add(opp)
        await self.session.flush()
        return opp

    def _validate_opportunity_data(
        self, vehicle_id: str, search_result: Any, opportunity: Any
    ) -> bool:
        """Valida que los datos críticos estén presentes antes de persistir una oportunidad.

        Criterios:
        - El vehículo debe tener precio
        - El opportunity score debe ser un número válido
        - Debe haber recomendación
        - Debe haber nivel de riesgo
        - El beneficio y ROI deben estar calculados
        """
        # Validar que el vehículo tiene precio
        vehicle = getattr(search_result, "vehicle", None)
        if vehicle is None:
            logger.debug("Vehicle missing for vehicle_id=%s", vehicle_id)
            return False

        vehicle_price = getattr(vehicle, "price", None)
        if vehicle_price is None or vehicle_price <= 0:
            logger.debug("Vehicle price missing or invalid for vehicle_id=%s", vehicle_id)
            return False

        # Validar opportunity score
        overall_score = getattr(opportunity, "overall_score", None)
        if overall_score is None or not (0 <= overall_score <= 100):
            logger.debug("Invalid opportunity score for vehicle_id=%s: %s", vehicle_id, overall_score)
            return False

        # Validar recomendación
        recommendation = getattr(opportunity, "recommendation", None)
        if recommendation is None:
            logger.debug("Recommendation missing for vehicle_id=%s", vehicle_id)
            return False

        # Validar nivel de riesgo
        risk_level = getattr(opportunity, "risk_level", None)
        if risk_level is None:
            logger.debug("Risk level missing for vehicle_id=%s", vehicle_id)
            return False

        # Validar que el profit analysis tiene datos
        profit_analysis = getattr(search_result, "profit_analysis", None)
        if profit_analysis is None:
            logger.debug("Profit analysis missing for vehicle_id=%s", vehicle_id)
            return False

        roi = getattr(profit_analysis, "roi_percentage", None)
        net_profit = getattr(profit_analysis, "net_profit", None)
        if roi is None or net_profit is None:
            logger.debug("ROI or net_profit missing for vehicle_id=%s", vehicle_id)
            return False

        return True

    async def _ensure_deal(self, user_id: str, vehicle_id: str, opp: Opportunity) -> None:
        """Crea Deal NEW si la oportunidad es BUY y no existe Deal activo."""
        rec = (opp.recommendation or "").upper()
        # Soporta BUY, BUY_NOW, BUY_NOW con texto o enum
        is_buy = rec in {"BUY", "BUY_NOW"} or "BUY" in rec
        if not is_buy:
            return
        # Evitar duplicados: solo si no hay Deal activo para esta oportunidad
        from sqlalchemy import select as _select

        active_statuses = [s.value for s in ACTIVE_STATUSES]
        result = await self.session.execute(
            _select(Deal).where(
                Deal.user_id == str(user_id),
                Deal.opportunity_id == opp.id,
                Deal.status.in_(active_statuses),
            )
        )
        if result.scalar_one_or_none() is not None:
            return
        deal = Deal(
            user_id=str(user_id),
            vehicle_id=vehicle_id,
            opportunity_id=opp.id,
            status=DealStatus.NEW,
            notes=f"Auto-creado desde búsqueda: {opp.recommendation} (score {opp.opportunity_score})",
        )
        self.session.add(deal)
        await self.session.flush()
        logger.info("Deal auto-creado %s para opportunity %s (vehicle %s)", deal.id, opp.id, vehicle_id)
