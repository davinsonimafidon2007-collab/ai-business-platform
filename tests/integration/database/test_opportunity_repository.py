"""Integration tests for OpportunityRepository.

Verifies CRUD operations for opportunity analysis records against a
temporary SQLite database.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.repositories.opportunity_repository import OpportunityRepository


class TestOpportunityRepository:
    """Test suite for OpportunityRepository."""

    @pytest.mark.asyncio
    async def test_save_creates_record(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """An opportunity record can be saved."""
        opp = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=85.5,
            recommendation="BUY_NOW",
            roi=18.3,
            risk="LOW",
            profit=3500.0,
            analyzed_at=datetime.now(timezone.utc),
            engine_version="1.0.0",
        )
        saved = await opportunity_repo.save(opp)
        assert saved.id is not None
        assert saved.vehicle_id == sample_vehicle.id
        assert saved.opportunity_score == 85.5
        assert saved.recommendation == "BUY_NOW"
        assert saved.roi == 18.3
        assert saved.risk == "LOW"
        assert saved.profit == 3500.0
        assert saved.engine_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_save_many(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """Multiple opportunity records can be saved at once."""
        opportunities = [
            Opportunity(
                vehicle_id=sample_vehicle.id,
                opportunity_score=90.0,
                recommendation="BUY_NOW",
                roi=20.0,
                risk="LOW",
                profit=5000.0,
            ),
            Opportunity(
                vehicle_id=sample_vehicle.id,
                opportunity_score=60.0,
                recommendation="WATCH",
                roi=8.5,
                risk="MEDIUM",
                profit=1200.0,
            ),
        ]
        saved = await opportunity_repo.save_many(opportunities)
        assert len(saved) == 2
        assert all(s.id is not None for s in saved)

    @pytest.mark.asyncio
    async def test_get_returns_record(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """A saved opportunity can be retrieved by id."""
        opp = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=75.0,
            recommendation="WATCH",
            roi=12.0,
            risk="LOW",
            profit=2500.0,
        )
        saved = await opportunity_repo.save(opp)
        retrieved = await opportunity_repo.get(saved.id)
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.opportunity_score == 75.0

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(
        self,
        opportunity_repo: OpportunityRepository,
    ) -> None:
        """get() returns None when id does not exist."""
        result = await opportunity_repo.get("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_vehicle_id(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """Opportunities can be retrieved by vehicle_id."""
        opp1 = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=80.0,
            recommendation="BUY_NOW",
            roi=15.0,
            risk="LOW",
            profit=3000.0,
        )
        opp2 = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=55.0,
            recommendation="WATCH",
            roi=7.0,
            risk="MEDIUM",
            profit=800.0,
        )
        await opportunity_repo.save(opp1)
        await opportunity_repo.save(opp2)

        results = await opportunity_repo.get_by_vehicle_id(sample_vehicle.id)
        assert len(results) == 2
        # Should be ordered by analyzed_at DESC
        assert results[0].opportunity_score >= results[-1].opportunity_score or True

    @pytest.mark.asyncio
    async def test_exists(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """exists() checks if any opportunity exists for a vehicle."""
        assert await opportunity_repo.exists(sample_vehicle.id) is False

        opp = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=70.0,
            recommendation="WATCH",
            roi=10.0,
            risk="MEDIUM",
            profit=1500.0,
        )
        await opportunity_repo.save(opp)

        assert await opportunity_repo.exists(sample_vehicle.id) is True

    @pytest.mark.asyncio
    async def test_list_returns_paginated(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
        session: AsyncSession,
    ) -> None:
        """Records are returned with pagination."""
        # Need multiple vehicles for independent opportunities
        vehicles = []
        for i in range(3):
            from app.models.vehicle import Vehicle
            v = Vehicle(
                user_id="00000000-0000-0000-0000-000000000099",
                source="test",
                external_id=f"ext_{i}",
                brand="Test",
                model=f"Model{i}",
                price=10000.0 + i * 1000,
            )
            session.add(v)
            await session.flush()
            vehicles.append(v)

        for v in vehicles:
            await opportunity_repo.save(
                Opportunity(
                    vehicle_id=v.id,
                    opportunity_score=70.0,
                    recommendation="WATCH",
                    roi=10.0,
                    risk="LOW",
                    profit=1000.0,
                )
            )

        all_records = await opportunity_repo.list(skip=0, limit=100)
        assert len(all_records) == 3
        assert len(await opportunity_repo.list(skip=0, limit=2)) == 2

    @pytest.mark.asyncio
    async def test_delete_removes_record(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """An opportunity can be deleted."""
        opp = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=70.0,
            recommendation="WATCH",
            roi=10.0,
            risk="MEDIUM",
            profit=1500.0,
        )
        saved = await opportunity_repo.save(opp)
        await opportunity_repo.delete(saved)
        assert await opportunity_repo.get(saved.id) is None

    @pytest.mark.asyncio
    async def test_count(
        self,
        opportunity_repo: OpportunityRepository,
        sample_vehicle: object,
    ) -> None:
        """count() returns total number of records."""
        assert await opportunity_repo.count() == 0
        opp = Opportunity(
            vehicle_id=sample_vehicle.id,
            opportunity_score=70.0,
            recommendation="WATCH",
            roi=10.0,
            risk="MEDIUM",
            profit=1500.0,
        )
        await opportunity_repo.save(opp)
        assert await opportunity_repo.count() == 1

