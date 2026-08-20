from __future__ import annotations

from app.providers.base import VehicleProvider


def _is_spain_import_profile() -> bool:
    """True si el perfil de costes destino es España."""
    from app.core.config import settings

    raw = getattr(settings, "default_import_cost_profile", None) or "SPAIN"
    key = str(raw).strip().upper()
    return key in {"SPAIN", "ES", "ESP", "ESPAÑA", "ESPANA"}


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
    def ensure_coches_net_fixture(cls, enabled: bool | None = None) -> None:
        """Registra coches_net_fixture si enabled y aún no está.

        Idempotente. ``enabled=None`` → lee settings.enable_coches_net_fixture
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
                    "ES_DATA_MODE=live: registro de coches_net_fixture bloqueado "
                    "(datos simulados desactivados)."
                )
                return
            enabled = (
                bool(getattr(settings, "enable_coches_net_fixture", False))
                or (
                    _is_spain_import_profile()
                    and not getattr(settings, "disable_es_market_auto", False)
                )
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
        - coches_net: solo con ES_DATA_MODE=live (TASK 2, scraping real)
        - es_market_fixture / coches_net_fixture / coches_net_html_fixture:
          SOLO con ES_DATA_MODE=fixture (TASK 1: modo explícito). En ``live``
          no se registran jamás; un ES_DATA_MODE inválido lanza RuntimeError
          (fail-fast en el startup).

        Reutiliza settings-provider_http_* para el cliente anti-bot, igual
        que las dependencias de API (get_mobile_de_provider /
        get_autoscout24_provider).
        """
        if "mobile_de" not in cls._providers:
            from app.core.config import settings

            if getattr(settings, "enable_mobile_de", True):
                from app.providers.http_client import ProviderHttpClient
                from app.providers.mobile_de import MobileDeProvider

                client = ProviderHttpClient(
                    provider_name="mobile_de",
                    base_url="https://suchen.mobile.de",
                    timeout=settings.provider_http_timeout,
                    max_retries=settings.provider_http_max_retries,
                )
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
                "datos SIMULADOS (coches_net_fixture, es_market_fixture). "
                "No usar en producción para decisiones de compra reales."
            )
            cls.ensure_es_market_fixture()
            cls.ensure_coches_net_fixture()
            cls.ensure_coches_net_html_fixture()
        else:
            logger.info("ES_DATA_MODE=live: fixtures ES NO se registran.")
            # TASK 2 — coches_net real (scraping con degradación explícita:
            # si el HTML falla o hay bloqueo anti-bot, propaga ProviderParsingError
            # / ProviderConnectionError; nunca cae a fixtures en silencio).
            if "coches_net" not in cls._providers:
                from app.providers.coches_net import CochesNetProvider
                from app.providers.http_client import ProviderHttpClient

                client = ProviderHttpClient(
                    provider_name="coches_net",
                    base_url="https://www.coches.net",
                    timeout=settings.provider_http_timeout,
                    max_retries=settings.provider_http_max_retries,
                )
                cls.register(CochesNetProvider(http_client=client))
