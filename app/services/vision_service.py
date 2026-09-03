"""Adapter between VisionProvider output and inspection-session suggestions."""

from __future__ import annotations

from app.core.config import settings
from app.core.path_safety import UnsafePhotoPathError, validate_photo_file_path
from app.models.inspection import InspectionObservation, InspectionPhoto
from app.models.vision import VisionImage
from app.providers.vision_provider import VisionProvider


class VisionService:
    """Produces reviewable suggestions only; it never persists inspection changes."""

    def __init__(self, provider: VisionProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        """Nombre del backend de vision activo (mock/gemini/openai)."""
        return str(getattr(self._provider, "provider_name", "mock"))

    @property
    def simulated(self) -> bool:
        """True si el análisis es simulado (MockVisionProvider), no real."""
        return bool(getattr(self._provider, "simulated", True))

    async def analyze_photos(
        self,
        photos: list[InspectionPhoto],
        observations: dict[str, InspectionObservation],
    ) -> dict[str, object]:
        # SEC.LFI.1 / SEC.SSRF.1: nunca enviar al proveedor rutas fuera del
        # directorio de uploads ni URLs inseguras; se descartan en silencio
        # (el intento queda registrado en el log de la app).
        safe_images: list[VisionImage] = []
        for photo in photos:
            try:
                path = validate_photo_file_path(photo.file_path, settings.upload_dir)
            except UnsafePhotoPathError:
                continue
            safe_images.append(
                VisionImage(photo_id=photo.id, file_path=path)
            )
        result = await self._provider.analyze_images(safe_images)
        suggestions: list[dict[str, object]] = []
        for detected in result.observations:
            inspection_observation = observations.get(detected.photo_id)
            if inspection_observation is None:
                continue
            suggestions.append(
                {
                    "photo_id": detected.photo_id,
                    "observation_id": inspection_observation.id,
                    "category_id": inspection_observation.category_id,
                    "item_id": inspection_observation.item_id,
                    "status": detected.status,
                    "severity": detected.severity.value,
                    "confidence": detected.confidence.value,
                    "notes": detected.notes,
                    "suggested_repair_cost": detected.suggested_repair_cost,
                }
            )
        return {
            "summary": result.summary,
            "suggestions": suggestions,
            "provider": self.provider_name,
            "simulated": self.simulated,
        }
