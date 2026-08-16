"""Unit tests for the OpenAIVisionProvider.

Tests validate:
- Correct HTTP request format to OpenAI API
- Proper parsing of API responses into VisionInspectionResult
- Error handling (HTTP errors, timeouts, invalid JSON)
- Empty input handling
- is_available check
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.models.vision import (
    VisionConfidence,
    VisionImage,
    VisionInspectionResult,
    VisionSeverity,
)
from app.providers.openai_vision import OpenAIVisionProvider, VisionProviderError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_key() -> str:
    return "sk-test-fake-key-12345"


def _make_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> AsyncMock:
    """Helper to create a mock httpx.Response without spec restrictions."""
    resp = AsyncMock()
    resp.status_code = status_code
    resp.text = text
    # httpx.Response.json() is synchronous, so use MagicMock (not AsyncMock)
    resp.json = MagicMock(return_value=json_data or {})

    async def _raise_for_status() -> None:
        if status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{status_code} Error",
                request=AsyncMock(),
                response=resp,
            )

    resp.raise_for_status = _raise_for_status
    return resp


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Mock httpx.AsyncClient to avoid real HTTP calls."""
    client = AsyncMock(spec=httpx.AsyncClient)

    # Default: return a successful response
    default_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "observations": [
                                    {
                                        "photo_id": "photo-1",
                                        "status": "WARNING",
                                        "severity": "MEDIUM",
                                        "confidence": "HIGH",
                                        "notes": "Rayón superficial en la pintura del capó.",
                                        "suggested_repair_cost": 150.0,
                                    },
                                    {
                                        "photo_id": "photo-2",
                                        "status": "BAD",
                                        "severity": "HIGH",
                                        "confidence": "HIGH",
                                        "notes": "Abolladura profunda en el panel lateral derecho.",
                                        "suggested_repair_cost": 450.0,
                                    },
                                ],
                                "summary": "Se detectaron 2 defectos: un rayón superficial y una abolladura profunda.",
                            }
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 850,
                "completion_tokens": 120,
                "total_tokens": 970,
            },
        },
    )

    client.post = AsyncMock(return_value=default_response)
    client.get = AsyncMock()

    return client


@pytest.fixture
def provider(
    api_key: str, mock_http_client: AsyncMock
) -> OpenAIVisionProvider:
    return OpenAIVisionProvider(
        api_key=api_key,
        model="gpt-4o",
        max_tokens=2000,
        temperature=0.1,
        http_client=mock_http_client,
    )


@pytest.fixture
def sample_images() -> list[VisionImage]:
    return [
        VisionImage(
            photo_id="photo-1",
            file_path="https://storage.example.com/photos/photo1.jpg",
        ),
        VisionImage(
            photo_id="photo-2",
            file_path="https://storage.example.com/photos/photo2.jpg",
        ),
    ]


# ===========================================================================
# Constructor
# ===========================================================================


def test_constructor_requires_api_key() -> None:
    """Provider must raise ValueError if no API key is provided."""
    with pytest.raises(ValueError, match="OpenAI API key is required"):
        OpenAIVisionProvider(api_key="", http_client=AsyncMock())


def test_constructor_with_valid_api_key(api_key: str) -> None:
    """Provider should be created successfully with a valid API key."""
    provider = OpenAIVisionProvider(
        api_key=api_key,
        model="gpt-4o",
        http_client=AsyncMock(),
    )
    assert provider is not None


# ===========================================================================
# analyze_images
# ===========================================================================


@pytest.mark.asyncio
async def test_analyze_images_empty_input(
    provider: OpenAIVisionProvider,
) -> None:
    """Empty image list should return empty result without calling API."""
    result = await provider.analyze_images([])
    assert isinstance(result, VisionInspectionResult)
    assert result.observations == []
    assert result.summary == "No se proporcionaron imágenes."


@pytest.mark.asyncio
async def test_analyze_images_sends_correct_request(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Verify the HTTP request sent to OpenAI has the correct structure."""
    await provider.analyze_images(sample_images)

    mock_http_client.post.assert_awaited_once()
    call_args = mock_http_client.post.call_args

    # Check URL
    assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"

    # Check headers
    headers = call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer sk-test-fake-key-12345"
    assert headers["Content-Type"] == "application/json"

    # Check body structure
    body = call_args[1]["json"]
    assert body["model"] == "gpt-4o"
    assert body["max_tokens"] == 2000
    assert body["temperature"] == 0.1
    assert body["response_format"] == {"type": "json_object"}

    # Check messages
    messages = body["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"

    content = messages[0]["content"]
    assert isinstance(content, list)
    assert len(content) == 4  # system text + user text + 2 images

    # First part is the system prompt
    assert content[0]["type"] == "text"

    # Image parts
    assert content[2]["type"] == "image_url"
    assert content[2]["image_url"]["url"] == sample_images[0].file_path
    assert content[3]["image_url"]["url"] == sample_images[1].file_path


@pytest.mark.asyncio
async def test_analyze_images_parses_result_correctly(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Verify the provider correctly parses the OpenAI response into VisionInspectionResult."""
    result = await provider.analyze_images(sample_images)

    assert isinstance(result, VisionInspectionResult)
    assert len(result.observations) == 2

    # First observation
    obs1 = result.observations[0]
    assert obs1.photo_id == "photo-1"
    assert obs1.status == "WARNING"
    assert obs1.severity == VisionSeverity.MEDIUM
    assert obs1.confidence == VisionConfidence.HIGH
    assert "Rayón superficial" in obs1.notes
    assert obs1.suggested_repair_cost == 150.0

    # Second observation
    obs2 = result.observations[1]
    assert obs2.photo_id == "photo-2"
    assert obs2.status == "BAD"
    assert obs2.severity == VisionSeverity.HIGH
    assert obs2.confidence == VisionConfidence.HIGH
    assert "Abolladura profunda" in obs2.notes
    assert obs2.suggested_repair_cost == 450.0

    # Summary
    assert "2 defectos" in result.summary


@pytest.mark.asyncio
async def test_analyze_images_skips_good_status(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Observations with status=GOOD should be excluded."""
    good_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test456",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "observations": [
                                    {
                                        "photo_id": "photo-1",
                                        "status": "GOOD",
                                        "severity": "LOW",
                                        "confidence": "HIGH",
                                        "notes": "Sin defectos visibles.",
                                        "suggested_repair_cost": None,
                                    },
                                    {
                                        "photo_id": "photo-2",
                                        "status": "WARNING",
                                        "severity": "MEDIUM",
                                        "confidence": "MEDIUM",
                                        "notes": "Pequeño roce en paragolpes.",
                                        "suggested_repair_cost": 80.0,
                                    },
                                ],
                                "summary": "Vehículo en buen estado general con un leve roce.",
                            }
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 500},
        },
    )
    mock_http_client.post = AsyncMock(return_value=good_response)

    result = await provider.analyze_images(sample_images)

    # Only the WARNING observation should remain
    assert len(result.observations) == 1
    assert result.observations[0].photo_id == "photo-2"
    assert result.observations[0].status == "WARNING"


@pytest.mark.asyncio
async def test_analyze_images_adds_placeholder_for_unmentioned_photos(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
) -> None:
    """Photos not mentioned in the response should get a low-confidence placeholder."""
    partial_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test789",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "observations": [
                                    {
                                        "photo_id": "photo-1",
                                        "status": "BAD",
                                        "severity": "HIGH",
                                        "confidence": "HIGH",
                                        "notes": "Golpe importante en puerta del conductor.",
                                        "suggested_repair_cost": 600.0,
                                    }
                                ],
                                "summary": "Se detectó un golpe importante.",
                            }
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 400},
        },
    )
    mock_http_client.post = AsyncMock(return_value=partial_response)

    images = [
        VisionImage(photo_id="photo-1", file_path="https://example.com/1.jpg"),
        VisionImage(photo_id="photo-2", file_path="https://example.com/2.jpg"),
    ]

    result = await provider.analyze_images(images)

    assert len(result.observations) == 2

    # photo-2 should have placeholder
    placeholder = [o for o in result.observations if o.photo_id == "photo-2"][0]
    assert placeholder.status == "WARNING"
    assert placeholder.confidence == VisionConfidence.LOW
    assert placeholder.suggested_repair_cost is None
    assert "No se pudo analizar" in placeholder.notes


# ===========================================================================
# Error handling
# ===========================================================================


@pytest.mark.asyncio
async def test_analyze_images_http_401(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """HTTP 401 should raise VisionProviderError about authentication."""
    error_response = _make_response(status_code=401, text='{"error": {"message": "Invalid API key"}}')
    mock_http_client.post = AsyncMock(return_value=error_response)

    with pytest.raises(VisionProviderError, match="Authentication failed"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_http_429(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """HTTP 429 should raise VisionProviderError about rate limit."""
    error_response = _make_response(status_code=429, text='{"error": {"message": "Rate limit exceeded"}}')
    mock_http_client.post = AsyncMock(return_value=error_response)

    with pytest.raises(VisionProviderError, match="Rate limit exceeded"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_http_400(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """HTTP 400 should raise VisionProviderError with the error body."""
    error_response = _make_response(status_code=400, text='{"error": {"message": "Invalid image format"}}')
    mock_http_client.post = AsyncMock(return_value=error_response)

    with pytest.raises(VisionProviderError, match="Bad request"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_timeout(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Timeout should raise VisionProviderError."""
    mock_http_client.post = AsyncMock(
        side_effect=httpx.TimeoutException(
            "Connection timed out", request=AsyncMock()
        )
    )

    with pytest.raises(VisionProviderError, match="Request timed out"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_network_error(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Generic network error should raise VisionProviderError."""
    mock_http_client.post = AsyncMock(
        side_effect=httpx.RequestError(
            "DNS resolution failed", request=AsyncMock()
        )
    )

    with pytest.raises(VisionProviderError, match="Network error"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_invalid_json_response(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Invalid JSON in the response should raise VisionProviderError."""
    bad_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is not valid JSON {broken",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 100},
        },
    )
    mock_http_client.post = AsyncMock(return_value=bad_response)

    with pytest.raises(VisionProviderError, match="Failed to parse JSON"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_empty_response_content(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Empty content string should raise VisionProviderError."""
    empty_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 100},
        },
    )
    mock_http_client.post = AsyncMock(return_value=empty_response)

    with pytest.raises(VisionProviderError, match="Empty content"):
        await provider.analyze_images(sample_images)


@pytest.mark.asyncio
async def test_analyze_images_no_choices(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Response with no choices should raise VisionProviderError."""
    no_choices_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [],
            "usage": {"total_tokens": 100},
        },
    )
    mock_http_client.post = AsyncMock(return_value=no_choices_response)

    with pytest.raises(VisionProviderError, match="Empty response"):
        await provider.analyze_images(sample_images)


# ===========================================================================
# is_available
# ===========================================================================


@pytest.mark.asyncio
async def test_is_available_returns_true(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
) -> None:
    """is_available should return True when API responds with 200."""
    ok_response = AsyncMock()
    ok_response.status_code = 200
    mock_http_client.get = AsyncMock(return_value=ok_response)

    result = await provider.is_available()
    assert result is True
    mock_http_client.get.assert_awaited_once_with(
        "https://api.openai.com/v1/models",
        headers={"Authorization": "Bearer sk-test-fake-key-12345"},
    )


@pytest.mark.asyncio
async def test_is_available_returns_false_on_error(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
) -> None:
    """is_available should return False when the API call fails."""
    mock_http_client.get = AsyncMock(
        side_effect=httpx.RequestError("Connection error", request=AsyncMock())
    )

    result = await provider.is_available()
    assert result is False


# ===========================================================================
# Invalid severity/confidence values
# ===========================================================================


@pytest.mark.asyncio
async def test_analyze_images_invalid_severity_falls_back_to_medium(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Unrecognized severity strings should default to MEDIUM."""
    bad_severity_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "observations": [
                                    {
                                        "photo_id": "photo-1",
                                        "status": "WARNING",
                                        "severity": "UNKNOWN_LEVEL",
                                        "confidence": "UNKNOWN_CONF",
                                        "notes": "Defecto detectado.",
                                        "suggested_repair_cost": 100.0,
                                    }
                                ],
                                "summary": "Defecto detectado.",
                            }
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 100},
        },
    )
    mock_http_client.post = AsyncMock(return_value=bad_severity_response)

    result = await provider.analyze_images(sample_images)

    assert len(result.observations) == 2
    # First photo has invalid values
    obs = result.observations[0]
    assert obs.severity == VisionSeverity.MEDIUM  # fallback
    assert obs.confidence == VisionConfidence.MEDIUM  # fallback


# ===========================================================================
# Negative repair cost handling
# ===========================================================================


@pytest.mark.asyncio
async def test_analyze_images_negative_repair_cost_returns_none(
    provider: OpenAIVisionProvider,
    mock_http_client: AsyncMock,
    sample_images: list[VisionImage],
) -> None:
    """Negative repair costs should be coerced to None."""
    negative_cost_response = _make_response(
        status_code=200,
        json_data={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "observations": [
                                    {
                                        "photo_id": "photo-1",
                                        "status": "WARNING",
                                        "severity": "LOW",
                                        "confidence": "HIGH",
                                        "notes": "Defecto menor.",
                                        "suggested_repair_cost": -50.0,
                                    }
                                ],
                                "summary": "Defecto menor.",
                            }
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 100},
        },
    )
    mock_http_client.post = AsyncMock(return_value=negative_cost_response)

    result = await provider.analyze_images(sample_images)

    obs = result.observations[0]
    assert obs.suggested_repair_cost is None

