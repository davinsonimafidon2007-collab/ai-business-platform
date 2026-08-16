"""SearchOrderRepository — persistencia de órdenes de búsqueda (PERSONAL.NOAUTH)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limits import clamp_limit, clamp_skip
from app.models.search_order import SearchOrder, SearchOrderVehicle


class SearchOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, order: SearchOrder) -> SearchOrder:
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def count_active_by_user(self, user_id: str) -> int:
        """Órdenes activas del usuario (PENDING/RUNNING/FAILED) (P3).

        Estas son las que consumen capacidad del job (las COMPLETED no).
        Sin tope, un usuario encola cientos de búsquedas que el job procesa
        una a una contra providers live.
        """
        result = await self.session.execute(
            select(func.count(SearchOrder.id)).where(
                SearchOrder.user_id == str(user_id),
                SearchOrder.status.in_(["PENDING", "RUNNING", "FAILED"]),
            )
        )
        return int(result.scalar() or 0)

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
        skip = clamp_skip(skip)
        limit = clamp_limit(limit)
        result = await self.session.execute(
            select(SearchOrder)
            .where(SearchOrder.user_id == str(user_id))
            .order_by(SearchOrder.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def pending_orders(
        self,
        limit: int = 10,
        max_attempts: int = 5,
        retry_cooldown_minutes: int = 30,
    ) -> list[SearchOrder]:
        """Órdenes listas para procesar (J1).

        - PENDING: siempre.
        - FAILED: solo si ``attempts < max_attempts`` y pasó el cooldown desde
          ``last_run_at``. Sin esto, un fallo permanente de provider (403, etc.)
          se reintentaba en cada ciclo del job sin límite ni backoff.
        """
        stmt = select(SearchOrder).where(
            or_(
                SearchOrder.status == "PENDING",
                and_(
                    SearchOrder.status == "FAILED",
                    SearchOrder.attempts < max_attempts,
                    or_(
                        SearchOrder.last_run_at.is_(None),
                        SearchOrder.last_run_at
                        < datetime.now(UTC)
                        - timedelta(minutes=retry_cooldown_minutes),
                    ),
                ),
            )
        )
        stmt = stmt.order_by(SearchOrder.created_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def stale_running_orders(
        self, stale_minutes: int, limit: int = 100
    ) -> list[SearchOrder]:
        """Órdenes RUNNING que no se actualizan hace ``stale_minutes`` min.

        Un proceso puede morir a mitad de procesar una orden (crash, OOM,
        reinicio) y dejar la orden en RUNNING para siempre. Estas son
        candidatas a recuperación: se resetean a PENDING para reprocesar.
        """
        # Cutoff aware UTC, igual que los writes (datetime.now(UTC)). Antes se
        # usaba un cutoff naive, inconsistente con el valor aware que escribe
        # claim_order/save; en Postgres/timestamptz eso era no determinista (J2).
        cutoff = datetime.now(UTC) - timedelta(minutes=stale_minutes)
        result = await self.session.execute(
            select(SearchOrder)
            .where(
                SearchOrder.status == "RUNNING",
                SearchOrder.updated_at < cutoff,
            )
            .order_by(SearchOrder.updated_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def claim_order(self, order: SearchOrder) -> bool:
        """Claim atómico de una orden para evitar doble procesado (race).

        Transición PENDING/FAILED -> RUNNING con un UPDATE condicional.
        Si otra instancia del job ya la reclamó (status != PENDING/FAILED),
        el UPDATE no toca filas y devolvemos False: no procesar dos veces.
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(SearchOrder)
            .where(
                SearchOrder.id == str(order.id),
                SearchOrder.status.in_(["PENDING", "FAILED"]),
            )
            .values(
                status="RUNNING",
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        if result.rowcount == 0:
            return False
        await self.session.refresh(order)
        return True

    async def reset_to_pending(self, order: SearchOrder) -> None:
        """Devuelve una orden RUNNING huérfana a PENDING (recovery)."""
        order.status = "PENDING"
        order.error_message = (
            f"Reencolada tras quedarse en RUNNING (stale). "
            f"Último error: {order.error_message or 'ninguno'}"
        )[:2000]
        order.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)

    async def recover_all_running(self) -> int:
        """Reencola TODAS las órdenes RUNNING -> PENDING (arranque de la app).

        Al boot no puede haber workers procesando; cualquier orden RUNNING es
        un resto de un proceso anterior (crash/reinicio). A diferencia de
        ``stale_running_orders``, no aplica umbral de antigüedad: se recuperan
        todas de inmediato (TASK-009).
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(SearchOrder)
            .where(SearchOrder.status == "RUNNING")
            .values(
                status="PENDING",
                error_message="Reencolada al arrancar la app (quedó en RUNNING)",
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return result.rowcount

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

    async def vehicle_ids_for_order(self, order_id: str | UUID) -> set[str]:
        """IDs de vehículos ya vinculados a la orden (para calcular ``new_count``).

        Devuelve TODOS los ids, sin límite de página: el badge de "nuevos"
        depende de este conjunto completo (J6).
        """
        result = await self.session.execute(
            select(SearchOrderVehicle.vehicle_id).where(
                SearchOrderVehicle.search_order_id == str(order_id)
            )
        )
        return set(result.scalars().all())

    async def existing_vehicle_ids_batch(
        self, order_id: str | UUID, candidate_ids: set[str]
    ) -> set[str]:
        """Solo los ``candidate_ids`` que ya están vinculados a la orden.

        Más eficiente que ``vehicle_ids_for_order`` cuando se conoce el
        conjunto candidato (batch de resultados). Evita cargar TODOS los
        ids de órdenes con miles de vehículos (AUDIT.PARALLEL.1 — badge).
        """
        if not candidate_ids:
            return set()
        result = await self.session.execute(
            select(SearchOrderVehicle.vehicle_id).where(
                SearchOrderVehicle.search_order_id == str(order_id),
                SearchOrderVehicle.vehicle_id.in_(candidate_ids),
            )
        )
        return set(result.scalars().all())

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
