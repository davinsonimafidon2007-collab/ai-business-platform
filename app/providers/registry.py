from __future__ import annotations

import logging

from app.providers.base import VehicleProvider

logger = logging.getLogger(__name__)


def _is_spain_import_profile() -> bool:
    """True si el perfil de costes destino es España."""
    from app.core.config import settings

    raw = getattr(settings, "default_import_cost_profile", None) or "SPAIN"
    key = str(raw).strip().upper()
    return key in {"SPAIN", "ES", "ESP", "ESPAÑA", "ESPANA"}


def _coches_net_real_enabled() -> bool:
    """True si el provider REAL de coches.net debe registrarse (TASK 4)."""
    from app.core.config import settings

    return bool(getattr(settings, "enable_coches_net", False))


def _es_fixtures_blocked() -> bool:
    """True si ``ES_DATA_MODE=live``: fixtures ES bloqueados (TASK 1).

    En modo live el pipeline de comparables españoles NO puede caer en datos
    simulados de forma silenciosa, venga el registro del flag explícito o del
    auto-registro por perfil SPAIN/ES.
    """
    from app.core.config import settings

    return str(getattr(settings, "es_data_mode", "fixture")) == "live"


class ProviderRegistry:
    """Registro central de proveedores de vehículos.

    Permite registrar, obtener y listar providers de forma desacoplada.
    Los providers se identifican por su source_name.
    """

    _providers: dict[str, VehicleProvider] = {}

    @classmethod
    def register(cls, provider: VehicleProvider) -> None:
        """Registra un provider en el registro.

        Args:
            provider: Instancia del provider a registrar.

        Raises:
            ValueError: Si ya existe un provider con el mismo source_name.
        """
        name = provider.source_name
        if name in cls._providers:
            raise ValueError(f"Provider '{name}' is already registered")
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> VehicleProvider:
        """Obtiene un provider por su nombre.

        Args:
            name: Nombre del provider (ej: 'mobile_de', 'autoscout24').

        Returns:
            Instancia del provider solicitado.

        Raises:
            KeyError: Si no existe un provider con ese nombre.
        """
        if name not in cls._providers:
            raise KeyError(f"Provider '{name}' is not registered. Available: {list(cls._providers.keys())}")
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """Devuelve la lista de nombres de providers registrados."""
        return list(cls._providers.keys())

    @classmethod
    def unregister(cls, name: str) -> None:
        """Elimina un provider del registro.

        Args:
            name: Nombre del provider a eliminar.
        """
        cls._providers.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Limpia todos los providers registrados (útil en tests)."""
        cls._providers.clear()

    @classmethod
    def ensure_es_market_fixture(cls, enabled: bool | None = None) -> None:
        """Registra es_market_fixture si enabled y aún no está.

        Idempotente. ``enabled=None`` → lee settings.enable_es_market_fixture
        y/o activa auto-registro cuando el perfil de costes es SPAIN/ES
        (salvo ``settings.disable_es_market_auto``).

        TASK 1: con ``ES_DATA_MODE=live`` el auto-registro/flag está bloqueado
        (el pipeline ES no debe usar datos simulados en modo live). Solo un
        ``enabled=True`` explícito (programático, p.ej. tests) lo fuerza.
        """
        if enabled is None:
            from app.core.config import settings

            if _es_fixtures_blocked():
                from app.core.logging import get_logger

                get_logger(__name__).info(
                    "ES_DATA_MODE=live: registro de es_market_fixture bloqueado "
                    "(datos simulados desactivados)."
                )
                return
            enabled = (
                bool(getattr(settings, "enable_es_market_fixture", False))
                or (
                    _is_spain_import_profile()
                    and not getattr(settings, "disable_es_market_auto", False)
                )
            )
        if not enabled:
            return
        if "es_market_fixture" in cls._providers:
            return
        from app.providers.es_market_fixture import EsMarketFixtureProvider

        cls.register(EsMarketFixtureProvider())

    @classmethod
    def ensure_coches_net(cls, enabled: bool | None = None) -> None:
        """Registra el provider REAL de coches.net si enabled y aún no está.

        TASK 4 (AUD-005): antes este scraper existía pero no se registraba
        nunca (solo import bajo TYPE_CHECKING), así que era inalcanzable en
        runtime y la búsqueda "España" se servía de fixtures.

        Idempotente. No hace HTTP al construir la instancia. Si coches.net
        bloquea la petición, el provider lanza la excepción correspondiente
        y el orquestador la reporta como ProviderIssue: nunca hay fallback
        silencioso a datos simulados.
        """
        if enabled is None:
            enabled = _coches_net_real_enabled()
        if not enabled:
            return
        if "coches_net" in cls._providers:
            return
        from app.core.config import settings
        from app.providers.coches_net import BASE_URL as COCHES_NET_BASE_URL
        from app.providers.coches_net import CochesNetProvider
        from app.providers.http_client import ProviderHttpClient

        client = ProviderHttpClient(
            provider_name="coches_net",
            base_url=COCHES_NET_BASE_URL,
            timeout=settings.provider_http_timeout,
            max_retries=settings.provider_http_max_retries,
        )
        cls.register(
            CochesNetProvider(http_client=client, base_url=COCHES_NET_BASE_URL)
        )

    @classmethod
    def ensure_coches_net_fixture(cls, enabled: bool | None = None) -> None:
        """Registra coches_net_fixture si enabled y aún no está.

        Idempotente. ``enabled=None`` → lee settings.enable_coches_net_fixture
        y/o activa auto-registro cuando el perfil de costes es SPAIN/ES
        (salvo ``settings.disable_es_market_auto``).

        TASK 1: con ``ES_DATA_MODE=live`` el auto-registro/flag está bloqueado
        (el pipeline ES no debe usar datos simulados en modo live). Solo un
        ``enabled=True`` explícito (programático, p.ej. tests) lo fuerza.

        TASK 4: además, en modo no-live, el auto-registro por perfil
        SPAIN/ES se desactiva cuando el provider REAL de coches.net está
        activo, para no mezclar anuncios reales y simulados de la misma
        fuente en los mismos resultados. El flag explícito
        ``enable_coches_net_fixture`` sigue teniendo prioridad (útil para
        desarrollo offline).
        """
        if enabled is None:
            from app.core.config import settings

            if _es_fixtures_blocked():
                from app.core.logging import get_logger

                get_logger(__name__).info(
                    "ES_DATA_MODE=live: registro de coches_net_fixture bloqueado "
                    "(datos simulados desactivados)."
                )
                return
            enabled = bool(
                getattr(settings, "enable_coches_net_fixture", False)
            ) or (
                _is_spain_import_profile()
                and not getattr(settings, "disable_es_market_auto", False)
                and not _coches_net_real_enabled()
            )
        if not enabled:
            return
        if "coches_net_fixture" in cls._providers:
            return
        from app.providers.coches_net_fixture import CochesNetFixtureProvider

        cls.register(CochesNetFixtureProvider())

    @classmethod
    def ensure_coches_net_html_fixture(cls, enabled: bool | None = None) -> None:
        """Registra coches_net_html_fixture si enabled y aún no está.

        Idempotente. ``enabled=None`` → lee settings.enable_coches_net_html_fixture.
        No se auto-registra por perfil SPAIN/ES (solo flag explícito).

        TASK 1: con ``ES_DATA_MODE=live`` el flag está bloqueado (el pipeline
        ES no debe usar datos simulados en modo live). Solo un ``enabled=True``
        explícito (programático, p.ej. tests) lo fuerza.
        """
        if enabled is None:
            from app.core.config import settings

            if _es_fixtures_blocked():
                from app.core.logging import get_logger

                get_logger(__name__).info(
                    "ES_DATA_MODE=live: registro de coches_net_html_fixture "
                    "bloqueado (datos simulados desactivados)."
                )
                return
            enabled = bool(getattr(settings, "enable_coches_net_html_fixture", False))
        if not enabled:
            return
        if "coches_net_html_fixture" in cls._providers:
            return
        from app.providers.coches_net_html import CochesNetHtmlFixtureProvider

        cls.register(CochesNetHtmlFixtureProvider())

    @classmethod
    def ensure_default_providers(cls) -> None:
        """Registra los providers de búsqueda/comparables usados en runtime.

        Idempotente. No hace HTTP al construir las instancias (el cliente
        HTTP se crea lazy y solo abre conexión en el primer ``search`` real).
        - mobile_de: solo si settings.enable_mobile_de (CRIT.001: opcional,
          requiere proxy residencial anti-bot)
        - autoscout24: siempre (fuente primaria, AS24-first)
        - autoscout24_es: solo si settings.enable_autoscout24_es
        - coches_net (REAL): si settings.enable_coches_net (TASK 4 / AUD-005)
        - es_market_fixture / coches_net_fixture / coches_net_html_fixture:
          SOLO con ES_DATA_MODE=fixture (TASK 1: modo explícito). En ``live``
          no se registran jamás; un ES_DATA_MODE inválido lanza RuntimeError
          (fail-fast en el startup). Dentro de fixture, coches_net_fixture
          además se desactiva si el provider real de coches.net está activo
          (TASK 4: no mezclar datos reales y simulados de la misma fuente).

        Reutiliza settings-provider_http_* para el cliente anti-bot, igual
        que las dependencias de API (get_mobile_de_provider /
        get_autoscout24_provider).
        """
        if "mobile_de" not in cls._providers:
            from app.core.config import settings

            if getattr(settings, "enable_mobile_de", False):
                from app.providers.http_client import ProviderHttpClient

                # Playwright opcional (sin cuenta): si está habilitado y disponible,
                # usa browser headless, sino cae a httpx. No requiere proxy.
                if getattr(settings, "enable_mobile_de_playwright", False):
                    try:
                        from app.providers.mobile_de_playwright import (
                            MobileDePlaywrightProvider,  # noqa: F401
                        )

                        use_pw = True
                    except ImportError:
                        use_pw = False
                else:
                    use_pw = False

                client = ProviderHttpClient(
                    provider_name="mobile_de",
                    base_url="https://suchen.mobile.de",
                    timeout=settings.provider_http_timeout,
                    max_retries=settings.provider_http_max_retries,
                )
                if use_pw:
                    from app.providers.mobile_de_playwright import MobileDePlaywrightProvider

                    cls.register(
                        MobileDePlaywrightProvider(
                            http_client=client, base_url="https://suchen.mobile.de"
                        )
                    )
                else:
                    from app.providers.mobile_de import MobileDeProvider

                    cls.register(
                        MobileDeProvider(
                            http_client=client, base_url="https://suchen.mobile.de"
                        )
                    )

        if "autoscout24" not in cls._providers:
            from app.core.config import settings
            from app.providers.autoscout24 import AutoScout24Provider
            from app.providers.http_client import ProviderHttpClient

            client = ProviderHttpClient(
                provider_name="autoscout24",
                base_url="https://www.autoscout24.de",
                timeout=settings.provider_http_timeout,
                max_retries=settings.provider_http_max_retries,
            )
            cls.register(
                AutoScout24Provider(
                    http_client=client, base_url="https://www.autoscout24.de"
                )
            )

        if "autoscout24_es" not in cls._providers:
            from app.core.config import settings

            if getattr(settings, "enable_autoscout24_es", False):
                from app.providers.autoscout24_es import AutoScout24EsProvider
                from app.providers.http_client import ProviderHttpClient

                client = ProviderHttpClient(
                    provider_name="autoscout24_es",
                    base_url="https://www.autoscout24.es",
                    timeout=settings.provider_http_timeout,
                    max_retries=settings.provider_http_max_retries,
                )
                cls.register(
                    AutoScout24EsProvider(
                        http_client=client,
                        base_url="https://www.autoscout24.es",
                    )
                )

        # TASK 1 — el modo ES debe ser explícito, nunca silencioso.
        from app.core.config import settings
        from app.core.logging import get_logger

        logger = get_logger(__name__)

        es_mode = getattr(settings, "es_data_mode", "fixture")
        if es_mode not in ("fixture", "live"):
            raise RuntimeError(
                f"ES_DATA_MODE inválido: '{es_mode}'. Debe ser 'fixture' o 'live'."
            )

        if es_mode == "fixture":
            logger.warning(
                "ES_DATA_MODE=fixture: el pipeline de comparables españoles usa "
                "datos SIMULADOS (coches_net_fixture, es_market_fixture) salvo "
                "que el provider real de coches.net esté activo (enable_coches_net). "
                "No usar fixtures en producción para decisiones de compra reales."
            )
            # Provider REAL de coches.net antes que su fixture: si está activo,
            # el fixture equivalente no se auto-registra (TASK 4 / AUD-005).
            cls.ensure_coches_net()
            cls.ensure_es_market_fixture()
            cls.ensure_coches_net_fixture()
            cls.ensure_coches_net_html_fixture()
        else:
            logger.info("ES_DATA_MODE=live: fixtures ES NO se registran.")
            # TASK 2 — coches_net real (scraping con degradación explícita:
            # si el HTML falla o hay bloqueo anti-bot, propaga ProviderParsingError
            # / ProviderConnectionError; nunca cae a fixtures en silencio).
            cls.ensure_coches_net()
