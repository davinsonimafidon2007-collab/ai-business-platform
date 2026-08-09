"""SearchOrderRepository — persistencia de órdenes de búsqueda (PERSONAL.NOAUTH)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_order import SearchOrder, SearchOrderVehicle


class SearchOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, order: SearchOrder) -> SearchOrder:
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_by_id(
        self, order_id: str | UUID, user_id: str | None = None
    ) -> SearchOrder | None:
        stmt = select(SearchOrder).where(SearchOrder.id == str(order_id))
        if user_id is not None:
            stmt = stmt.where(SearchOrder.user_id == str(user_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[SearchOrder]:
        result = await self.session.execute(
            select(SearchOrder)
            .where(SearchOrder.user_id == str(user_id))
            .order_by(SearchOrder.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def pending_orders(self, limit: int = 10) -> list[SearchOrder]:
        """Órdenes listas para procesar (PENDING o reintento de FAILED)."""
        result = await self.session.execute(
            select(SearchOrder)
            .where(SearchOrder.status.in_(["PENDING", "FAILED"]))
            .order_by(SearchOrder.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_vehicle(
        self,
        order: SearchOrder,
        vehicle_id: str,
        *,
        seen: bool = False,
        result_json: str | None = None,
    ) -> SearchOrderVehicle:
        """Vincula un vehículo a la orden (idempotente por par order+vehicle)."""
        existing = await self.session.execute(
            select(SearchOrderVehicle).where(
                SearchOrderVehicle.search_order_id == order.id,
                SearchOrderVehicle.vehicle_id == str(vehicle_id),
            )
        )
        link = existing.scalar_one_or_none()
        if link is not None:
            if result_json is not None:
                link.result_json = result_json
            return link
        link = SearchOrderVehicle(
            search_order_id=order.id,
            vehicle_id=str(vehicle_id),
            seen=seen,
            result_json=result_json,
        )
        self.session.add(link)
        return link

    async def list_order_vehicles(
        self, order_id: str | UUID, limit: int = 200
    ) -> list[SearchOrderVehicle]:
        result = await self.session.execute(
            select(SearchOrderVehicle)
            .where(SearchOrderVehicle.search_order_id == str(order_id))
            .order_by(SearchOrderVehicle.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_seen(self, order_id: str | UUID, user_id: str) -> None:
        """Marca como vistos todos los vehículos de la orden y resetea el badge."""
        order = await self.get_by_id(order_id, user_id=user_id)
        if order is None:
            return
        order.new_count = 0
        order.updated_at = datetime.now(UTC)
        await self.session.execute(
            update(SearchOrderVehicle)
            .where(SearchOrderVehicle.search_order_id == str(order_id))
            .values(seen=True)
        )
        await self.session.commit()

    async def save(self, order: SearchOrder) -> SearchOrder:
        order.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def delete(self, order: SearchOrder) -> None:
        await self.session.delete(order)
        await self.session.commit()

    async def total_new_by_user(self, user_id: str) -> int:
        """Suma de ``new_count`` de las órdenes del usuario (badge global)."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.coalesce(func.sum(SearchOrder.new_count), 0)).where(
                SearchOrder.user_id == str(user_id)
            )
        )
        return int(result.scalar() or 0)
