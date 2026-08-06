from __future__ import annotations

import pytest

from app.providers.registry import ProviderRegistry


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


def test_ensure_default_providers_registers_de(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_es_market_fixture", False)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "mobile_de" in names
    assert "autoscout24" in names
    assert "es_market_fixture" not in names


def test_ensure_default_providers_includes_es_when_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_es_market_fixture", True)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "mobile_de" in names
    assert "autoscout24" in names
    assert "es_market_fixture" in names


def test_ensure_default_providers_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_es_market_fixture", False)

    ProviderRegistry.ensure_default_providers()
    ProviderRegistry.ensure_default_providers()  # no ValueError
    assert len([n for n in ProviderRegistry.list_providers() if n == "mobile_de"]) == 1
    assert len([n for n in ProviderRegistry.list_providers() if n == "autoscout24"]) == 1
    assert "es_market_fixture" not in ProviderRegistry.list_providers()
