"""Scheduler — Decoupled async job scheduler.

Allows registering periodic and one-shot jobs, manages concurrency,
and exposes runtime metrics for monitoring.

The scheduler is completely independent from FastAPI and can be reused
in CLI tools, tests, and worker processes.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.jobs.base import Job, JobContext, JobMetrics, JobResult, JobStatus


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class ScheduledJob:
    """Internal representation of a registered job.

    Attributes:
        job: The job instance.
        interval: Interval in seconds between periodic runs (0 = no repeat).
        task: Optional reference to the running asyncio.Task.
        cancel_event: Event used to signal cancellation.
        metrics: Current runtime metrics for this job.
    """

    job: Job
    interval: int
    task: asyncio.Task[None] | None = None
    cancel_event: asyncio.Event | None = None
    metrics: JobMetrics = field(default_factory=JobMetrics)


# =============================================================================
# Scheduler
# =============================================================================


class Scheduler:
    """Decoupled async job scheduler.

    Supports both periodic (interval > 0) and one-shot (interval = 0) jobs.

    Usage:
        scheduler = Scheduler(context)
        scheduler.register(job_instance, interval=3600)
        await scheduler.start()
        # ... later ...
        await scheduler.run_once(other_job)
        # ... later ...
        await scheduler.stop()
    """

    def __init__(
        self,
        context: JobContext,
        *,
        max_concurrent: int = 4,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the scheduler.

        Args:
            context: Shared ``JobContext`` passed to every job.
            max_concurrent: Maximum number of jobs that can run simultaneously.
            logger: Optional logger; defaults to ``app.jobs.scheduler``.
        """
        self._context = context
        self._max_concurrent = max_concurrent
        self._logger = logger or logging.getLogger("app.jobs.scheduler")
        self._jobs: dict[str, ScheduledJob] = {}
        self._semaphore: asyncio.Semaphore | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """True if the scheduler's event loop is active."""
        return self._running

    @property
    def registered_jobs(self) -> dict[str, ScheduledJob]:
        """Read-only view of registered scheduled jobs."""
        return dict(self._jobs)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, job: Job, interval: int = 0) -> None:
        """Register a job for periodic execution.

        Args:
            job: Job instance to register.
            interval: Interval in seconds between runs. Use 0 for
                manual/on-demand execution only.

        Raises:
            ValueError: If a job with the same name is already registered.
        """
        if job.name in self._jobs:
            raise ValueError(f"Job '{job.name}' is already registered.")

        self._jobs[job.name] = ScheduledJob(
            job=job,
            interval=interval,
            metrics=job._metrics,
        )
        self._logger.info(
            "Registered job '%s' with interval=%ss", job.name, interval
        )

    def unregister(self, name: str) -> None:
        """Unregister a previously registered job.

        If the job is currently running, it will be cancelled.

        Args:
            name: Name of the job to unregister.

        Raises:
            KeyError: If no job with that name exists.
        """
        if name not in self._jobs:
            raise KeyError(f"Job '{name}' is not registered.")

        entry = self._jobs.pop(name)
        if entry.task is not None and not entry.task.done():
            entry.task.cancel()
            self._logger.info("Cancelled running job '%s'", name)

        self._logger.info("Unregistered job '%s'", name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler loop.

        Begins executing registered periodic jobs on their intervals.
        """
        if self._running:
            self._logger.warning("Scheduler is already running.")
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

        # Start periodic tasks for each registered job
        for name, entry in list(self._jobs.items()):
            if entry.interval > 0:
                entry.cancel_event = asyncio.Event()
                entry.task = asyncio.create_task(
                    self._run_periodic(name, entry)
                )

        self._logger.info(
            "Scheduler started (max_concurrent=%s)", self._max_concurrent
        )

    async def stop(self) -> None:
        """Gracefully stop the scheduler.

        Signals all periodic jobs to stop and waits for them to finish.
        """
        if not self._running:
            return

        self._running = False

        # Signal cancellation to all periodic jobs
        for name, entry in self._jobs.items():
            if entry.cancel_event is not None:
                entry.cancel_event.set()

        # Wait for all tasks to complete
        tasks = [entry.task for entry in self._jobs.values() if entry.task is not None]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._logger.info("Scheduler stopped.")

    # ------------------------------------------------------------------
    # One-shot execution
    # ------------------------------------------------------------------

    async def run_once(self, job: Job) -> JobResult:
        """Execute a job immediately as a one-shot.

        This does NOT register the job; it runs it directly.
        Useful for manual triggers, admin panels, and testing.

        Args:
            job: Job instance to execute.

        Returns:
            JobResult from the execution.
        """
        return await self._execute_with_semaphore(job)

    # ------------------------------------------------------------------
    # Job listing / metrics
    # ------------------------------------------------------------------

    def get_job_metrics(self, name: str) -> JobMetrics | None:
        """Return metrics for a registered job.

        Args:
            name: Job name.

        Returns:
            JobMetrics if the job is registered, None otherwise.
        """
        entry = self._jobs.get(name)
        if entry is None:
            return None
        return entry.metrics

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return a snapshot of all registered jobs and their metrics.

        Returns:
            List of dicts with job name, interval, and current metrics.
        """
        result: list[dict[str, Any]] = []
        for name, entry in self._jobs.items():
            metrics = entry.metrics
            result.append({
                "name": name,
                "interval": entry.interval,
                "status": metrics.status.value,
                "last_execution": metrics.last_execution,
                "next_execution": metrics.next_execution,
                "last_duration": metrics.last_duration,
                "execution_count": metrics.execution_count,
                "success_count": metrics.success_count,
                "failure_count": metrics.failure_count,
                "consecutive_failures": metrics.consecutive_failures,
            })
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run_periodic(self, name: str, entry: ScheduledJob) -> None:
        """Background loop for a single periodic job.

        Ejecuta el job una vez al arrancar y después espera ``interval``
        entre ejecuciones. Así no hay que esperar 1h/24h tras un restart.
        """
        cancel_event = entry.cancel_event
        if cancel_event is None:
            return

        first_run = True

        while self._running and not cancel_event.is_set():
            if not first_run:
                now = datetime.now(timezone.utc)
                entry.metrics.next_execution = now + timedelta(seconds=entry.interval)
                try:
                    await self._wait_with_cancellation(
                        entry.interval, cancel_event
                    )
                except asyncio.CancelledError:
                    break

                if cancel_event.is_set() or not self._running:
                    break
            else:
                first_run = False
                entry.metrics.next_execution = datetime.now(timezone.utc)

            entry.metrics.status = JobStatus.RUNNING
            result = await self._execute_with_semaphore(entry.job)
            entry.job._record_execution(result)

        entry.metrics.status = JobStatus.CANCELLED

    async def _execute_with_semaphore(self, job: Job) -> JobResult:
        """Execute a job under the concurrency semaphore."""
        sem = self._semaphore
        if sem is None:
            # Allow execution even if scheduler not started (for run_once in tests)
            return await self._execute_job(job)

        async with sem:
            return await self._execute_job(job)

    async def _execute_job(self, job: Job) -> JobResult:
        """Execute a job and time it."""
        start = datetime.now(timezone.utc)
        try:
            result = await job.execute(self._context)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result = JobResult(
                success=False,
                message=f"Unhandled exception: {exc}",
                duration=duration,
            )
        else:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result.duration = duration

        return result

    @staticmethod
    async def _wait_with_cancellation(
        interval: int, cancel_event: asyncio.Event
    ) -> None:
        """Wait for the specified interval, checking cancellation periodically."""
        wait_time = min(interval, 1.0)  # Check cancel every second
        remaining = interval
        while remaining > 0:
            if cancel_event.is_set():
                return
            try:
                await asyncio.wait_for(
                    asyncio.sleep(min(wait_time, remaining)),
                    timeout=min(wait_time, remaining),
                )
            except asyncio.TimeoutError:
                pass
            remaining -= wait_time

