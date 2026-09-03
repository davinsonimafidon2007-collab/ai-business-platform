from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.limits import clamp_limit
from app.models.audit_log import AuditLog
from app.models.deal import ACTIVE_STATUSES, Deal, DealStatus, DealStatusHistory


class DealRepository:
    """Repository for Deal persistence operations (Task D.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, deal: Deal) -> Deal:
        """Persists a new deal.

        Args:
            deal: The Deal instance to persist.

        Returns:
            The persisted Deal with generated id and timestamps.

        Raises:
            sqlalchemy.exc.IntegrityError: si se viola el índice único parcial
                ``uq_deals_active_per_opportunity`` (duplicado concurrente).
        """
        self.session.add(deal)
        await self.session.commit()
        await self.session.refresh(deal)
        return deal

    async def get_by_id(
        self,
        deal_id: str | UUID,
        *,
        for_update: bool = False,
    ) -> Deal | None:
        """Retrieves a deal by id.

        Args:
            deal_id: The UUID (as string or UUID object) of the deal.
            for_update: Si True, bloquea la fila (SELECT ... FOR UPDATE)
                para serializar transiciones concurrentes. En SQLite el
                lock es un no-op; en PostgreSQL es real.

        Returns:
            The Deal if found, None otherwise.
        """
        query = (
            select(Deal)
            .where(Deal.id == str(deal_id))
            .options(
                selectinload(Deal.vehicle),
                selectinload(Deal.opportunity),
            )
        )
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_opportunity(
        self,
        user_id: str | UUID,
        opportunity_id: str | UUID,
    ) -> Deal | None:
        """Returns an active (non-terminal) deal for an opportunity.

        "Active" is any status before SOLD/LOST/CANCELLED (TASK 3): a deal
        that already reached WON/BOUGHT/IN_TRANSIT/REGISTERED still blocks
        a duplicate deal for the same opportunity, not just NEW/ANALYZING/
        NEGOTIATING as before the fulfillment stages existed. See
        ``ACTIVE_STATUSES`` in app.models.deal (single source of truth).

        Args:
            user_id: The owner of the deal.
            opportunity_id: The opportunity to check.

        Returns:
            The active Deal if found, None otherwise.
        """
        active_statuses = [s.value for s in ACTIVE_STATUSES]
        result = await self.session.execute(
            select(Deal).where(
                Deal.user_id == str(user_id),
                Deal.opportunity_id == str(opportunity_id),
                Deal.status.in_(active_statuses),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: str | UUID,
        status: DealStatus | str | None = None,
        opportunity_id: str | UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Deal], int]:
        """Lists deals owned by a user, optionally filtered by status.

        Args:
            user_id: The owner of the deals.
            status: Optional status filter (e.g. "NEW", "ANALYZING").
            opportunity_id: Optional filter by opportunity.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A tuple of (list of Deal, total count).
        """
        limit = clamp_limit(limit)
        base_query = select(Deal).where(Deal.user_id == str(user_id))

        if opportunity_id is not None:
            base_query = base_query.where(
                Deal.opportunity_id == str(opportunity_id)
            )

        if status is not None:
            status_value = (
                status.value if isinstance(status, DealStatus) else str(status)
            )
            base_query = base_query.where(Deal.status == status_value)

        # func.count() sin columna: ver comentario equivalente en
        # OpportunityRepository.list_filtered (mismo bug de producto
        # cartesiano al contar sobre un subquery, encontrado en TASK 3).
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        items_query = (
            base_query.options(
                selectinload(Deal.vehicle),
                selectinload(Deal.opportunity),
            )
            .order_by(Deal.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await self.session.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    async def get_portfolio_aggregates(self, user_id: str | UUID) -> dict:
        """Agregados de cartera para reporting (previsto vs. real, cashflow).

        Toda la suma se hace en SQL (no trayendo filas a Python) para que
        escale con el número de deals. ``func.sum`` ignora NULLs por
        defecto, que es justo el comportamiento deseado (un deal sin
        ``actual_taxes`` capturado no debe contarse como 0 en la suma).

        Returns:
            dict con conteos por estado, agregados de deals SOLD (real vs.
            previsto) y del pipeline activo (solo previsto, aún no hay real).
        """
        user_id_str = str(user_id)

        status_counts_query = (
            select(Deal.status, func.count())
            .where(Deal.user_id == user_id_str)
            .group_by(Deal.status)
        )
        status_result = await self.session.execute(status_counts_query)
        by_status = {row[0]: row[1] for row in status_result.all()}

        sold_query = select(
            func.count(),
            func.sum(Deal.actual_profit),
            func.sum(Deal.last_sim_net_profit),
            func.sum(Deal.sale_price),
            func.sum(Deal.actual_purchase_price),
            func.sum(Deal.transport_cost),
            func.sum(Deal.registration_cost),
            func.sum(Deal.actual_taxes),
        ).where(Deal.user_id == user_id_str, Deal.status == DealStatus.SOLD.value)
        sold_row = (await self.session.execute(sold_query)).one()

        active_statuses = [s.value for s in ACTIVE_STATUSES]
        pipeline_query = select(func.count(), func.sum(Deal.last_sim_net_profit)).where(
            Deal.user_id == user_id_str, Deal.status.in_(active_statuses)
        )
        pipeline_row = (await self.session.execute(pipeline_query)).one()

        return {
            "by_status": by_status,
            "sold_count": sold_row[0] or 0,
            "sold_actual_profit_sum": sold_row[1],
            "sold_projected_profit_sum": sold_row[2],
            "sold_revenue_sum": sold_row[3],
            "sold_purchase_sum": sold_row[4],
            "sold_transport_sum": sold_row[5],
            "sold_registration_sum": sold_row[6],
            "sold_taxes_sum": sold_row[7],
            "pipeline_count": pipeline_row[0] or 0,
            "pipeline_projected_profit_sum": pipeline_row[1],
        }

    async def save_transition(
        self,
        deal: Deal,
        history: DealStatusHistory,
        audit_log: AuditLog | None = None,
    ) -> Deal:
        """Persists a state transition atomically.

        Deal + history + audit log se confirman en una única transacción:
        o queda todo, o no queda nada. Un conflicto de versión (bloqueo
        optimista) eleva ``StaleDataError`` desde el commit.

        Args:
            deal: The Deal instance with updated fields (or the new Deal on
                creation paths).
            history: The immutable DealStatusHistory row for this transition.
            audit_log: Optional AuditLog entry for the global audit trail.

        Returns:
            The refreshed Deal.
        """
        # add() es idempotente: en transiciones el deal ya está persistente;
        # en creación lo introduce en la sesión para que se inserte aquí.
        self.session.add(deal)
        self.session.add(history)
        if audit_log is not None:
            self.session.add(audit_log)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(deal)
        return deal

    async def list_history(
        self,
        deal_id: str | UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DealStatusHistory], int]:
        """Lists the status history of a deal, newest first.

        Args:
            deal_id: The deal whose history to list.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A tuple of (list of DealStatusHistory, total count).
        """
        limit = clamp_limit(limit)
        deal_id_str = str(deal_id)

        count_result = await self.session.execute(
            select(func.count(DealStatusHistory.id)).where(
                DealStatusHistory.deal_id == deal_id_str
            )
        )
        total = count_result.scalar() or 0

        result = await self.session.execute(
            select(DealStatusHistory)
            .where(DealStatusHistory.deal_id == deal_id_str)
            .order_by(DealStatusHistory.created_at.desc(), DealStatusHistory.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def update(self, deal: Deal) -> Deal:
        """Persists changes to an existing deal.

        Args:
            deal: The Deal instance with updated fields.

        Returns:
            The refreshed Deal.
        """
        await self.session.commit()
        await self.session.refresh(deal)
        return deal

    async def delete(self, deal: Deal, audit_log: AuditLog | None = None) -> None:
        """Deletes a deal record (history cascades).

        Args:
            deal: The Deal instance to delete.
            audit_log: Optional AuditLog entry persisted in the same commit.
        """
        if audit_log is not None:
            self.session.add(audit_log)
        await self.session.delete(deal)
        await self.session.commit()

    @staticmethod
    def now() -> datetime:
        """Current aware UTC timestamp (helper shared with services)."""
        return datetime.now(UTC)
