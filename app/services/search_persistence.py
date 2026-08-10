"""SearchPersistenceService — persiste los resultados de una búsqueda.

Convierte los ``SearchResult`` del pipeline (VehicleSearchResult + análisis)
en registros de BD: ``vehicles``, ``vehicle_evaluations`` y ``opportunities``.
La búsqueda en background guarda así los vehículos encontrados para que el
dashboard los muestre al usuario sin volver a buscarlos (PERSONAL.NOAUTH).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation


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

        for idx, search_result in enumerate(results):
            dto = getattr(search_result, "vehicle", None)
            if dto is None:
                continue

            vehicle = await self._upsert_vehicle(user_id, dto)
            if vehicle is None:
                continue
            links[idx] = vehicle.id
            saved += 1

            try:
                await self._upsert_evaluation(vehicle.id, search_result)
            except Exception:
                self.session.rollback()
                raise

            try:
                await self._upsert_opportunity(vehicle.id, search_result)
            except Exception:
                self.session.rollback()
                raise

        await self.session.commit()
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
            vehicle.images = ",".join(_stringify(i) for i in images if i)

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
                getattr(profit, "transport_cost", None)
                or evaluation.estimated_import_cost
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

    async def _upsert_opportunity(self, vehicle_id: str, search_result: Any) -> None:
        opportunity = getattr(search_result, "opportunity", None)
        if opportunity is None:
            return

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
