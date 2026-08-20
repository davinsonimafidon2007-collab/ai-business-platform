"""TASK 1 — contrato explícito del pipeline ES: fixture vs live.

``ES_DATA_MODE`` (settings) es el contrato maestro del pipeline de comparables
españoles y gobierna el registro de los fixtures:

- ``fixture`` (default): se registran y se loggea un WARNING visible al
  arrancar (hoy en día idéntico al comportamiento previo, pero ya no
  silencioso).
- ``live``: NO se registran bajo ninguna circunstancia (ni por perfil SPAIN,
  ni por flags ENABLE_*_FIXTURE, ni por llamadas runtime como las de
  ``SearchEngineService`` que re-invoca ``ensure_*`` en cada búsqueda).
- Valor inválido: RuntimeError en el startup (fail-fast).
"""

from __future__ import annotations

import logging

import pytest

from app.providers.registry import ProviderRegistry

ES_FIXTURE_SOURCES = (
    "es_market_fixture",
    "coches_net_fixture",
    "coches_net_html_fixture",
)


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


def _arrange(monkeypatch: pytest.MonkeyPatch, es_mode: str) -> None:
    """Perfil SPAIN (caso de uso principal) con flags de fixture apagados.

    Así se prueba exactamente el auto-registro silencioso que TASK 1 debe
    bloquear: si con esta configuración no se registran en ``live``, ningún
    otro escenario (flags explícitos aparte) lo hará.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    monkeypatch.setattr(settings, "enable_mobile_de", False)
    monkeypatch.setattr(settings, "es_data_mode", es_mode)


def test_fixture_mode_registers_es_fixtures_and_warns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Caso 1: ES_DATA_MODE=fixture (default) registra fixtures + WARNING."""
    _arrange(monkeypatch, "fixture")
    from app.core.config import settings

    # El HTML fixture no se auto-registra por perfil; con flag sí (en fixture).
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", True)

    with caplog.at_level(logging.WARNING, logger="app.providers.registry"):
        ProviderRegistry.ensure_default_providers()

    names = ProviderRegistry.list_providers()
    for src in ES_FIXTURE_SOURCES:
        assert src in names, f"{src} debería registrarse en modo fixture"
    # El warning explícito debe ser visible (nada de modo silencioso).
    assert any(
        "ES_DATA_MODE=fixture" in record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING
    )


def test_live_mode_registers_no_es_fixtures(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Caso 2: ES_DATA_MODE=live no registra fixtures ES (ni con perfil SPAIN)."""
    _arrange(monkeypatch, "live")

    with caplog.at_level(logging.INFO, logger="app.providers.registry"):
        ProviderRegistry.ensure_default_providers()

    names = ProviderRegistry.list_providers()
    assert "autoscout24" in names  # el resto del registry no cambia (AS24-first)
    for src in ES_FIXTURE_SOURCES:
        assert src not in names, f"{src} NO debe registrarse en modo live"
    assert any(
        "ES_DATA_MODE=live" in record.getMessage()
        for record in caplog.records
        if record.levelno == logging.INFO
    )


def test_live_mode_blocks_explicit_fixture_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso 2b: live gana sobre ENABLE_*_FIXTURE=true (contrato maestro)."""
    _arrange(monkeypatch, "live")
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_es_market_fixture", True)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", True)
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", True)

    ProviderRegistry.ensure_default_providers()

    names = ProviderRegistry.list_providers()
    for src in ES_FIXTURE_SOURCES:
        assert src not in names


def test_live_mode_blocks_runtime_auto_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso 2c: search_engine re-llama ensure_* en cada búsqueda; tampoco ahí.

    Sin este bloqueo, ES_DATA_MODE=live solo valdría hasta la primera
    búsqueda: SearchEngineService.ensure_registry re-registraría los
    fixtures por perfil SPAIN en runtime (auto-registro silencioso).
    """
    _arrange(monkeypatch, "live")

    ProviderRegistry.ensure_es_market_fixture()
    ProviderRegistry.ensure_coches_net_fixture()
    ProviderRegistry.ensure_coches_net_html_fixture()

    names = ProviderRegistry.list_providers()
    for src in ES_FIXTURE_SOURCES:
        assert src not in names


def test_invalid_mode_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso 3: ES_DATA_MODE inválido → RuntimeError (fail-fast en startup)."""
    _arrange(monkeypatch, "production")

    with pytest.raises(RuntimeError, match="ES_DATA_MODE"):
        ProviderRegistry.ensure_default_providers()
