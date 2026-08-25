"""Unit tests for the VisionService adapter.

VisionService is only an adapter between VisionProvider output and
inspection-session suggestion format. These tests verify correct
mapping and that no business logic leaks into the service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models.inspection import InspectionObservation, InspectionPhoto
from app.models.vision import (
    VisionConfidence,
    VisionImage,
    VisionInspectionResult,
    VisionObservation,
    VisionSeverity,
)
from app.services.vision_service import VisionService


@pytest.fixture
def mock_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.analyze_images = AsyncMock(
        return_value=VisionInspectionResult(
            observations=[
                VisionObservation(
                    photo_id="photo-1",
                    status="WARNING",
                    severity=VisionSeverity.MEDIUM,
                    confidence=VisionConfidence.MEDIUM,
                    notes="Posible rayón en la pintura.",
                    suggested_repair_cost=150.0,
                ),
                VisionObservation(
                    photo_id="photo-2",
                    status="BAD",
                    severity=VisionSeverity.HIGH,
                    confidence=VisionConfidence.HIGH,
                    notes="Abolladura en el panel lateral.",
                    suggested_repair_cost=450.0,
                ),
            ],
            summary="Se detectaron 2 posibles defectos.",
        )
    )
    return provider


@pytest.fixture
def vision_service(mock_provider: AsyncMock) -> VisionService:
    return VisionService(provider=mock_provider)


@pytest.fixture
def photos(tmp_path, monkeypatch: pytest.MonkeyPatch) -> list[InspectionPhoto]:
    """Fotos DENTRO del upload_dir (SEC.LFI.1): el servicio filtra las externas."""
    from app.core.config import settings

    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True)
    monkeypatch.setattr(settings, "upload_dir", str(upload_root))
    return [
        InspectionPhoto(
            id="photo-1",
            session_id="session-1",
            observation_id="obs-1",
            file_path=str(upload_root / "photo1.jpg"),
        ),
        InspectionPhoto(
            id="photo-2",
            session_id="session-1",
            observation_id="obs-2",
            file_path=str(upload_root / "photo2.jpg"),
        ),
    ]


@pytest.fixture
def observations() -> dict[str, InspectionObservation]:
    return {
        "photo-1": InspectionObservation(
            id="obs-1",
            session_id="session-1",
            category_id="exterior",
            item_id="pintura",
        ),
        "photo-2": InspectionObservation(
            id="obs-2",
            session_id="session-1",
            category_id="exterior",
            item_id="golpes",
        ),
    }


@pytest.mark.asyncio
async def test_analyze_photos_calls_provider(
    vision_service: VisionService,
    mock_provider: AsyncMock,
    photos: list[InspectionPhoto],
    observations: dict[str, InspectionObservation],
) -> None:
    """Verifies the service delegates to the provider with correct VisionImage list."""
    result = await vision_service.analyze_photos(photos, observations)

    mock_provider.analyze_images.assert_awaited_once()
    call_args = mock_provider.analyze_images.call_args[0][0]
    assert len(call_args) == 2
    assert all(isinstance(img, VisionImage) for img in call_args)
    assert call_args[0].photo_id == "photo-1"
    assert call_args[0].file_path.endswith("photo1.jpg")
    assert call_args[1].photo_id == "photo-2"
    assert call_args[1].file_path.endswith("photo2.jpg")
    assert "summary" in result
    assert "suggestions" in result


@pytest.mark.asyncio
async def test_analyze_photos_maps_suggestions_correctly(
    vision_service: VisionService,
    mock_provider: AsyncMock,
    photos: list[InspectionPhoto],
    observations: dict[str, InspectionObservation],
) -> None:
    """Verifies that each provider observation becomes a suggestion with correct fields."""
    result = await vision_service.analyze_photos(photos, observations)

    suggestions = result["suggestions"]
    assert len(suggestions) == 2

    # First suggestion
    s1 = suggestions[0]
    assert s1["photo_id"] == "photo-1"
    assert s1["observation_id"] == "obs-1"
    assert s1["category_id"] == "exterior"
    assert s1["item_id"] == "pintura"
    assert s1["status"] == "WARNING"
    assert s1["severity"] == "MEDIUM"
    assert s1["confidence"] == "MEDIUM"
    assert s1["notes"] == "Posible rayón en la pintura."
    assert s1["suggested_repair_cost"] == 150.0

    # Second suggestion
    s2 = suggestions[1]
    assert s2["photo_id"] == "photo-2"
    assert s2["observation_id"] == "obs-2"
    assert s2["category_id"] == "exterior"
    assert s2["item_id"] == "golpes"
    assert s2["status"] == "BAD"
    assert s2["severity"] == "HIGH"
    assert s2["confidence"] == "HIGH"
    assert s2["notes"] == "Abolladura en el panel lateral."
    assert s2["suggested_repair_cost"] == 450.0


@pytest.mark.asyncio
async def test_analyze_photos_skips_orphan_photos(
    vision_service: VisionService,
    mock_provider: AsyncMock,
    photos: list[InspectionPhoto],
    observations: dict[str, InspectionObservation],
) -> None:
    """Photos without a matching observation should be skipped silently."""
    # Add a photo that has no corresponding observation
    photos.append(
        InspectionPhoto(
            id="photo-orphan",
            session_id="session-1",
            observation_id="obs-orphan",
            file_path="/img/orphan.jpg",
        )
    )

    result = await vision_service.analyze_photos(photos, observations)
    suggestions = result["suggestions"]
    assert len(suggestions) == 2  # orphan skipped
    assert all(s["photo_id"] != "photo-orphan" for s in suggestions)


@pytest.mark.asyncio
async def test_analyze_photos_empty_input(
    vision_service: VisionService,
    mock_provider: AsyncMock,
) -> None:
    """Empty photos list should return empty suggestions."""
    result = await vision_service.analyze_photos([], {})
    assert result["suggestions"] == []
    assert "summary" in result


@pytest.mark.asyncio
async def test_analyze_photos_passes_summary(
    vision_service: VisionService,
    mock_provider: AsyncMock,
    photos: list[InspectionPhoto],
    observations: dict[str, InspectionObservation],
) -> None:
    """The provider summary should be forwarded as-is in the result."""
    result = await vision_service.analyze_photos(photos, observations)
    assert result["summary"] == "Se detectaron 2 posibles defectos."

