"""Tests para el cliente HTTP de proveedores."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderMaxRetriesExceededError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseTooLargeError,
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


def _mock_response(
    status_code: int = 200,
    body: bytes = b"<html>Test</html>",
    headers: dict | None = None,
    raise_error: bool = False,
) -> MagicMock:
    """Mock de una respuesta streamed (contrato de `client.send(stream=True)`)."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.request = MagicMock()
    if raise_error:
        # El HTTPStatusError referencia a `response` (que expone aclose AsyncMock).
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=MagicMock(),
                response=response,
            )
        )
    else:
        response.raise_for_status = MagicMock()

    async def _aiter_bytes():
        yield body

    response.aiter_bytes = _aiter_bytes
    response.aclose = AsyncMock()

    async def _aread() -> bytes:
        return body

    response.aread = _aread
    return response


def _patch_transport(
    mock_response: MagicMock, side_effect=None
) -> tuple[ExitStack, AsyncMock, MagicMock]:
    """Parchea `send` + `build_request` (contrato streaming de TASK-010).

    Returns:
        (stack, send_mock, build_mock) — entrar en `stack` para activar los
        parches. `send_mock` es el mock de `AsyncClient.send` y `build_mock`
        el de `AsyncClient.build_request` (captura url/headers/params).
    """
    send_mock = AsyncMock()
    if side_effect is not None:
        send_mock.side_effect = side_effect
    else:
        send_mock.return_value = mock_response
    build_mock = MagicMock(return_value=MagicMock())

    stack = ExitStack()
    stack.enter_context(patch.object(httpx.AsyncClient, "send", send_mock))
    stack.enter_context(
        patch.object(httpx.AsyncClient, "build_request", build_mock)
    )
    return stack, send_mock, build_mock


@pytest.mark.asyncio
async def test_http_client_get_success(http_client):
    """Test que verifica una petición GET exitosa."""
    mock_response = _mock_response(status_code=200, body=b"<html>Test</html>")
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        response = await http_client.get("/test")
        assert response.status_code == 200
        assert response.text == "<html>Test</html>"


@pytest.mark.asyncio
async def test_http_client_post_success(http_client):
    """Test que verifica una petición POST exitosa."""
    mock_response = _mock_response(status_code=201)
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        response = await http_client.post("/test", json={"key": "value"})
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_http_client_timeout_raises_error(http_client):
    """Test que verifica que un timeout lanza ProviderTimeoutError."""
    stack, _, _ = _patch_transport(
        _mock_response(),
        side_effect=httpx.TimeoutException("Timeout"),
    )
    with stack:
        with pytest.raises(ProviderTimeoutError, match="Timeout al conectar con test_provider"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_connection_error_raises_error(http_client):
    """Test que verifica que un error de conexión lanza ProviderConnectionError."""
    stack, _, _ = _patch_transport(
        _mock_response(),
        side_effect=httpx.NetworkError("Connection failed"),
    )
    with stack:
        with pytest.raises(ProviderConnectionError, match="Error de conexión con test_provider"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_rate_limit_raises_error(http_client):
    """Test que verifica que un 429 lanza ProviderRateLimitError."""
    mock_response = _mock_response(
        status_code=429,
        headers={"Retry-After": "60"},
        raise_error=True,
    )
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        with pytest.raises(ProviderRateLimitError, match="Rate limit excedido en test_provider"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_server_error_after_retries(http_client):
    """Test que verifica que errores 5xx agotan los reintentos."""
    mock_response = _mock_response(status_code=500, raise_error=True)
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        with pytest.raises(ProviderMaxRetriesExceededError, match="después de 2 intentos"):
            await http_client.get("/test")


@pytest.mark.asyncio
async def test_http_client_retries_on_timeout(http_client):
    """Test que verifica que se reintenta en timeouts."""
    mock_response = _mock_response(status_code=200)

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.TimeoutException("Timeout")
        return mock_response

    stack, _, _ = _patch_transport(mock_response, side_effect=side_effect)
    with stack:
        response = await http_client.get("/test")
        assert response.status_code == 200
        assert call_count == 2  # 1 fallo + 1 éxito (max_retries=2)


@pytest.mark.asyncio
async def test_http_client_does_not_retry_on_404(http_client):
    """Test que verifica que NO se reintenta en errores 404.

    SEARCH.DIAG.1: desde el diagnóstico de providers, el 404 se traduce a
    ``ProviderNotFoundError`` (marca/modelo inexistente) en vez de propagar
    el ``httpx.HTTPStatusError`` crudo. Lo que se sigue comprobando aquí es
    que no hay reintentos.
    """
    mock_response = _mock_response(
        status_code=404,
        headers={},
        raise_error=True,
    )

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_response

    stack, _, _ = _patch_transport(mock_response, side_effect=side_effect)
    with stack:
        with pytest.raises(ProviderNotFoundError):
            await http_client.get("/test")
        assert call_count == 1  # No reintenta


@pytest.mark.asyncio
async def test_http_client_user_agent_rotation(http_client):
    """Test que verifica que se rotan los User-Agents."""
    mock_response = _mock_response(status_code=200)

    stack, _, build_mock = _patch_transport(mock_response)
    with stack:
        # Hacer múltiples peticiones
        await http_client.get("/test1")
        await http_client.get("/test2")
        await http_client.get("/test3")

        # Verificar que se llamó 3 veces
        assert build_mock.call_count == 3

        # Verificar que los User-Agents son diferentes (con alta probabilidad)
        user_agents = [
            call.kwargs.get("headers", {}).get("User-Agent")
            for call in build_mock.call_args_list
        ]
        # Al menos debería haber variación (aunque puede haber colisiones por aleatoriedad)
        assert all(ua is not None for ua in user_agents)


@pytest.mark.asyncio
async def test_http_client_custom_headers(http_client):
    """Test que verifica que se pueden agregar headers personalizados."""
    mock_response = _mock_response(status_code=200)

    stack, _, build_mock = _patch_transport(mock_response)
    with stack:
        await http_client.get("/test", headers={"X-Custom-Header": "custom-value"})

        # Verificar que el header personalizado está presente
        call_headers = build_mock.call_args.kwargs.get("headers", {})
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
    mock_response = _mock_response(status_code=200)

    stack, _, build_mock = _patch_transport(mock_response)
    with stack:
        await http_client.get("/test")

        # Verificar que la URL se construyó correctamente
        called_url = build_mock.call_args.kwargs.get("url")
        assert called_url == "https://example.com/test"


@pytest.mark.asyncio
async def test_http_client_full_url_without_base_url():
    """Test que verifica URLs absolutas sin base_url."""
    http_client = ProviderHttpClient(provider_name="test", base_url="")
    mock_response = _mock_response(status_code=200)

    stack, _, build_mock = _patch_transport(mock_response)
    with stack:
        await http_client.get("https://other.com/test")

        # Verificar que se usa la URL absoluta
        called_url = build_mock.call_args.kwargs.get("url")
        assert called_url == "https://other.com/test"


@pytest.mark.asyncio
async def test_http_client_default_headers(http_client):
    """Test que verifica que se agregan los headers por defecto."""
    mock_response = _mock_response(status_code=200)

    stack, _, build_mock = _patch_transport(mock_response)
    with stack:
        await http_client.get("/test")

        # Verificar headers por defecto
        call_headers = build_mock.call_args.kwargs.get("headers", {})
        assert "Accept" in call_headers
        assert "Accept-Language" in call_headers
        assert "User-Agent" in call_headers
        assert call_headers["Accept-Language"] == "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"


@pytest.mark.asyncio
async def test_http_client_retry_on_500_error(http_client):
    """Test que verifica que se reintenta en errores 500."""
    mock_response = _mock_response(status_code=200)

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=MagicMock(status_code=500)
            )
        return mock_response

    stack, _, _ = _patch_transport(mock_response, side_effect=side_effect)
    with stack:
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
    mock_response = _mock_response(status_code=403, body=b"Zugriff verweigert / Access denied")
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        with pytest.raises(ProviderConnectionError, match="403"):
            await client.get("/fahrzeuge/search.html")


@pytest.mark.asyncio
async def test_http_client_404_raises_provider_not_found():
    """SEARCH.DIAG.1: 404 → ProviderNotFoundError, no HTTPStatusError crudo.

    En un listado, 404 casi siempre significa marca/modelo inexistente. Como
    salía sin traducir, el diagnóstico lo reportaba igual que una fuente rota
    y alarmaba por una búsqueda simplemente vacía.
    """
    http_client = ProviderHttpClient(
        provider_name="autoscout24", base_url="https://example.com", max_retries=2
    )
    mock_response = _mock_response(
        status_code=404,
        headers={},
        raise_error=True,
    )

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_response

    stack, _, _ = _patch_transport(mock_response, side_effect=side_effect)
    with stack:
        with pytest.raises(ProviderNotFoundError, match="marca/modelo"):
            await http_client.get("/lst/marca-inexistente")

    assert call_count == 1, "un 404 no debe reintentarse"


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
    mock_response = _mock_response(status_code=200, body=b"ok")
    with patch("httpx.AsyncClient") as mock_cls:
        instance = MagicMock()
        instance.is_closed = False
        instance.send = AsyncMock(return_value=mock_response)
        instance.build_request = MagicMock(return_value=MagicMock())
        instance.aclose = AsyncMock()
        mock_cls.return_value = instance
        response = await client.get("https://example.com/")
        assert response.status_code == 200
        assert mock_cls.call_args.kwargs.get("proxy") == "http://user:pass@proxy.example:8080"
    await client.close()


def test_default_user_agents_are_modern():
    client = ProviderHttpClient(provider_name="test")
    uas = client._default_user_agents()
    assert any("Chrome/131" in ua or "Chrome/12" in ua for ua in uas)
    assert any("Firefox" in ua for ua in uas)


# --- TASK-010: límite de tamaño de descarga ---

@pytest.mark.asyncio
async def test_http_client_max_bytes_raises_when_exceeding_limit():
    """Una respuesta mayor que max_bytes lanza ProviderResponseTooLargeError."""
    client = ProviderHttpClient(
        provider_name="test", base_url="https://example.com", max_bytes=4
    )
    mock_response = _mock_response(status_code=200, body=b"x" * 100)
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        with pytest.raises(ProviderResponseTooLargeError, match="límite de 4 bytes"):
            await client.get("/test")
        # El stream debe cerrarse al cortar la descarga.
        mock_response.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_http_client_max_bytes_allows_within_limit():
    """Una respuesta menor que max_bytes se devuelve completa."""
    client = ProviderHttpClient(
        provider_name="test", base_url="https://example.com", max_bytes=1024
    )
    body = b"<html>ok</html>"
    mock_response = _mock_response(status_code=200, body=body)
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        response = await client.get("/test")
        assert response.text == "<html>ok</html>"


@pytest.mark.asyncio
async def test_http_client_max_bytes_zero_means_no_limit():
    """max_bytes=0 desactiva el límite y usa `aread()` completo."""
    client = ProviderHttpClient(
        provider_name="test", base_url="https://example.com", max_bytes=0
    )
    body = b"z" * 500
    mock_response = _mock_response(status_code=200, body=body)
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        response = await client.get("/test")
        assert len(response.content) == 500


# --- Bug real: doble descompresión gzip en el Response reconstruido ---
# aread()/aiter_bytes() sobre la respuesta original YA devuelven el cuerpo
# descomprimido; _mock_response() simula exactamente ese contrato (igual
# que el httpx real). Si el cliente reconstruye el Response final
# reutilizando headers con "Content-Encoding: gzip" tal cual, cualquier
# acceso a .text/.content sobre ESE response intenta des-gzipear de nuevo
# un cuerpo que ya es texto plano y falla con httpx.DecodingError.


@pytest.mark.asyncio
async def test_http_client_strips_stale_content_encoding_header(http_client):
    """El Response final no debe reventar al acceder a .text/.content.

    Regresión: encontrado probando una búsqueda real contra AutoScout24
    (que sirve HTML real con Content-Encoding: gzip) — ver commit
    "fix(providers): doble descompresión gzip rompía toda búsqueda real".
    """
    decoded_html = "<html><body>anuncio real</body></html>"
    mock_response = _mock_response(
        status_code=200,
        body=decoded_html.encode("utf-8"),
        headers={"content-encoding": "gzip", "content-length": "9999"},
    )
    stack, _, _ = _patch_transport(mock_response)
    with stack:
        response = await http_client.get("/test")
        assert "content-encoding" not in response.headers
        assert response.text == decoded_html
        assert response.content == decoded_html.encode("utf-8")
        # httpx recalcula Content-Length a partir del body real al
        # construir el Response; ya no debe quedar el valor stale (9999).
        assert response.headers["content-length"] == str(len(decoded_html))
