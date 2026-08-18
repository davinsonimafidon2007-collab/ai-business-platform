from __future__ import annotations

import pytest

from app.providers.registry import ProviderRegistry


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


def test_ensure_default_providers_registers_de(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_mobile_de", True)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "mobile_de" in names
    assert "autoscout24" in names
    assert "es_market_fixture" not in names
    assert "coches_net_fixture" not in names


def test_ensure_default_providers_includes_es_when_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", True)
    monkeypatch.setattr(settings, "enable_mobile_de", True)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "mobile_de" in names
    assert "autoscout24" in names
    assert "es_market_fixture" in names


def test_ensure_default_providers_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_mobile_de", True)

    ProviderRegistry.ensure_default_providers()
    ProviderRegistry.ensure_default_providers()  # no ValueError
    assert len([n for n in ProviderRegistry.list_providers() if n == "mobile_de"]) == 1
    assert len([n for n in ProviderRegistry.list_providers() if n == "autoscout24"]) == 1
    assert "es_market_fixture" not in ProviderRegistry.list_providers()


def test_ensure_default_providers_spain_profile_auto_registers_es_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    monkeypatch.setattr(settings, "enable_mobile_de", True)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "mobile_de" in names
    assert "autoscout24" in names
    assert "es_market_fixture" in names
    assert "coches_net_fixture" in names
    assert "autoscout24_es" not in names  # HTTP: solo flag explícito


def test_ensure_default_providers_skips_mobile_de_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CRIT.001: mobile_de no se registra si enable_mobile_de=false."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_mobile_de", False)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "mobile_de" not in names
    assert "autoscout24" in names  # AS24-first: la fuente primaria siempre


def test_germany_profile_no_auto_es_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "es_market_fixture" not in names
    assert "coches_net_fixture" not in names


def test_explicit_flag_still_works_on_non_spain(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "PORTUGAL")
    monkeypatch.setattr(settings, "enable_es_market_fixture", True)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)

    ProviderRegistry.ensure_default_providers()
    assert "es_market_fixture" in ProviderRegistry.list_providers()


def test_disable_es_market_auto_blocks_spain_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "disable_es_market_auto", True)

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    assert "es_market_fixture" not in names
    assert "coches_net_fixture" not in names
