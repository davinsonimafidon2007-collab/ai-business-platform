"""Unit tests for GeminiVisionProvider (TEST.PROV.GEMINI.1).

Igual que su hermano OpenAI: se mockea SOLO el borde externo
(httpx.AsyncClient). Todo el parsing, límites de tamaño, manejo de errores y
construcción de la petición es código real bajo test.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.models.vision import VisionConfidence, VisionImage, VisionSeverity
from app.providers.gemini_vision import GeminiVisionProvider, VisionProviderError


@pytest.fixture
def http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def provider(http_client: AsyncMock) -> GeminiVisionProvider:
    return GeminiVisionProvider(api_key="test-gemini-key", http_client=http_client)


def _gemini_payload(text: str) -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": text}], "role": "model"}}
        ]
    }


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    return resp


def _analysis_json() -> str:
    return json.dumps(
        {
            "observations": [
                {
                    "photo_id": "p1",
                    "status": "BAD",
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "notes": "Abolladura en la puerta",
                    "suggested_repair_cost": 450.0,
                }
            ],
            "summary": "Un defecto detectado",
        }
    )


# ---------------------------------------------------------------------------
# Constructor / entrada
# ---------------------------------------------------------------------------


def test_missing_api_key_raises() -> None:
    with pytest.raises(ValueError, match="API key"):
        GeminiVisionProvider(api_key="")


@pytest.mark.asyncio
async def test_empty_images_skips_http(provider: GeminiVisionProvider, http_client: AsyncMock) -> None:
    result = await provider.analyze_images([])
    assert result.observations == []
    http_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_remote_url_rejected(provider: GeminiVisionProvider, http_client: AsyncMock) -> None:
    with pytest.raises(VisionProviderError, match="path local"):
        await provider.analyze_images(
            [VisionImage(photo_id="p1", file_path="https://cdn.example.com/foto.jpg")]
        )
    http_client.post.assert_not_called()


# ---------------------------------------------------------------------------
# Petición y parsing con contenido real
# ---------------------------------------------------------------------------


async def _run_with_tmp_file(provider: GeminiVisionProvider, tmp_path) -> tuple[AsyncMock, object]:
    foto = tmp_path / "foto.jpg"
    foto.write_bytes(b"\xff\xd8\xff\xe0" + b"datos" * 10)
    http_post = AsyncMock(return_value=_ok_response(_gemini_payload(_analysis_json())))
    provider._http_client.post = http_post
    result = await provider.analyze_images(
        [VisionImage(photo_id="p1", file_path=str(foto))]
    )
    return http_post, result


@pytest.mark.asyncio
async def test_local_file_sent_as_base64_jpeg(provider: GeminiVisionProvider, tmp_path) -> None:
    http_post, result = await _run_with_tmp_file(provider, tmp_path)

    assert result.summary == "Un defecto detectado"
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert str(obs.status) == "BAD"
    assert obs.severity == VisionSeverity.HIGH
    assert obs.confidence == VisionConfidence.HIGH
    assert obs.suggested_repair_cost == 450.0

    url = http_post.call_args.args[0]
    assert ":generateContent?key=test-gemini-key" in url
    body = http_post.call_args.kwargs["json"]
    parts = body["contents"][0]["parts"]
    inline = [p for p in parts if "inlineData" in p]
    assert len(inline) == 1
    assert inline[0]["inlineData"]["mimeType"] == "image/jpeg"
    decoded = base64.b64decode(inline[0]["inlineData"]["data"])
    assert decoded.startswith(b"\xff\xd8\xff")


@pytest.mark.asyncio
async def test_data_url_used_inline(provider: GeminiVisionProvider, tmp_path) -> None:
    raw = b"\x89PNG\r\n\x1a\n" + b"pngdata" * 4
    b64 = base64.b64encode(raw).decode()
    http_post = AsyncMock(return_value=_ok_response(_gemini_payload(_analysis_json())))
    provider._http_client.post = http_post

    await provider.analyze_images(
        [VisionImage(photo_id="p1", file_path=f"data:image/png;base64,{b64}")]
    )

    body = http_post.call_args.kwargs["json"]
    inline = [p for p in body["contents"][0]["parts"] if "inlineData" in p]
    assert inline[0]["inlineData"]["mimeType"] == "image/png"


@pytest.mark.asyncio
async def test_good_photos_can_be_absent_from_observations(provider: GeminiVisionProvider, tmp_path) -> None:
    foto = tmp_path / "ok.jpg"
    foto.write_bytes(b"\xff\xd8\xff" + b"x" * 8)
    text = json.dumps({"observations": [], "summary": "Sin defectos"})
    provider._http_client.post = AsyncMock(return_value=_ok_response(_gemini_payload(text)))

    result = await provider.analyze_images([VisionImage(photo_id="p9", file_path=str(foto))])
    assert result.observations == []
    assert result.summary == "Sin defectos"


# ---------------------------------------------------------------------------
# Errores HTTP / red / parsing
# ---------------------------------------------------------------------------


def _status_response(status_code: int, text: str = "boom") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "fragment"),
    [(400, "Bad request"), (403, "API key"), (429, "Rate limit"), (500, "HTTP 500")],
)
async def test_http_errors_map_to_provider_error(
    provider: GeminiVisionProvider,
    tmp_path,
    status_code: int,
    fragment: str,
) -> None:
    foto = tmp_path / "f.jpg"
    foto.write_bytes(b"\xff\xd8\xff" + b"y")
    provider._http_client.post = AsyncMock(return_value=_status_response(status_code))

    with pytest.raises(VisionProviderError, match=fragment):
        await provider.analyze_images([VisionImage(photo_id="p1", file_path=str(foto))])


@pytest.mark.asyncio
async def test_timeout_maps_to_provider_error(provider: GeminiVisionProvider, tmp_path) -> None:
    foto = tmp_path / "f.jpg"
    foto.write_bytes(b"\xff\xd8\xff")
    provider._http_client.post = AsyncMock(side_effect=httpx.ReadTimeout("t"))

    with pytest.raises(VisionProviderError, match="[Tt]imed out"):
        await provider.analyze_images([VisionImage(photo_id="p1", file_path=str(foto))])


@pytest.mark.asyncio
async def test_network_error_maps_to_provider_error(provider: GeminiVisionProvider, tmp_path) -> None:
    foto = tmp_path / "f.jpg"
    foto.write_bytes(b"\xff\xd8\xff")
    provider._http_client.post = AsyncMock(side_effect=httpx.ConnectError("no dns"))

    with pytest.raises(VisionProviderError, match="Network error"):
        await provider.analyze_images([VisionImage(photo_id="p1", file_path=str(foto))])


@pytest.mark.asyncio
async def test_no_candidates_is_error(provider: GeminiVisionProvider, tmp_path) -> None:
    foto = tmp_path / "f.jpg"
    foto.write_bytes(b"\xff\xd8\xff")
    provider._http_client.post = AsyncMock(return_value=_ok_response({"candidates": []}))

    with pytest.raises(VisionProviderError, match="No candidates"):
        await provider.analyze_images([VisionImage(photo_id="p1", file_path=str(foto))])


@pytest.mark.asyncio
async def test_invalid_json_in_text_is_error(provider: GeminiVisionProvider, tmp_path) -> None:
    foto = tmp_path / "f.jpg"
    foto.write_bytes(b"\xff\xd8\xff")
    provider._http_client.post = AsyncMock(
        return_value=_ok_response(_gemini_payload("esto no es json {"))
    )

    with pytest.raises(VisionProviderError, match="Invalid JSON"):
        await provider.analyze_images([VisionImage(photo_id="p1", file_path=str(foto))])


@pytest.mark.asyncio
async def test_malformed_observation_skipped_valid_kept(provider: GeminiVisionProvider, tmp_path) -> None:
    foto = tmp_path / "f.jpg"
    foto.write_bytes(b"\xff\xd8\xff")
    text = json.dumps(
        {
            "observations": [
                {"photo_id": "bad", "severity": "NO_EXISTE"},
                {
                    "photo_id": "ok",
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "confidence": "LOW",
                    "notes": "Aranazo",
                    "suggested_repair_cost": None,
                },
            ],
            "summary": "mixto",
        }
    )
    provider._http_client.post = AsyncMock(return_value=_ok_response(_gemini_payload(text)))

    result = await provider.analyze_images([VisionImage(photo_id="p1", file_path=str(foto))])
    assert [o.photo_id for o in result.observations] == ["ok"]
    assert result.observations[0].confidence == VisionConfidence.LOW


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_available_true_on_200(provider: GeminiVisionProvider) -> None:
    resp = MagicMock()
    resp.status_code = 200
    provider._http_client.get = AsyncMock(return_value=resp)
    assert await provider.is_available() is True


@pytest.mark.asyncio
async def test_is_available_false_on_network_error(provider: GeminiVisionProvider) -> None:
    provider._http_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
    assert await provider.is_available() is False
