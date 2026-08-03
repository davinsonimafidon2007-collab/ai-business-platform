"""Cliente HTTP profesional para proveedores con reintentos, timeouts y anti-bot.

Características (Task A.5):
  - httpx.AsyncClient reutilizable
  - Timeouts y retries con backoff exponencial + jitter
  - Rotación de User-Agent (Chrome/Firefox/Safari 2026)
  - Headers realistas (Sec-Fetch-*, sec-ch-ua)
  - Proxy opcional (PROVIDER_HTTP_PROXY)
  - Cookie string opcional (PROVIDER_HTTP_COOKIES)
  - Delay mínimo entre peticiones (PROVIDER_HTTP_MIN_DELAY_MS)
  - HTTP 403 → ProviderConnectionError (anti-bot), sin reintentos
  - HTTP 429 → ProviderRateLimitError (sí reintenta)
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any
from urllib.parse import urljoin

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
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
    """Cliente HTTP reutilizable para todos los proveedores."""

    def __init__(
        self,
        provider_name: str,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        user_agents: list[str] | None = None,
        default_headers: dict[str, str] | None = None,
        proxy: str | None = None,
        cookies: str | None = None,
        min_delay_ms: int | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = base_url
        self.timeout = (
            timeout
            if timeout is not None
            else float(getattr(settings, "provider_http_timeout", 30.0))
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(getattr(settings, "provider_http_max_retries", 3))
        )
        self.user_agents = user_agents or self._default_user_agents()
        self.default_headers = default_headers or self._default_headers()

        cfg_proxy = (getattr(settings, "provider_http_proxy", None) or "").strip()
        self.proxy = (proxy if proxy is not None else cfg_proxy) or None
        if self.proxy == "":
            self.proxy = None

        cfg_cookies = (getattr(settings, "provider_http_cookies", None) or "").strip()
        self.cookies = (cookies if cookies is not None else cfg_cookies) or None
        if self.cookies == "":
            self.cookies = None

        cfg_delay = int(getattr(settings, "provider_http_min_delay_ms", 0) or 0)
        self.min_delay_ms = min_delay_ms if min_delay_ms is not None else cfg_delay
        self._last_request_at: float = 0.0
        self._client: httpx.AsyncClient | None = None

    def _default_user_agents(self) -> list[str]:
        return [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
                "Gecko/20100101 Firefox/133.0"
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
            ),
            (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        ]

    def _default_headers(self) -> dict[str, str]:
        return {
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    def _get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            **self.default_headers,
            "User-Agent": self._get_random_user_agent(),
        }
        if self.cookies:
            headers["Cookie"] = self.cookies
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            kwargs: dict[str, Any] = {
                "base_url": self.base_url or "",
                "timeout": httpx.Timeout(self.timeout),
                "follow_redirects": True,
                "http2": False,
            }
            if self.proxy:
                kwargs["proxy"] = self.proxy
                logger.info(
                    "provider_http_client: proxy habilitado para %s",
                    self.provider_name,
                )
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> ProviderHttpClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _should_retry(self, exception: BaseException) -> bool:
        if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
            return True
        if isinstance(exception, httpx.HTTPStatusError):
            code = exception.response.status_code
            if code == 429 or 500 <= code < 600:
                return True
            return False
        return False

    def _log_retry(self, retry_state: Any) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        logger.warning(
            "provider_http_client: reintento %s/%s para %s — %s",
            retry_state.attempt_number,
            self.max_retries,
            self.provider_name,
            type(exc).__name__ if exc else "?",
        )

    async def _respect_min_delay(self) -> None:
        if self.min_delay_ms <= 0:
            return
        elapsed_ms = (time.monotonic() - self._last_request_at) * 1000
        remaining = self.min_delay_ms - elapsed_ms
        if remaining > 0:
            jitter = remaining * random.uniform(0.8, 1.2)
            await asyncio.sleep(jitter / 1000.0)

    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        full_url = url
        if self.base_url and not url.startswith("http"):
            full_url = urljoin(self.base_url.rstrip("/") + "/", url.lstrip("/"))

        request_headers = self._build_headers(headers)
        backoff_min = int(getattr(settings, "provider_http_retry_backoff_min", 1))
        backoff_max = int(getattr(settings, "provider_http_retry_backoff_max", 60))

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential_jitter(initial=backoff_min, max=backoff_max),
                retry=retry_if_exception(self._should_retry),
                reraise=True,
                before_sleep=self._log_retry,
            ):
                with attempt:
                    await self._respect_min_delay()
                    client = await self._get_client()
                    response = await client.request(
                        method=method,
                        url=full_url,
                        params=params,
                        headers=request_headers,
                        **kwargs,
                    )
                    self._last_request_at = time.monotonic()

                    if response.status_code == 403:
                        logger.error(
                            "provider_http_client: HTTP 403 anti-bot en %s (url=%s)",
                            self.provider_name,
                            full_url,
                        )
                        raise ProviderConnectionError(
                            f"{self.provider_name} bloqueó la petición (HTTP 403 anti-bot). "
                            "Configura PROVIDER_HTTP_PROXY (residencial) o "
                            "PROVIDER_HTTP_COOKIES de un navegador real.",
                            provider=self.provider_name,
                        )

                    response.raise_for_status()
                    return response

        except ProviderConnectionError:
            raise
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
                    f"Error del servidor {e.response.status_code} en {self.provider_name} "
                    f"después de {self.max_retries} intentos",
                    provider=self.provider_name,
                    attempts=self.max_retries,
                ) from e
            raise

        raise ProviderMaxRetriesExceededError(
            f"Máximo de reintentos agotado en {self.provider_name}",
            provider=self.provider_name,
            attempts=self.max_retries,
        )

    async def get(
        self, url: str, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        return await self.request("GET", url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request("POST", url, data=data, json=json, **kwargs)

    async def put(
        self, url: str, data: dict[str, Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        return await self.request("PUT", url, data=data, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)