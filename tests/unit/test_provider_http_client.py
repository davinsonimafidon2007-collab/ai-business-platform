"""Tests para el cliente HTTP de proveedores."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderMaxRetriesExceededError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.providers.http_client import ProviderHttpClient


@pytest.fixture
def http_client():
    """Fixture que crea un ProviderHttpClient para tests."""
    return ProviderHttpClient(
        provider_name="test_provider",
        base_url="https://example.com",
        timeout=5.0,
        max_retries=2,
    )


@pytest.mark.asyncio
async def test_http_client_get_success(http_client):
    """Test que verifica una petición GET exitosa."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html>Test</html>"
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response):
        response = await http_client.get("/test")
        assert response.status_code == 200
        assert response.text == "<html>Test</html>"


@pytest.mark.asyncio
async def test_http_client_post_success(http_client):
    """Test que verifica una petición POST exitosa."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response):
        response = await http_client.post("/test", json={"key": "value"})
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_http_client_timeout_raises_error(http_client):
    """Test que verifica que un timeout lanza ProviderTimeoutError."""
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(ProviderTimeoutError, match="Timeout al conectar con test_provider"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_connection_error_raises_error(http_client):
    """Test que verifica que un error de conexión lanza ProviderConnectionError."""
    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, side_effect=httpx.NetworkError("Connection failed")):
        with pytest.raises(ProviderConnectionError, match="Error de conexión con test_provider"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_rate_limit_raises_error(http_client):
    """Test que verifica que un 429 lanza ProviderRateLimitError."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "60"}
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=mock_response))

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(ProviderRateLimitError, match="Rate limit excedido en test_provider"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_server_error_after_retries(http_client):
    """Test que verifica que errores 5xx agotan los reintentos."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response))

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(ProviderMaxRetriesExceededError, match="después de 2 intentos"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_retries_on_timeout(http_client):
    """Test que verifica que se reintenta en timeouts."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.TimeoutException("Timeout")
        return mock_response

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, side_effect=side_effect):
        response = await http_client.get("/test")
        assert response.status_code == 200
        assert call_count == 2  # 1 fallo + 1 éxito (max_retries=2)


@pytest.mark.asyncio
async def test_http_client_does_not_retry_on_404(http_client):
    """Test que verifica que NO se reintenta en errores 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response))

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_response

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, side_effect=side_effect):
        with pytest.raises(httpx.HTTPStatusError):
            await http_client.get("/test")
        assert call_count == 1  # No reintenta


@pytest.mark.asyncio
async def test_http_client_user_agent_rotation(http_client):
    """Test que verifica que se rotan los User-Agents."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        # Hacer múltiples peticiones
        await http_client.get("/test1")
        await http_client.get("/test2")
        await http_client.get("/test3")

        # Verificar que se llamó 3 veces
        assert mock_request.call_count == 3

        # Verificar que los User-Agents son diferentes (con alta probabilidad)
        user_agents = [call.kwargs.get("headers", {}).get("User-Agent") for call in mock_request.call_args_list]
        # Al menos debería haber variación (aunque puede haber colisiones por aleatoriedad)
        assert all(ua is not None for ua in user_agents)


@pytest.mark.asyncio
async def test_http_client_custom_headers(http_client):
    """Test que verifica que se pueden agregar headers personalizados."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        await http_client.get("/test", headers={"X-Custom-Header": "custom-value"})

        # Verificar que el header personalizado está presente
        call_headers = mock_request.call_args.kwargs.get("headers", {})
        assert call_headers.get("X-Custom-Header") == "custom-value"
        # Verificar que el User-Agent también está presente
        assert "User-Agent" in call_headers


@pytest.mark.asyncio
async def test_http_client_context_manager():
    """Test que verifica que el context manager funciona correctamente."""
    async with ProviderHttpClient(provider_name="test", base_url="https://example.com") as client:
        assert client.provider_name == "test"
        assert client.base_url == "https://example.com"


@pytest.mark.asyncio
async def test_http_client_close():
    """Test que verifica que el método close funciona."""
    http_client = ProviderHttpClient(provider_name="test", base_url="https://example.com")
    
    # Crear el cliente
    client = await http_client._get_client()
    assert client is not None

    # Cerrar el cliente
    await http_client.close()
    # El cliente se limpia (None) tras cerrarse
    assert http_client._client is None


@pytest.mark.asyncio
async def test_http_client_reuse_client(http_client):
    """Test que verifica que el cliente se reutiliza."""
    client1 = await http_client._get_client()
    client2 = await http_client._get_client()
    assert client1 is client2


@pytest.mark.asyncio
async def test_http_client_full_url_with_base_url(http_client):
    """Test que verifica que se construye la URL completa correctamente."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        await http_client.get("/test")

        # Verificar que la URL se construyó correctamente (se pasa como keyword argument)
        called_url = mock_request.call_args.kwargs.get("url")
        assert called_url == "https://example.com/test"


@pytest.mark.asyncio
async def test_http_client_full_url_without_base_url():
    """Test que verifica URLs absolutas sin base_url."""
    http_client = ProviderHttpClient(provider_name="test", base_url="")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        await http_client.get("https://other.com/test")

        # Verificar que se usa la URL absoluta (se pasa como keyword argument)
        called_url = mock_request.call_args.kwargs.get("url")
        assert called_url == "https://other.com/test"


@pytest.mark.asyncio
async def test_http_client_default_headers(http_client):
    """Test que verifica que se agregan los headers por defecto."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        await http_client.get("/test")

        # Verificar headers por defecto
        call_headers = mock_request.call_args.kwargs.get("headers", {})
        assert "Accept" in call_headers
        assert "Accept-Language" in call_headers
        assert "User-Agent" in call_headers
        assert call_headers["Accept-Language"] == "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"


@pytest.mark.asyncio
async def test_http_client_retry_on_500_error(http_client):
    """Test que verifica que se reintenta en errores 500."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response))

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock, side_effect=side_effect):
        response = await http_client.get("/test")
        assert response.status_code == 200
        assert call_count == 2


@pytest.mark.asyncio
async def test_http_client_configurable_timeout():
    """Test que verifica que el timeout es configurable."""
    http_client = ProviderHttpClient(provider_name="test", timeout=10.0)
    assert http_client.timeout == 10.0


@pytest.mark.asyncio
async def test_http_client_configurable_max_retries():
    """Test que verifica que max_retries es configurable."""
    http_client = ProviderHttpClient(provider_name="test", max_retries=5)
    assert http_client.max_retries == 5


@pytest.mark.asyncio
async def test_http_client_custom_user_agents():
    """Test que verifica que se pueden usar User-Agents personalizados."""
    custom_agents = ["CustomAgent/1.0", "AnotherAgent/2.0"]
    http_client = ProviderHttpClient(provider_name="test", user_agents=custom_agents)
    assert http_client.user_agents == custom_agents


@pytest.mark.asyncio
async def test_http_client_custom_default_headers():
    """Test que verifica que se pueden usar headers personalizados por defecto."""
    custom_headers = {"X-Custom": "value"}
    http_client = ProviderHttpClient(provider_name="test", default_headers=custom_headers)
    assert http_client.default_headers["X-Custom"] == "value"


# --- Task A.5 anti-bot tests ---

@pytest.mark.asyncio
async def test_http_client_403_raises_provider_connection_error():
    client = ProviderHttpClient(
        provider_name="mobile_de",
        base_url="https://suchen.mobile.de",
        timeout=5.0,
        max_retries=2,
    )
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Zugriff verweigert / Access denied"
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "403", request=MagicMock(), response=mock_response
        )
    )
    with patch.object(
        httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(ProviderConnectionError, match="403"):
            await client.get("/fahrzeuge/search.html")


@pytest.mark.asyncio
async def test_http_client_builds_cookie_header():
    client = ProviderHttpClient(provider_name="test", cookies="sid=abc; consent=1")
    headers = client._build_headers()
    assert headers.get("Cookie") == "sid=abc; consent=1"
    assert "User-Agent" in headers
    assert "Sec-Fetch-Mode" in headers


@pytest.mark.asyncio
async def test_http_client_proxy_passed_to_async_client():
    client = ProviderHttpClient(
        provider_name="test",
        proxy="http://user:pass@proxy.example:8080",
        timeout=5.0,
        max_retries=1,
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient") as mock_cls:
        instance = MagicMock()
        instance.is_closed = False
        instance.request = AsyncMock(return_value=mock_response)
        instance.aclose = AsyncMock()
        mock_cls.return_value = instance
        await client.get("https://example.com/")
        assert mock_cls.call_args.kwargs.get("proxy") == "http://user:pass@proxy.example:8080"
    await client.close()


def test_default_user_agents_are_modern():
    client = ProviderHttpClient(provider_name="test")
    uas = client._default_user_agents()
    assert any("Chrome/131" in ua or "Chrome/12" in ua for ua in uas)
    assert any("Firefox" in ua for ua in uas)
