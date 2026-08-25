"""Estados del pipeline del orquestador (ORCH.STATES.1).

Modela las 6 etapas del flujo completo SEARCH → PROVIDERS → NORMALIZATION →
ANALYSIS → OPPORTUNITY → DEAL con su máquina de estados por etapa y por
ejecución. ``PipelineRunState`` es la fuente de verdad en memoria de cada
run; la persistencia durable vive en ``app.models.pipeline_run``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class PipelineStage(str, Enum):
    """Etapas del flujo completo del orquestador."""

    SEARCH = "SEARCH"
    PROVIDERS = "PROVIDERS"
    NORMALIZATION = "NORMALIZATION"
    ANALYSIS = "ANALYSIS"
    OPPORTUNITY = "OPPORTUNITY"
    DEAL = "DEAL"

    @classmethod
    def in_order(cls) -> tuple["PipelineStage", ...]:
        """Etapas en el orden canónico de ejecución."""
        return (
            cls.SEARCH,
            cls.PROVIDERS,
            cls.NORMALIZATION,
            cls.ANALYSIS,
            cls.OPPORTUNITY,
            cls.DEAL,
        )


class StageStatus(str, Enum):
    """Estado de una etapa concreta dentro de un run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class PipelineRunStatus(str, Enum):
    """Estado global de una ejecución del pipeline."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StageTrace:
    """Trazabilidad de una etapa: estado, intentos, tiempos y metadatos."""

    __slots__ = (
        "stage",
        "status",
        "attempts",
        "started_at",
        "finished_at",
        "duration_ms",
        "error",
        "metadata",
    )

    def __init__(self, stage: PipelineStage) -> None:
        self.stage = stage
        self.status = StageStatus.PENDING
        self.attempts = 0
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.duration_ms: float | None = None
        self.error: str | None = None
        self.metadata: dict[str, Any] = {}

    def mark_running(self) -> None:
        self.status = StageStatus.RUNNING
        self.attempts += 1
        self.started_at = _utcnow()

    def mark_completed(self, metadata: dict[str, Any] | None = None) -> None:
        self.status = StageStatus.COMPLETED
        self.finished_at = _utcnow()
        if self.started_at is not None:
            self.duration_ms = (self.finished_at - self.started_at).total_seconds() * 1000
        if metadata:
            self.metadata.update(metadata)

    def mark_skipped(self, reason: str) -> None:
        self.status = StageStatus.SKIPPED
        self.finished_at = _utcnow()
        self.metadata["reason"] = reason

    def mark_failed(self, error: str) -> None:
        self.status = StageStatus.FAILED
        self.finished_at = _utcnow()
        if self.started_at is not None:
            self.duration_ms = (self.finished_at - self.started_at).total_seconds() * 1000
        self.error = error[:2000]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "attempts": self.attempts,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms is not None else None,
            "error": self.error,
            "metadata": self.metadata,
        }


class PipelineRunState:
    """Estado completo de una ejecución del pipeline (en memoria).

    Cada run tiene un id único, una clave de idempotencia opcional y una
    traza por etapa. Los métodos mutadores son síncronos: el run se ejecuta
    dentro de un solo task de asyncio.
    """

    def __init__(self, *, idempotency_key: str | None = None) -> None:
        self.run_id: str = str(uuid4())
        self.idempotency_key = idempotency_key
        self.status = PipelineRunStatus.PENDING
        self.current_stage: PipelineStage | None = None
        self.error: str | None = None
        self.created_at = _utcnow()
        self.updated_at = self.created_at
        self._stages: dict[PipelineStage, StageTrace] = {
            stage: StageTrace(stage) for stage in PipelineStage.in_order()
        }

    # ------------------------------------------------------------------
    # Ciclo de vida del run
    # ------------------------------------------------------------------

    def start(self) -> None:
        self.status = PipelineRunStatus.RUNNING
        self.touch()

    def complete(self) -> None:
        self.status = PipelineRunStatus.COMPLETED
        self.current_stage = None
        self.touch()

    def fail(self, error: str) -> None:
        self.status = PipelineRunStatus.FAILED
        self.error = error[:2000]
        self.touch()

    def touch(self) -> None:
        self.updated_at = _utcnow()

    # ------------------------------------------------------------------
    # Etapas
    # ------------------------------------------------------------------

    def start_stage(self, stage: PipelineStage) -> StageTrace:
        trace = self._stages[stage]
        trace.mark_running()
        self.current_stage = stage
        self.touch()
        return trace

    def complete_stage(
        self, stage: PipelineStage, metadata: dict[str, Any] | None = None
    ) -> StageTrace:
        trace = self._stages[stage]
        trace.mark_completed(metadata)
        self.touch()
        return trace

    def skip_stage(self, stage: PipelineStage, reason: str) -> StageTrace:
        trace = self._stages[stage]
        trace.mark_skipped(reason)
        self.touch()
        return trace

    def fail_stage(self, stage: PipelineStage, error: str) -> StageTrace:
        trace = self._stages[stage]
        if trace.status != StageStatus.RUNNING:
            trace.mark_running()
        trace.mark_failed(error)
        self.touch()
        return trace

    def trace(self, stage: PipelineStage) -> StageTrace:
        return self._stages[stage]

    def stages(self) -> Iterator[tuple[PipelineStage, StageTrace]]:
        return iter(self._stages.items())

    @property
    def completed_stages(self) -> int:
        return sum(
            1 for t in self._stages.values() if t.status == StageStatus.COMPLETED
        )

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "stages": [t.to_dict() for t in self._stages.values()],
        }
