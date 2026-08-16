"""Base classes for the job scheduling system.

Defines the abstract Job interface, shared context, metrics tracking,
and result types used by all jobs and the scheduler.
"""

from __future__ import annotations

import copy
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.core.config import settings as app_settings
from app.database import DatabaseManager

# =============================================================================
# Enums
# =============================================================================


class JobStatus(str, Enum):
    """Current status of a job execution."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class JobResult:
    """Result of a single job execution.

    Attributes:
        success: Whether the job completed successfully.
        message: Human-readable outcome description.
        duration: Execution duration in seconds (wall-clock).
        data: Optional structured data produced by the job.
    """

    success: bool
    message: str = ""
    duration: float = 0.0
    data: dict[str, Any] | None = None


@dataclass
class JobMetrics:
    """Runtime metrics tracked per job by the scheduler.

    Attributes:
        last_execution: Datetime of the most recent run (utc).
        next_execution: Datetime of the next scheduled run (utc).
        last_duration: Duration of the most recent run in seconds.
        execution_count: Total number of executions.
        success_count: Number of successful executions.
        failure_count: Number of failed executions.
        consecutive_failures: Current streak of consecutive failures.
        status: Current JobStatus.
    """

    last_execution: datetime | None = None
    next_execution: datetime | None = None
    last_duration: float = 0.0
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    status: JobStatus = JobStatus.IDLE


@dataclass
class JobContext:
    """Shared context passed to every job execution.

    Attributes:
        db_manager: DatabaseManager for creating DB sessions.
        settings: Application settings (from app.core.config).
        logger: A logger instance for the job.
    """

    db_manager: DatabaseManager
    settings: Any = field(default_factory=lambda: app_settings)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))


# =============================================================================
# Abstract Job
# =============================================================================


class Job(ABC):
    """Abstract base class for all jobs.

    Every job must provide a unique ``name`` and implement the
    ``execute(context)`` method. The scheduler uses the name for
    registration, metrics tracking, and logging.
    """

    def __init__(self) -> None:
        self._metrics = JobMetrics()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this job."""
        ...

    @abstractmethod
    async def execute(self, context: JobContext) -> JobResult:
        """Execute the job's work.

        Args:
            context: Shared context providing DB access, settings, logger.

        Returns:
            JobResult indicating success/failure with details.
        """
        ...

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def metrics(self) -> JobMetrics:
        """Return a copy of the current metrics to prevent mutation."""
        return copy.deepcopy(self._metrics)

    def reset_metrics(self) -> None:
        """Reset all runtime metrics to initial values."""
        self._metrics = JobMetrics()

    def _record_execution(self, result: JobResult) -> None:
        """Update internal metrics after a job run (internal use)."""
        self._metrics.execution_count += 1
        self._metrics.last_duration = result.duration
        self._metrics.last_execution = datetime.now(UTC)

        if result.success:
            self._metrics.success_count += 1
            self._metrics.consecutive_failures = 0
            self._metrics.status = JobStatus.SUCCESS
        else:
            self._metrics.failure_count += 1
            self._metrics.consecutive_failures += 1
            self._metrics.status = JobStatus.FAILED

