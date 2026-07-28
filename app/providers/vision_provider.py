"""Provider contract and local mock for inspection photo analysis."""

from __future__ import annotations

from typing import Protocol

from app.models.vision import (
    VisionConfidence,
    VisionImage,
    VisionInspectionResult,
    VisionObservation,
    VisionSeverity,
)


class VisionProvider(Protocol):
    async def analyze_images(self, images: list[VisionImage]) -> VisionInspectionResult:
        """Return non-persistent inspection suggestions for the supplied images."""


class MockVisionProvider:
    """Deterministic local provider used while no real vision backend is configured."""

    async def analyze_images(self, images: list[VisionImage]) -> VisionInspectionResult:
        return VisionInspectionResult(
            observations=[
                VisionObservation(
                    photo_id=image.photo_id,
                    status="WARNING",
                    severity=VisionSeverity.MEDIUM,
                    confidence=VisionConfidence.MEDIUM,
                    notes="Posible desperfecto visual detectado. Requiere confirmación del inspector.",
                    suggested_repair_cost=150.0,
                )
                for image in images
            ],
            summary="Sugerencias generadas por el proveedor simulado; no se han aplicado cambios.",
        )
