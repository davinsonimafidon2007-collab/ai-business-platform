"""Cliente HTTP profesional para proveedores con reintentos, timeouts y manejo de errores."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any
from urllib.parse import urljoin

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderMaxRetriesExceededError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = get_logger(__name__)


class ProviderHttpClient:
    """Cliente HTTP reutilizable para todos los proveedores.

    Características:
    - httpx.AsyncClient reutilizable
    - Timeouts configurables
    - Retries con backoff exponencial
    - Rotación de User-Agent
    - Headers centralizados
    - Manejo de errores específicos
    """

    def __init__(
        self,
        provider_name: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        user_agents: list[str] | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agents = user_agents or self._default_user_agents()
        self.default_headers = default_headers or self._default_headers()

        self._client: httpx.AsyncClient | None = None

    def _default_user_agents(self) -> list[str]:
        """Lista de User-Agents para rotación."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]

    def _default_headers(self) -> dict[str, str]:
        """Headers por defecto para todas las peticiones."""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _get_random_user_agent(self) -> str:
        """Obtiene un User-Agent aleatorio de la lista."""
        return random.choice(self.user_agents)

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Construye los headers para una petición."""
        headers = {**self.default_headers, "User-Agent": self._get_random_user_agent()}
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente HTTP."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> ProviderHttpClient:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.close()

    def _should_retry(self, exception: BaseException) -> bool:
        """Determina si una excepción debe ser reintentada."""
        # Reintentar en errores de conexión y timeouts
        if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
            return True
        # Reintentar en rate limits (429)
        if isinstance(exception, httpx.HTTPStatusError) and exception.response.status_code == 429:
            return True
        # No reintentar en errores 4xx (excepto 429)
        if isinstance(exception, httpx.HTTPStatusError) and 400 <= exception.response.status_code < 500:
            return False
        # Reintentar en errores 5xx
        if isinstance(exception, httpx.HTTPStatusError) and 500 <= exception.response.status_code < 600:
            return True
        return False

    def _before_sleep(self, retry_state: RetryCallState) -> None:
        """Callback antes de cada reintento."""
        if retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            if isinstance(exception, httpx.HTTPStatusError) and exception.response.status_code == 429:
                retry_after = exception.response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after else retry_state.next_action.sleep if retry_state.next_action else 1
                logger.warning(
                    "Rate limit alcanzado en %s. Esperando %ss antes de reintentar...",
                    self.provider_name, wait_time,
                )
            else:
                logger.info(
                    "Reintentando petición a %s (intento %s/%s)...",
                    self.provider_name, retry_state.attempt_number, self.max_retries,
                )

    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Realiza una petición HTTP con reintentos y manejo de errores.

        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL del endpoint
            params: Parámetros de query string
            headers: Headers adicionales
            **kwargs: Argumentos adicionales para httpx

        Returns:
            Response de httpx

        Raises:
            ProviderTimeoutError: Si la petición excede el timeout
            ProviderConnectionError: Si hay error de conexión
            ProviderRateLimitError: Si se excede el rate limit
            ProviderMaxRetriesExceededError: Si se exceden los reintentos
        """
        request_headers = self._build_headers(headers)
        if not self.base_url or url.startswith("http"):
            full_url = url
        else:
            full_url = urljoin(f"{self.base_url}/", url.lstrip("/"))

        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(self._should_retry),
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=60),
                reraise=True,
                before_sleep=self._before_sleep,
            ):
                with attempt:
                    client = await self._get_client()
                    response = await client.request(
                        method=method,
                        url=full_url,
                        params=params,
                        headers=request_headers,
                        **kwargs,
                    )
                    response.raise_for_status()
                    return response

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                f"Timeout al conectar con {self.provider_name}",
                provider=self.provider_name,
                timeout=self.timeout,
            ) from e

        except httpx.NetworkError as e:
            raise ProviderConnectionError(
                f"Error de conexión con {self.provider_name}",
                provider=self.provider_name,
                original_error=e,
            ) from e

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    f"Rate limit excedido en {self.provider_name}",
                    provider=self.provider_name,
                    retry_after=int(retry_after) if retry_after else None,
                ) from e

            if 500 <= e.response.status_code < 600:
                raise ProviderMaxRetriesExceededError(
                    f"Error del servidor {e.response.status_code} en {self.provider_name} después de {self.max_retries} intentos",
                    provider=self.provider_name,
                    attempts=self.max_retries,
                ) from e

            # Re-lanzar otros errores HTTP
            raise

    async def get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> httpx.Response:
        """Realiza una petición GET."""
        return await self.request("GET", url, params=params, **kwargs)

    async def post(
        self, url: str, data: dict[str, Any] | None = None, json: dict[str, Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        """Realiza una petición POST."""
        return await self.request("POST", url, data=data, json=json, **kwargs)

    async def put(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> httpx.Response:
        """Realiza una petición PUT."""
        return await self.request("PUT", url, data=data, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Realiza una petición DELETE."""
        return await self.request("DELETE", url, **kwargs)