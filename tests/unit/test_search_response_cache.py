"""Tests SEARCH.ORCH.1 — caché de respuestas de búsqueda (fail-soft)."""

from __future__ import annotations

from typing import Any

import pytest

from app.api.v1.schemas.search import SearchAPIRequest
from app.services import search_response_cache as cache_module
from app.services.search_response_cache import (
    build_search_cache_key,
    get_cached_search_response,
    set_cached_search_response,
)


def _request(**overrides: Any) -> SearchAPIRequest:
    payload: dict[str, Any] = {"query": "bmw 320d", "providers": ["mobile_de"]}
    payload.update(overrides)
    return SearchAPIRequest(**payload)


@pytest.fixture(autouse=True)
def _enable_cache(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "search_cache_enabled", True)
    monkeypatch.setattr(settings, "search_cache_ttl", 300)


# =============================================================================
# Clave estable
# =============================================================================


class TestCacheKey:
    def test_key_stable_for_identical_requests(self) -> None:
        assert build_search_cache_key(_request()) == build_search_cache_key(_request())

    def test_key_differs_for_different_query(self) -> None:
        assert build_search_cache_key(_request()) != build_search_cache_key(
            _request(query="golf")
        )

    def test_key_differs_for_different_page(self) -> None:
        assert build_search_cache_key(_request(page=1)) != build_search_cache_key(
            _request(page=2)
        )


# =============================================================================
# Comportamiento fail-soft
# =============================================================================


class TestDisabledByDefault:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "search_cache_enabled", False)

        async def _fail_get(key: str) -> str:
            raise AssertionError("no debe tocar Redis si está desactivada")

        monkeypatch.setattr(cache_module, "cache_get", _fail_get)
        assert await get_cached_search_response("k") is None

    @pytest.mark.asyncio
    async def test_set_is_noop_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "search_cache_enabled", False)

        async def _fail_set(key: str, value: str, ttl_seconds: int) -> None:
            raise AssertionError("no debe tocar Redis si está desactivada")

        monkeypatch.setattr(cache_module, "cache_set", _fail_set)
        await set_cached_search_response("k", "{}")  # no debe lanzar


class TestFailSoft:
    @pytest.mark.asyncio
    async def test_get_swallows_redis_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _boom(key: str) -> str:
            raise ConnectionError("redis down")

        monkeypatch.setattr(cache_module, "cache_get", _boom)
        assert await get_cached_search_response("k") is None

    @pytest.mark.asyncio
    async def test_set_swallows_redis_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _boom(key: str, value: str, ttl_seconds: int) -> None:
            raise ConnectionError("redis down")

        monkeypatch.setattr(cache_module, "cache_set", _boom)
        await set_cached_search_response("k", "{}")  # no debe lanzar

    @pytest.mark.asyncio
    async def test_corrupt_entry_is_a_miss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _raw(key: str) -> str:
            return "{not-json"

        monkeypatch.setattr(cache_module, "cache_get", _raw)
        assert await get_cached_search_response("k") is None

    @pytest.mark.asyncio
    async def test_roundtrip_hit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store: dict[str, str] = {}

        async def _get(key: str) -> str | None:
            return store.get(key)

        async def _set(key: str, value: str, ttl_seconds: int) -> None:
            store[key] = value

        monkeypatch.setattr(cache_module, "cache_get", _get)
        monkeypatch.setattr(cache_module, "cache_set", _set)

        assert await get_cached_search_response("k") is None  # miss
        await set_cached_search_response("k", '{"results": []}')
        assert await get_cached_search_response("k") == {"results": []}  # hit
