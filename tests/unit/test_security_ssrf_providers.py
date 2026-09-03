"""Tests de seguridad SEC.SSRF.1 — guard en ProviderHttpClient y providers.

No hay red: el guard se ejecuta ANTES de construir la petición httpx.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.providers.exceptions import ProviderConnectionError
from app.providers.http_client import ProviderHttpClient


@pytest.mark.asyncio
async def test_request_bloquea_url_interna() -> None:
    client = ProviderHttpClient(provider_name="test", base_url="https://www.mobile.de/")
    with pytest.raises(ProviderConnectionError):
        await client.request("GET", "http://169.254.169.254/latest/meta-data/")


@pytest.mark.asyncio
async def test_request_bloquea_localhost() -> None:
    client = ProviderHttpClient(provider_name="test", base_url="https://www.mobile.de/")
    with pytest.raises(ProviderConnectionError):
        await client.request("GET", "http://localhost:8001/api/v1/health")


@pytest.mark.asyncio
async def test_request_bloquea_esquema_file() -> None:
    client = ProviderHttpClient(provider_name="test")
    with pytest.raises(ProviderConnectionError):
        await client.request("GET", "file:///etc/passwd")


@pytest.mark.asyncio
async def test_ruta_relativa_contra_base_url_permitida() -> None:
    """Las rutas relativas usan base_url de confianza: no pasan por el guard
    y fallan solo al conectar (aquí mockeado)."""
    client = ProviderHttpClient(
        provider_name="test", base_url="https://www.mobile.de/"
    )
    fake_response = AsyncMock()
    # raise_for_status en httpx es SINCRONO: un AsyncMock devolvería una
    # coroutine nunca esperada.
    fake_response.raise_for_status = lambda: None
    fake_response.status_code = 200
    fake_response.headers = {"content-length": "10"}
    fake_response.aread = AsyncMock(return_value=b"0123456789")

    async def _aiter_bytes():
        yield b"0123456789"

    fake_response.aiter_bytes = lambda: _aiter_bytes()

    sent_urls: list[str] = []

    class FakeClient:
        is_closed = False

        def build_request(self, **kwargs):
            sent_urls.append(str(kwargs["url"]))
            return kwargs["url"]

        async def send(self, request, stream=False):
            return fake_response

    with patch.object(client, "_get_client", AsyncMock(return_value=FakeClient())):
        response = await client.request("GET", "/suchen/123")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# SEC.LFI.1 — InspectionService.upload_photo valida file_path (capa servicio)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_photo_rechaza_ruta_externa(tmp_path) -> None:
    from app.core.config import settings as cfg
    from app.services.inspection_service import InspectionService

    service = InspectionService(
        session_repo=AsyncMock(),
        observation_repo=AsyncMock(),
        photo_repo=AsyncMock(),
        vision_service=AsyncMock(),
    )

    original = cfg.upload_dir
    object.__setattr__(cfg, "upload_dir", str(tmp_path))
    try:
        with pytest.raises(ValueError):
            await service.upload_photo(
                session_id="s1",
                observation_id="o1",
                file_path="/etc/passwd",
            )
    finally:
        object.__setattr__(cfg, "upload_dir", original)
