from app.models.inspection import InspectionObservation, InspectionPhoto
from app.providers.vision_provider import MockVisionProvider
from app.services.vision_service import VisionService
import pytest


@pytest.mark.asyncio
async def test_mock_provider_returns_reviewable_suggestion() -> None:
    observation = InspectionObservation(
        session_id="session", category_id="exterior", item_id="pintura"
    )
    photo = InspectionPhoto(
        session_id="session", observation_id=observation.id, file_path="/car.jpg"
    )

    result = await VisionService(MockVisionProvider()).analyze_photos(
        [photo], {photo.id: observation}
    )

    suggestion = result["suggestions"][0]
    assert suggestion["category_id"] == "exterior"
    assert suggestion["status"] == "WARNING"
    assert suggestion["suggested_repair_cost"] == 150.0


@pytest.mark.asyncio
async def test_service_ignores_photo_without_inspection_observation() -> None:
    photo = InspectionPhoto(session_id="session", observation_id="missing", file_path="/car.jpg")

    result = await VisionService(MockVisionProvider()).analyze_photos([photo], {})

    assert result["suggestions"] == []
