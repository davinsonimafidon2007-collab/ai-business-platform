"""Tests for individual Job implementations.

Covers:
    - RefreshMarketCacheJob
    - RefreshOpportunityJob
    - CleanupExpiredCacheJob
    - CleanupOldSearchesJob
    - Job base class metrics tracking

All tests use mocked DB sessions — no real database required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.base import Job, JobContext, JobResult, JobStatus
from app.jobs.cleanup_cache import CleanupExpiredCacheJob
from app.jobs.cleanup_old_searches import CleanupOldSearchesJob
from app.jobs.refresh_market_cache import RefreshMarketCacheJob
from app.jobs.refresh_opportunities import RefreshOpportunityJob

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Creates a mock DatabaseManager that returns mock sessions."""
    manager = MagicMock()
    manager.get_session = MagicMock()
    return manager


@pytest.fixture
def context(mock_db_manager: MagicMock) -> JobContext:
    """Creates a JobContext with a mock db_manager and default settings."""
    settings = MagicMock()
    settings.search_history_ttl = 3600
    settings.cache_refresh_interval = 600
    settings.max_concurrent_jobs = 4
    settings.enable_scheduler = True
    settings.market_cache_ttl = 21600

    return JobContext(
        db_manager=mock_db_manager,
        settings=settings,
        logger=logging.getLogger("test_jobs"),
    )


# =============================================================================
# Job base class
# =============================================================================


class TestJobBase:
    """Tests for the Job base class and metrics."""

    def test_job_abstract_cannot_instantiate(self) -> None:
        """Job ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Job()  # type: ignore[abstract]

    def test_metrics_initial_values(self) -> None:
        """A fresh job has default metrics."""

        class SimpleJob(Job):
            @property
            def name(self) -> str:
                return "simple"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=True)

        job = SimpleJob()
        metrics = job._metrics
        assert metrics.execution_count == 0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
        assert metrics.consecutive_failures == 0
        assert metrics.status == JobStatus.IDLE
        assert metrics.last_execution is None

    def test_record_execution_success(self) -> None:
        """_record_execution updates metrics on success."""

        class GoodJob(Job):
            @property
            def name(self) -> str:
                return "good"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=True)

        job = GoodJob()
        result = JobResult(success=True, message="OK", duration=1.5)
        job._record_execution(result)

        assert job._metrics.execution_count == 1
        assert job._metrics.success_count == 1
        assert job._metrics.failure_count == 0
        assert job._metrics.consecutive_failures == 0
        assert job._metrics.last_duration == 1.5
        assert job._metrics.status == JobStatus.SUCCESS
        assert job._metrics.last_execution is not None

    def test_record_execution_failure(self) -> None:
        """_record_execution updates metrics on failure."""

        class BadJob(Job):
            @property
            def name(self) -> str:
                return "bad"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=False)

        job = BadJob()
        result = JobResult(success=False, message="Boom", duration=0.5)
        job._record_execution(result)

        assert job._metrics.execution_count == 1
        assert job._metrics.success_count == 0
        assert job._metrics.failure_count == 1
        assert job._metrics.consecutive_failures == 1
        assert job._metrics.status == JobStatus.FAILED

    def test_consecutive_failures_tracking(self) -> None:
        """Consecutive failures increment; success resets."""

        class TrackJob(Job):
            @property
            def name(self) -> str:
                return "test"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=True)

        track_job = TrackJob()
        track_job._record_execution(JobResult(success=False))
        track_job._record_execution(JobResult(success=False))
        assert track_job._metrics.consecutive_failures == 2

        track_job._record_execution(JobResult(success=True))
        assert track_job._metrics.consecutive_failures == 0

    def test_five_consecutive_failures(self) -> None:
        """Five consecutive failures accumulate; success resets the streak."""

        class FailJob(Job):
            @property
            def name(self) -> str:
                return "five_fail"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=False)

        job = FailJob()
        for _ in range(5):
            job._record_execution(JobResult(success=False, duration=0.01))
        assert job._metrics.consecutive_failures == 5
        assert job._metrics.failure_count == 5

        # A subsequent success resets the streak without touching failure_count.
        job._record_execution(JobResult(success=True, duration=0.01))
        assert job._metrics.consecutive_failures == 0
        assert job._metrics.failure_count == 5
        assert job._metrics.success_count == 1

    def test_reset_metrics(self) -> None:
        """reset_metrics restores initial state."""

        class ResetJob(Job):
            @property
            def name(self) -> str:
                return "reset_test"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=True)

        reset_job = ResetJob()
        reset_job._record_execution(JobResult(success=True, duration=1.0))
        reset_job.reset_metrics()

        assert reset_job._metrics.execution_count == 0
        assert reset_job._metrics.last_execution is None
        assert reset_job._metrics.last_duration == 0.0

    def test_metrics_property_returns_copy(self) -> None:
        """The metrics property returns a copy to prevent mutation."""

        class CopyJob(Job):
            @property
            def name(self) -> str:
                return "copy_test"

            async def execute(self, context: JobContext) -> JobResult:
                return JobResult(success=True)

        copy_job = CopyJob()
        metrics_copy = copy_job.metrics
        metrics_copy.execution_count = 999  # Should not affect internal

        assert copy_job._metrics.execution_count == 0


# =============================================================================
# RefreshMarketCacheJob
# =============================================================================


class TestRefreshMarketCacheJob:
    """Tests for RefreshMarketCacheJob."""

    def test_name(self) -> None:
        job = RefreshMarketCacheJob()
        assert job.name == "refresh_market_cache"

    @pytest.mark.asyncio
    async def test_execute_success(self, context: JobContext) -> None:
        """Successful execution returns success with deleted count."""
        # Mock the async context manager for db_manager.get_session()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        # Patch at source — local imports inside execute() resolve to patched version
        with patch(
            "app.repositories.cached_market_repository.CachedMarketRepository"
        ) as mock_repo_class:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.delete_expired = AsyncMock(return_value=5)
            mock_repo_class.return_value = mock_repo_instance

            job = RefreshMarketCacheJob()
            result = await job.execute(context)

        assert result.success is True
        assert "Cleaned 5" in result.message
        assert result.data == {"deleted_count": 5}
        assert result.duration >= 0

    @pytest.mark.asyncio
    async def test_execute_failure(self, context: JobContext) -> None:
        """Exception during execution returns a failed result."""
        # Mock the async context manager to raise
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        job = RefreshMarketCacheJob()
        result = await job.execute(context)

        assert result.success is False
        assert "DB error" in result.message


# =============================================================================
# RefreshOpportunityJob
# =============================================================================


class TestRefreshOpportunityJob:
    """Tests for RefreshOpportunityJob."""

    def test_name(self) -> None:
        job = RefreshOpportunityJob()
        assert job.name == "refresh_opportunities"

    @pytest.mark.asyncio
    async def test_execute_with_data(self, context: JobContext) -> None:
        """Executes successfully: recalculates opportunities for vehicles."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with (
            patch(
                "app.repositories.vehicle_repository.VehicleRepository"
            ) as mock_vehicle_repo,
            patch(
                "app.repositories.opportunity_repository.OpportunityRepository"
            ) as mock_opp_repo,
            patch(
                "app.services.evaluation_engine.EvaluationEngine"
            ) as mock_engine_class,
        ):
            # Mock vehicles
            mock_vehicle = MagicMock()
            mock_vehicle.id = "v1"
            mock_vehicle_repo_instance = AsyncMock()
            mock_vehicle_repo_instance.list_all = AsyncMock(
                return_value=[mock_vehicle]
            )
            mock_vehicle_repo.return_value = mock_vehicle_repo_instance

            # Mock opportunity repo: no existing opp → create new
            mock_opp_repo_instance = AsyncMock()
            mock_opp_repo_instance.get_by_vehicle_id = AsyncMock(return_value=[])
            mock_opp_repo_instance.save = AsyncMock(return_value=MagicMock())
            mock_opp_repo.return_value = mock_opp_repo_instance

            # Mock EvaluationEngine.evaluate → returns a result-like object
            mock_result = MagicMock()
            mock_result.score = 75
            mock_result.classification = "verde"
            mock_result.recommendation = "Buena oportunidad"
            mock_result.profit_margin_percent = 20.0
            mock_result.gross_profit = 1500.0
            mock_engine_instance = MagicMock()
            mock_engine_instance.evaluate = MagicMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            job = RefreshOpportunityJob()
            result = await job.execute(context)

        assert result.success is True
        assert result.data["vehicle_count"] == 1
        assert result.data["updated_count"] == 1
        assert result.data["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_calls_telegram_alert_service(self, context: JobContext) -> None:
        """El job dispara TelegramAlertService.send_opportunity_alert con la opp."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with (
            patch(
                "app.repositories.vehicle_repository.VehicleRepository"
            ) as mock_vehicle_repo,
            patch(
                "app.repositories.opportunity_repository.OpportunityRepository"
            ) as mock_opp_repo,
            patch(
                "app.services.evaluation_engine.EvaluationEngine"
            ) as mock_engine_class,
            patch(
                "app.repositories.user_repository.UserRepository"
            ) as mock_user_repo,
            patch(
                "app.services.opportunity_alert_service.OpportunityAlertService"
            ) as mock_alert_svc,
            patch(
                "app.services.telegram_alert_service.TelegramAlertService"
            ) as mock_tg_svc,
        ):
            mock_vehicle = MagicMock(id="v1", user_id="u1")
            mock_vehicle_repo_instance = AsyncMock()
            mock_vehicle_repo_instance.list_all = AsyncMock(return_value=[mock_vehicle])
            mock_vehicle_repo.return_value = mock_vehicle_repo_instance

            mock_opp_repo_instance = AsyncMock()
            mock_opp_repo_instance.get_by_vehicle_id = AsyncMock(return_value=[])
            mock_opp_repo_instance.save = AsyncMock(return_value=MagicMock())
            mock_opp_repo.return_value = mock_opp_repo_instance

            mock_result = MagicMock()
            mock_result.score = 75
            mock_result.classification = "verde"
            mock_result.recommendation = "Buena oportunidad"
            mock_result.profit_margin_percent = 20.0
            mock_result.gross_profit = 1500.0
            mock_engine_instance = MagicMock()
            mock_engine_instance.evaluate = MagicMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_user_repo_instance = AsyncMock()
            mock_user_repo_instance.get_by_id = AsyncMock(
                return_value=MagicMock(email="a@b.com")
            )
            mock_user_repo.return_value = mock_user_repo_instance

            mock_alert_svc.return_value.maybe_notify = AsyncMock(return_value=True)
            tg_instance = AsyncMock()
            tg_instance.send_opportunity_alert = AsyncMock(return_value=True)
            mock_tg_svc.return_value = tg_instance

            job = RefreshOpportunityJob()
            result = await job.execute(context)

        assert result.success is True
        assert result.data["updated_count"] == 1
        tg_instance.send_opportunity_alert.assert_awaited_once()
        call = tg_instance.send_opportunity_alert.await_args
        assert call.kwargs["opportunity"].vehicle_id == "v1"
        assert call.kwargs["vehicle"] is mock_vehicle
        assert call.kwargs["evaluation"] is mock_result

    @pytest.mark.asyncio
    async def test_execute_continues_if_telegram_fails(self, context: JobContext) -> None:
        """Un fallo en TelegramAlertService no debe romper el job (Task C.3)."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with (
            patch(
                "app.repositories.vehicle_repository.VehicleRepository"
            ) as mock_vehicle_repo,
            patch(
                "app.repositories.opportunity_repository.OpportunityRepository"
            ) as mock_opp_repo,
            patch(
                "app.services.evaluation_engine.EvaluationEngine"
            ) as mock_engine_class,
            patch(
                "app.repositories.user_repository.UserRepository"
            ) as mock_user_repo,
            patch(
                "app.services.opportunity_alert_service.OpportunityAlertService"
            ) as mock_alert_svc,
            patch(
                "app.services.telegram_alert_service.TelegramAlertService"
            ) as mock_tg_svc,
        ):
            mock_vehicle = MagicMock(id="v1", user_id="u1")
            mock_vehicle_repo_instance = AsyncMock()
            mock_vehicle_repo_instance.list_all = AsyncMock(return_value=[mock_vehicle])
            mock_vehicle_repo.return_value = mock_vehicle_repo_instance

            mock_opp_repo_instance = AsyncMock()
            mock_opp_repo_instance.get_by_vehicle_id = AsyncMock(return_value=[])
            mock_opp_repo_instance.save = AsyncMock(return_value=MagicMock())
            mock_opp_repo.return_value = mock_opp_repo_instance

            mock_engine_class.return_value.evaluate = MagicMock(
                return_value=MagicMock(
                    score=75,
                    classification="verde",
                    recommendation="BUY",
                    profit_margin_percent=20.0,
                    gross_profit=1500.0,
                )
            )

            mock_user_repo.return_value.get_by_id = AsyncMock(
                return_value=MagicMock(email="a@b.com")
            )

            mock_alert_svc.return_value.maybe_notify = AsyncMock(return_value=True)
            tg_instance = AsyncMock()
            tg_instance.send_opportunity_alert = AsyncMock(
                side_effect=RuntimeError("telegram exploded")
            )
            mock_tg_svc.return_value = tg_instance

            job = RefreshOpportunityJob()
            result = await job.execute(context)

        # El job atrapa la excepción del alerta y sigue exitoso.
        assert result.success is True
        assert result.data["updated_count"] == 1
        assert result.data["failed_count"] == 0
        tg_instance.send_opportunity_alert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_empty(self, context: JobContext) -> None:
        """Executes successfully with no vehicles."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with (
            patch(
                "app.repositories.vehicle_repository.VehicleRepository"
            ) as mock_vehicle_repo,
            patch(
                "app.repositories.opportunity_repository.OpportunityRepository"
            ) as mock_opp_repo,
            patch(
                "app.services.evaluation_engine.EvaluationEngine"
            ) as mock_engine_class,
        ):
            mock_vehicle_repo_instance = AsyncMock()
            mock_vehicle_repo_instance.list_all = AsyncMock(return_value=[])
            mock_vehicle_repo.return_value = mock_vehicle_repo_instance

            mock_opp_repo_instance = AsyncMock()
            mock_opp_repo.return_value = mock_opp_repo_instance

            mock_engine_class.return_value = MagicMock()

            job = RefreshOpportunityJob()
            result = await job.execute(context)

        assert result.success is True
        assert result.data["vehicle_count"] == 0
        assert result.data["updated_count"] == 0


# =============================================================================
# CleanupExpiredCacheJob
# =============================================================================


class TestCleanupExpiredCacheJob:
    """Tests for CleanupExpiredCacheJob."""

    def test_name(self) -> None:
        job = CleanupExpiredCacheJob()
        assert job.name == "cleanup_expired_cache"

    @pytest.mark.asyncio
    async def test_execute_deletes_expired(self, context: JobContext) -> None:
        """Delegates to CachedMarketRepository.delete_expired()."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with patch(
            "app.repositories.cached_market_repository.CachedMarketRepository"
        ) as mock_repo_class:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.delete_expired = AsyncMock(return_value=10)
            mock_repo_class.return_value = mock_repo_instance

            job = CleanupExpiredCacheJob()
            result = await job.execute(context)

        assert result.success is True
        assert "Deleted 10" in result.message
        assert result.data == {"deleted_count": 10}

    @pytest.mark.asyncio
    async def test_execute_no_expired(self, context: JobContext) -> None:
        """Returns success with 0 when nothing expired."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with patch(
            "app.repositories.cached_market_repository.CachedMarketRepository"
        ) as mock_repo_class:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.delete_expired = AsyncMock(return_value=0)
            mock_repo_class.return_value = mock_repo_instance

            job = CleanupExpiredCacheJob()
            result = await job.execute(context)

        assert result.success is True
        assert "Deleted 0" in result.message


# =============================================================================
# CleanupOldSearchesJob
# =============================================================================


class TestCleanupOldSearchesJob:
    """Tests for CleanupOldSearchesJob."""

    def test_name(self) -> None:
        job = CleanupOldSearchesJob()
        assert job.name == "cleanup_old_searches"

    @pytest.mark.asyncio
    async def test_execute_deletes_old(self, context: JobContext) -> None:
        """Deletes search history records older than TTL."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        with patch(
            "app.repositories.search_history_repository.SearchHistoryRepository"
        ) as mock_repo_class:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.delete_older_than = AsyncMock(return_value=7)
            mock_repo_class.return_value = mock_repo_instance

            job = CleanupOldSearchesJob()
            result = await job.execute(context)

        assert result.success is True
        assert "Deleted 7" in result.message
        assert result.data["deleted_count"] == 7

        # Verify that delete_older_than was called with a datetime
        mock_repo_instance.delete_older_than.assert_called_once()
        call_arg = mock_repo_instance.delete_older_than.call_args[0][0]
        assert isinstance(call_arg, datetime)

    @pytest.mark.asyncio
    async def test_execute_failure(self, context: JobContext) -> None:
        """Exception during execution returns a failed result."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=ValueError("Bad data"))
        mock_session.__aexit__ = AsyncMock(return_value=None)
        context.db_manager.get_session.return_value = mock_session

        job = CleanupOldSearchesJob()
        result = await job.execute(context)

        assert result.success is False
        assert "Bad data" in result.message
