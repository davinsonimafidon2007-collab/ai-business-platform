from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.limits import clamp_limit
from app.models.opportunity import Opportunity
from app.models.vehicle import Vehicle
from app.repositories.cursor_pagination import CursorPaginator


class OpportunityRepository:
    """Repository for Opportunity persistence operations.

    Handles CRUD for vehicle import opportunity analysis records,
    including opportunity scores, recommendations, ROI, risk and profit data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, opportunity: Opportunity) -> Opportunity:
        """Persists a new opportunity record.

        Args:
            opportunity: The Opportunity instance to persist.

        Returns:
            The persisted Opportunity with generated id and timestamps.
        """
        self.session.add(opportunity)
        await self.session.commit()
        await self.session.refresh(opportunity)
        return opportunity

    async def save_many(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Persists multiple opportunity records in a single transaction.

        Args:
            opportunities: List of Opportunity instances to persist.

        Returns:
            List of persisted Opportunity instances.
        """
        for opp in opportunities:
            self.session.add(opp)
        await self.session.commit()
        for opp in opportunities:
            await self.session.refresh(opp)
        return opportunities

    async def get(self, opportunity_id: str | UUID) -> Opportunity | None:
        """Retrieves an opportunity record by id.

        Args:
            opportunity_id: The UUID (as string or UUID object) of the record.

        Returns:
            The Opportunity if found, None otherwise.
        """
        result = await self.session.execute(
            select(Opportunity)
            .where(Opportunity.id == str(opportunity_id))
            .options(selectinload(Opportunity.vehicle))
        )
        return result.scalar_one_or_none()

    async def get_by_vehicle_id(self, vehicle_id: str | UUID) -> list[Opportunity]:
        """Retrieves all opportunity records for a given vehicle.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            List of Opportunity records ordered by analyzed_at DESC (NULLS LAST).
        """
        result = await self.session.execute(
            select(Opportunity)
            .where(Opportunity.vehicle_id == str(vehicle_id))
            .options(selectinload(Opportunity.vehicle))
            .order_by(Opportunity.analyzed_at.desc().nulls_last(), Opportunity.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_by_vehicle_id(self, vehicle_id: str | UUID) -> Opportunity | None:
        """Retrieves the most recent opportunity for a vehicle.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            The latest Opportunity record, or None if none exists.
        """
        result = await self.session.execute(
            select(Opportunity)
            .where(Opportunity.vehicle_id == str(vehicle_id))
            .options(selectinload(Opportunity.vehicle))
            .order_by(Opportunity.analyzed_at.desc().nulls_last(), Opportunity.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert_opportunity(self, opportunity: Opportunity) -> Opportunity:
        """Inserts a new opportunity or updates the latest one for the same vehicle.

        This prevents duplicate opportunities for the same vehicle by updating
        the most recent record instead of creating a new one.

        Args:
            opportunity: The Opportunity instance to persist.

        Returns:
            The persisted Opportunity (new or updated).
        """
        existing = await self.get_latest_by_vehicle_id(opportunity.vehicle_id)
        if existing is not None:
            # Update existing record
            existing.opportunity_score = opportunity.opportunity_score
            existing.recommendation = opportunity.recommendation
            existing.roi = opportunity.roi
            existing.risk = opportunity.risk
            existing.profit = opportunity.profit
            existing.analyzed_at = opportunity.analyzed_at or datetime.now(UTC)
            existing.engine_version = opportunity.engine_version
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new record
            return await self.save(opportunity)

    async def exists(self, vehicle_id: str | UUID) -> bool:
        """Checks if any opportunity record exists for a vehicle.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            True if at least one record exists, False otherwise.
        """
        result = await self.session.execute(
            select(Opportunity.id)
            .where(Opportunity.vehicle_id == str(vehicle_id))
            .limit(1)
        )
        return result.scalar() is not None

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        """Lists all opportunity records with pagination.

        Args:
            skip: Number of records to skip (pagination).
            limit: Maximum number of records to return.

        Returns:
            List of Opportunity records ordered by created_at DESC.
        """
        result = await self.session.execute(
            select(Opportunity)
            .options(selectinload(Opportunity.vehicle))
            .order_by(Opportunity.created_at.desc())
            .offset(skip)
            .limit(clamp_limit(limit))
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        *,
        user_id: str | None = None,
        recommendation: str | None = None,
        min_score: float | None = None,
        min_roi: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Opportunity], int]:
        """Lists opportunity records with optional filters and pagination.

        Opportunities are scoped to the user via the vehicle's ``user_id``.
        Returns ``(items, total)`` where items are ordered by
        ``opportunity_score`` DESC.

        Args:
            user_id: If provided, only opportunities for vehicles owned by
                this user are returned.
            recommendation: Optional filter on recommendation value
                (e.g. BUY_NOW, WATCH, NEGOTIATE, REJECT).
            min_score: Optional minimum opportunity_score (inclusive).
            min_roi: Optional minimum roi percentage (inclusive).
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            A tuple of (list of Opportunity, total count).
        """
        limit = clamp_limit(limit)
        base_query = select(Opportunity).join(
            Vehicle, Vehicle.id == Opportunity.vehicle_id
        )

        if user_id is not None:
            base_query = base_query.where(Vehicle.user_id == user_id)
        if recommendation is not None:
            base_query = base_query.where(Opportunity.recommendation == recommendation)
        if min_score is not None:
            base_query = base_query.where(Opportunity.opportunity_score >= min_score)
        if min_roi is not None:
            base_query = base_query.where(Opportunity.roi >= min_roi)

        # Count query
        count_query = select(func.count(Opportunity.id)).select_from(
            base_query.subquery()
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Items query - deterministic tie-breaker for paginación
        items_query = (
            base_query.options(selectinload(Opportunity.vehicle))
            .order_by(Opportunity.opportunity_score.desc(), Opportunity.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await self.session.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    async def list_export(
        self,
        *,
        user_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        max_rows: int = 5000,
    ) -> list[Opportunity]:
        """Lista oportunidades del usuario para export (TASK-018).

        Filtra por rango de ``created_at`` inclusive (si se indica) e incluye
        el vehículo (selectinload). Tope duro de filas (PERF-001).
        """
        query = (
            select(Opportunity)
            .options(selectinload(Opportunity.vehicle))
            .where(Opportunity.vehicle_id.in_(
                select(Vehicle.id).where(Vehicle.user_id == user_id)
            ))
        )
        if date_from is not None:
            query = query.where(Opportunity.created_at >= date_from)
        if date_to is not None:
            query = query.where(Opportunity.created_at <= date_to)
        query = (
            query.order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
            .limit(max_rows)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, opportunity: Opportunity) -> None:
        """Deletes an opportunity record.

        Args:
            opportunity: The Opportunity instance to delete.
        """
        await self.session.delete(opportunity)
        await self.session.commit()

    async def count(self) -> int:
        """Counts total opportunity records.

        Returns:
            Total number of records.
        """
        result = await self.session.execute(
            select(func.count(Opportunity.id))
        )
        return result.scalar() or 0

    async def list_cursor(
        self,
        cursor: str | None = None,
        limit: int = 20,
        user_id: str | None = None,
    ) -> tuple[list[Opportunity], int, bool, str | None]:
        """Pagina las oportunidades con keyset (TASK-019).

        Devuelve ``(items, total, has_more, next_cursor)`` ordenado por
        ``created_at DESC, id DESC``. Con ``user_id`` filtra por vehículos
        del usuario (join). Los items incluyen ``Opportunity.vehicle``.
        """
        limit = clamp_limit(limit)
        where: list = [Opportunity.vehicle_id.is_not(None)]
        if user_id is not None:
            where = [
                *where,
                Opportunity.vehicle_id.in_(
                    select(Vehicle.id).where(Vehicle.user_id == user_id)
                ),
            ]

        paginator = CursorPaginator(self.session, Opportunity)
        # Van con eager-load del vehicle en la query de items del paginator.
        return await paginator.paginate(
            cursor,
            limit,
            where=where,
            options=[selectinload(Opportunity.vehicle)],
        )

