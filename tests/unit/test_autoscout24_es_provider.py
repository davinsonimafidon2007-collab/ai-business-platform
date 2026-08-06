from __future__ import annotations

from app.core.config import settings
from app.providers.autoscout24_es import BASE_URL_ES, AutoScout24EsProvider
from app.providers.registry import ProviderRegistry


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


def test_source_name_and_base_url() -> None:
    p = AutoScout24EsProvider()
    assert p.source_name == "autoscout24_es"
    assert "autoscout24.es" in (p._base_url or BASE_URL_ES)


def test_not_registered_when_flag_false(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    ProviderRegistry.ensure_default_providers()
    assert "autoscout24_es" not in ProviderRegistry.list_providers()
    assert "mobile_de" in ProviderRegistry.list_providers()
    assert "autoscout24" in ProviderRegistry.list_providers()


def test_registered_when_flag_true(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_autoscout24_es", True)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    ProviderRegistry.ensure_default_providers()
    assert "autoscout24_es" in ProviderRegistry.list_providers()
    p = ProviderRegistry.get("autoscout24_es")
    assert p.source_name == "autoscout24_es"


def test_idempotent(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_autoscout24_es", True)
    ProviderRegistry.ensure_default_providers()
    ProviderRegistry.ensure_default_providers()
    assert ProviderRegistry.list_providers().count("autoscout24_es") == 1 or (
        ProviderRegistry.list_providers().count("autoscout24_es") == 0
        and "autoscout24_es" in ProviderRegistry.list_providers()
    )
    # count of name in list is 1
    assert sum(1 for n in ProviderRegistry.list_providers() if n == "autoscout24_es") == 1
