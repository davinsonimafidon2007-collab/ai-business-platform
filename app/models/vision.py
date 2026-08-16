"""Transport models for the pluggable inspection vision layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VisionConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VisionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class VisionImage:
    photo_id: str
    file_path: str


@dataclass(frozen=True)
class VisionObservation:
    photo_id: str
    status: str
    severity: VisionSeverity
    confidence: VisionConfidence
    notes: str
    suggested_repair_cost: float | None = None


@dataclass
class VisionInspectionResult:
    observations: list[VisionObservation] = field(default_factory=list)
    summary: str = ""
