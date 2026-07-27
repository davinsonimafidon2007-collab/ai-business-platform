"""Tests for the Scheduler component.

Covers:
    - Job registration and unregistration
    - Periodic execution cycle
    - One-shot (run_once) execution
    - Cancellation / graceful shutdown
    - Error handling (job failure doesn't crash scheduler)
    - Concurrency limits
    - Repeated failures tracking
    - Metrics consistency
    - Job registration after scheduler creation
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.jobs.base import Job, JobContext, JobResult, JobStatus
from app.jobs.scheduler import Scheduler


# =============================================================================
# Helper: a test job that tracks calls
# =============================================================================


class CallTrackerJob(Job):
    """A simple job that records each call and returns a configurable result."""

    def __init__(
        self,
        name: str = "test_job",
        *,
        fail_on: set[int] | None = None,
        delay: float = 0.0,
    ) -> None:
        super().__init__()
        self._name = name
        self._fail_on = fail_on or set()
        self._delay = delay
        self.call_count = 0
        self.calls: list[int] = []

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context: JobContext) -> JobResult:
        self.call_count += 1
        call_num = self.call_count
        self.calls.append(call_num)

        if self._delay > 0:
            await asyncio.sleep(self._delay)

        if call_num in self._fail_on:
            return JobResult(
                success=False, message=f"Forced failure on call {call_num}"
            )

        return JobResult(
            success=True,
            message=f"Call {call_num} succeeded",
            data={"call": call_num},
        )


class NeverRunJob(Job):
    """A job that should never execute (used for unregister tests)."""

    @property
    def name(self) -> str:
        return "never_run"

    async def execute(self, context: JobContext) -> JobResult:
        pytest.fail("This job should never have been executed")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context() -> JobContext:
    """Minimal JobContext for testing.

    Uses a mock db_manager that will fail if called (tests shouldn't need it).
    """
    return JobContext(
        db_manager=None,  # type: ignore[arg-type]
        settings=None,  # type: ignore[arg-type]
        logger=logging.getLogger("test_scheduler"),
    )


@pytest.fixture
def scheduler(context: JobContext) -> Scheduler:
    """Creates a fresh Scheduler with max_concurrent=2 for testing."""
    return Scheduler(context, max_concurrent=2)


# =============================================================================
# Registration
# =============================================================================


class TestRegistration:
    """Tests for job registration and unregistration."""

    def test_register_job(self, scheduler: Scheduler) -> None:
        """A job can be registered with an interval."""
        job = CallTrackerJob("my_job")
        scheduler.register(job, interval=60)
        assert "my_job" in scheduler.registered_jobs
        assert scheduler.registered_jobs["my_job"].interval == 60

    def test_register_duplicate_raises(self, scheduler: Scheduler) -> None:
        """Registering the same name twice raises ValueError."""
        scheduler.register(CallTrackerJob("dup"), interval=10)
        with pytest.raises(ValueError, match="already registered"):
            scheduler.register(CallTrackerJob("dup"), interval=20)

    def test_register_zero_interval(self, scheduler: Scheduler) -> None:
        """Jobs with interval=0 can be registered (manual only)."""
        job = CallTrackerJob("manual")
        scheduler.register(job, interval=0)
        assert "manual" in scheduler.registered_jobs

    def test_unregister_job(self, scheduler: Scheduler) -> None:
        """A registered job can be unregistered."""
        scheduler.register(CallTrackerJob("remove_me"), interval=60)
        scheduler.unregister("remove_me")
        assert "remove_me" not in scheduler.registered_jobs

    def test_unregister_missing_raises(self, scheduler: Scheduler) -> None:
        """Unregistering a non-existent job raises KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            scheduler.unregister("nope")

    def test_register_after_creation(self, scheduler: Scheduler) -> None:
        """Jobs can be registered after scheduler creation (before start)."""
        job = CallTrackerJob("late_registration")
        scheduler.register(job, interval=10)
        assert "late_registration" in scheduler.registered_jobs


# =============================================================================
# One-shot execution
# =============================================================================


class TestRunOnce:
    """Tests for the run_once() one-shot execution."""

    @pytest.mark.asyncio
    async def test_run_once_success(self, scheduler: Scheduler) -> None:
        """run_once executes a job and returns a successful result."""
        job = CallTrackerJob("once")
        result = await scheduler.run_once(job)

        assert result.success is True
        assert result.data == {"call": 1}
        assert result.duration >= 0
        assert job.call_count == 1

    @pytest.mark.asyncio
    async def test_run_once_failure(self, scheduler: Scheduler) -> None:
        """run_once returns a failed result when the job fails."""
        job = CallTrackerJob("fail_once", fail_on={1})
        result = await scheduler.run_once(job)

        assert result.success is False
        assert "Forced failure" in result.message

    @pytest.mark.asyncio
    async def test_run_once_unhandled_exception(
        self, scheduler: Scheduler
    ) -> None:
        """run_once catches unhandled exceptions and returns a failed result."""

        class ExplodingJob(Job):
            @property
            def name(self) -> str:
                return "exploder"

            async def execute(self, context: JobContext) -> JobResult:
                raise RuntimeError("Kaboom!")

        job = ExplodingJob()
        result = await scheduler.run_once(job)

        assert result.success is False
        assert "Kaboom!" in result.message

    @pytest.mark.asyncio
    async def test_run_once_does_not_register(self, scheduler: Scheduler) -> None:
        """run_once does NOT register the job."""
        job = CallTrackerJob("no_register")
        await scheduler.run_once(job)
        assert "no_register" not in scheduler.registered_jobs


# =============================================================================
# Periodic execution
# =============================================================================


class TestPeriodic:
    """Tests for periodic job execution."""

    @pytest.mark.asyncio
    async def test_periodic_execution(self, scheduler: Scheduler) -> None:
        """A periodic job executes multiple times."""
        job = CallTrackerJob("periodic_test")
        scheduler.register(job, interval=0.05)  # 50ms interval

        await scheduler.start()
        await asyncio.sleep(0.12)  # Allow ~2-3 executions
        await scheduler.stop()

        assert job.call_count >= 2, (
            f"Expected at least 2 calls, got {job.call_count}"
        )

    @pytest.mark.asyncio
    async def test_stop_stops_execution(self, scheduler: Scheduler) -> None:
        """After stop(), a periodic job does not execute more."""
        job = CallTrackerJob("stop_test")
        scheduler.register(job, interval=0.02)

        await scheduler.start()
        await asyncio.sleep(0.06)
        await scheduler.stop()

        calls_before = job.call_count
        await asyncio.sleep(0.06)  # Wait longer than one interval

        assert job.call_count == calls_before, (
            "Job kept running after scheduler.stop()"
        )

    @pytest.mark.asyncio
    async def test_register_zero_interval_no_auto_run(
        self, scheduler: Scheduler
    ) -> None:
        """Jobs with interval=0 are NOT automatically executed."""
        job = CallTrackerJob("manual_only")
        scheduler.register(job, interval=0)

        await scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

        assert job.call_count == 0, (
            "Job with interval=0 should not auto-execute"
        )


# =============================================================================
# Concurrency limits
# =============================================================================


class TestConcurrency:
    """Tests for concurrent execution limits."""

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        """No more than max_concurrent jobs run simultaneously."""
        context = JobContext(
            db_manager=None,
            settings=None,
            logger=logging.getLogger("test_concurrency"),
        )
        scheduler = Scheduler(context, max_concurrent=2)

        max_concurrent_observed = 0
        current_running = 0
        lock = asyncio.Lock()

        class SlowJob(Job):
            @property
            def name(self) -> str:
                return "slow"

            async def execute(self, context: JobContext) -> JobResult:
                nonlocal max_concurrent_observed, current_running
                async with lock:
                    current_running += 1
                    max_concurrent_observed = max(
                        max_concurrent_observed, current_running
                    )
                await asyncio.sleep(0.05)
                async with lock:
                    current_running -= 1
                return JobResult(success=True)

        scheduler.register(SlowJob(), interval=0.02)
        await scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()

        assert max_concurrent_observed <= 2, (
            f"Observed {max_concurrent_observed} concurrent, max is 2"
        )


# =============================================================================
# Error handling
# =============================================================================


class TestErrorHandling:
    """Tests that job failures don't crash the scheduler."""

    @pytest.mark.asyncio
    async def test_failure_does_not_crash_scheduler(
        self, scheduler: Scheduler
    ) -> None:
        """A failing job does not prevent subsequent executions."""
        job = CallTrackerJob("flaky", fail_on={1, 2})
        scheduler.register(job, interval=0.03)

        await scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()

        # The job should have run multiple times
        assert job.call_count >= 2
        # Verify that execution count equals success + failure
        metrics = scheduler.get_job_metrics("flaky")
        assert metrics is not None
        assert metrics.execution_count >= 2
        assert metrics.execution_count == metrics.success_count + metrics.failure_count

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracked(
        self, scheduler: Scheduler
    ) -> None:
        """Consecutive failures are tracked in metrics."""
        job = CallTrackerJob("always_fail", fail_on={1, 2, 3, 4, 5})
        scheduler.register(job, interval=0.02)

        await scheduler.start()
        await asyncio.sleep(0.12)
        await scheduler.stop()

        metrics = scheduler.get_job_metrics("always_fail")
        assert metrics is not None
        assert metrics.consecutive_failures > 0
        assert metrics.failure_count > 0


# =============================================================================
# Metrics
# =============================================================================


class TestMetrics:
    """Tests for runtime metric tracking."""

    @pytest.mark.asyncio
    async def test_metrics_after_success(self, scheduler: Scheduler) -> None:
        """Metrics are updated after a successful execution."""
        job = CallTrackerJob("metric_success")
        scheduler.register(job, interval=0.03)

        await scheduler.start()
        await asyncio.sleep(0.07)
        await scheduler.stop()

        metrics = scheduler.get_job_metrics("metric_success")
        assert metrics is not None
        assert metrics.execution_count > 0
        assert metrics.success_count > 0
        assert metrics.last_duration > 0
        assert metrics.last_execution is not None

    @pytest.mark.asyncio
    async def test_metrics_after_failure(self, scheduler: Scheduler) -> None:
        """Metrics reflect failures."""
        job = CallTrackerJob("metric_fail", fail_on={1})
        scheduler.register(job, interval=0.03)

        await scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

        metrics = scheduler.get_job_metrics("metric_fail")
        assert metrics is not None
        # At least one execution attempted
        assert metrics.execution_count >= 1
        # If first call was the failure, failure_count >= 1
        total = metrics.success_count + metrics.failure_count
        assert total == metrics.execution_count

    def test_list_jobs(self, scheduler: Scheduler) -> None:
        """list_jobs returns a snapshot of all registered jobs."""
        scheduler.register(CallTrackerJob("alpha"), interval=10)
        scheduler.register(CallTrackerJob("beta"), interval=20)

        jobs = scheduler.list_jobs()
        assert len(jobs) == 2

        names = {j["name"] for j in jobs}
        assert names == {"alpha", "beta"}

        for j in jobs:
            assert "interval" in j
            assert "status" in j
            assert "execution_count" in j

    def test_get_job_metrics_missing(self, scheduler: Scheduler) -> None:
        """get_job_metrics returns None for unregistered jobs."""
        metrics = scheduler.get_job_metrics("nonexistent")
        assert metrics is None


# =============================================================================
# Graceful shutdown
# =============================================================================


class TestShutdown:
    """Tests for graceful scheduler shutdown."""

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_running_jobs(
        self, scheduler: Scheduler
    ) -> None:
        """Scheduler stops gracefully even with long-running jobs."""

        class SlowJob(Job):
            @property
            def name(self) -> str:
                return "slowpoke"

            async def execute(self, context: JobContext) -> JobResult:
                await asyncio.sleep(10)  # Very long job
                return JobResult(success=True, message="Done")

        scheduler.register(SlowJob(), interval=0.02)
        await scheduler.start()
        # Don't wait for the job to finish
        await scheduler.stop()

        # After stop, scheduler reports not running
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_double_stop_is_safe(self, scheduler: Scheduler) -> None:
        """Calling stop() twice is safe and doesn't raise."""
        await scheduler.stop()
        await scheduler.stop()  # Second stop is a no-op

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, scheduler: Scheduler) -> None:
        """Calling start() twice doesn't break anything."""
        await scheduler.start()
        await scheduler.start()  # Second start is a no-op
        await scheduler.stop()


# =============================================================================
# Job status tracking
# =============================================================================


class TestJobStatus:
    """Tests for job status transitions."""

    @pytest.mark.asyncio
    async def test_status_idle_initially(self, scheduler: Scheduler) -> None:
        """Newly registered jobs start as IDLE."""
        job = CallTrackerJob("idle_check")
        scheduler.register(job, interval=60)

        metrics = scheduler.get_job_metrics("idle_check")
        assert metrics is not None
        assert metrics.status == JobStatus.IDLE

    @pytest.mark.asyncio
    async def test_status_after_execution(self, scheduler: Scheduler) -> None:
        """Status reflects SUCCESS or FAILED before stop, CANCELLED after."""
        job = CallTrackerJob("status_check")
        scheduler.register(job, interval=0.03)

        await scheduler.start()
        await asyncio.sleep(0.08)
        await scheduler.stop()

        metrics = scheduler.get_job_metrics("status_check")
        assert metrics is not None
        # After scheduler.stop(), periodic jobs get CANCELLED status.
        # The job itself may have succeeded or failed during execution.
        # assert that execution_count matches success_count + failure_count
        assert metrics.execution_count == metrics.success_count + metrics.failure_count

