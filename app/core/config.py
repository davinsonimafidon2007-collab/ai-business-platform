import os
from typing import Any, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Business Platform API"
    app_description: str = "API for the AI Business Platform."
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"
    app_mode: Literal["personal", "multiuser"] = "personal"
    """Intención de producto (documentación); NO controla la autenticación.

    El bypass de login tiene una única fuente de verdad: ``auth_disabled``.
    Para uso personal sin registro/login hay que activar ``AUTH_DISABLED=true``
    (y ``NEXT_PUBLIC_AUTH_DISABLED=true`` en el frontend). Dejar ``app_mode``
    en ``personal`` sin ``auth_disabled`` mantiene la auth JWT normal.
    """
    app_url: str = "http://localhost:3000"
    """Frontend URL for constructing email links and CORS."""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_business_platform"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"

    auth_disabled: bool = False
    """Si True, no exige JWT: inyecta usuario local ADMIN (uso personal).

    Activar solo en máquina local / uso personal (``AUTH_DISABLED=true``).
    No usar en un despliegue público: cualquiera con acceso al puerto sería
    ADMIN. En producción real dejar ``false``.
    """

    allow_auth_disabled_in_prod: bool = False
    """Override explícito para permitir ``AUTH_DISABLED=true`` en production.

    Por defecto la app **no arranca** si ``environment=production`` y
    ``auth_disabled=true`` (fail-fast, PERS.CLOSE.1). Solo poner a ``true`` si
    sabes que el puerto no está expuesto públicamente.
    """

    @model_validator(mode="after")
    def validate_jwt_secret_for_env(self) -> "Settings":
        if self.environment == "test":
            if not self.jwt_secret_key:
                object.__setattr__(
                    self,
                    "jwt_secret_key",
                    "test_secret_key_that_is_at_least_32_characters_long_1234567890",
                )
            return self

        if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set and at least 32 characters in "
                f"environment={self.environment!r}"
            )
        return self

    @model_validator(mode="after")
    def auth_disabled_safe_for_test(self) -> "Settings":
        """En test la auth debe seguir ON por defecto (tests de JWT/401).

        El valor ``AUTH_DISABLED=true`` del ``.env`` local (uso personal) no debe
        filtrarse a la suite de tests: sin él, los tests de auth/middleware
        fallarían (401 esperados que pasan a 200).

        El escape NO puede ser el propio ``AUTH_DISABLED`` del OS: al correr en
        Docker con el flag personal, compose lo inyecta siempre en el entorno y
        la protección quedaba anulada (E2E.MANUAL.PASS.1: 13 tests rojos por
        contaminación). Se usa una variable dedicada, ``AUTH_DISABLED_IN_TESTS``,
        que solo se activa a propósito. En development/production se respeta el
        valor del ``.env``.
        """
        if self.environment != "test":
            return self

        opt_in = os.environ.get("AUTH_DISABLED_IN_TESTS", "").strip().lower()
        if opt_in not in {"true", "1"}:
            object.__setattr__(self, "auth_disabled", False)
        return self

    @model_validator(mode="before")
    @classmethod
    def _ignore_env_auth_disabled_under_pytest(cls, data: Any) -> Any:
        """Bajo pytest, ``AUTH_DISABLED`` del OS no se hereda por defecto.

        Varios tests construyen ``Settings()`` con ``patch.dict(os.environ, ...)``
        para probar reglas de producción (CORS, JWT). En una máquina de uso
        personal ``AUTH_DISABLED=true`` está siempre en el entorno, se colaba en
        esos Settings y disparaba el fail-fast de producción antes que la regla
        bajo test (E2E.MANUAL.PASS.1: 6 tests de CORS/config en rojo).

        Para pedirlo a propósito en un test existe ``AUTH_DISABLED_IN_TESTS``.
        Fuera de pytest no se toca nada: el runtime real respeta el ``.env``.
        """
        if not isinstance(data, dict):
            return data
        if "PYTEST_CURRENT_TEST" not in os.environ:
            return data
        if os.environ.get("AUTH_DISABLED_IN_TESTS", "").strip().lower() in {"true", "1"}:
            return data
        # pydantic-settings ya ha volcado el valor del entorno en ``data``, así
        # que no basta con comprobar si la clave falta: hay que sobrescribirla.
        return {**data, "auth_disabled": False}

    @model_validator(mode="after")
    def auth_disabled_forbidden_in_production(self) -> "Settings":
        """production + AUTH_DISABLED=true → no arranca (PERS.CLOSE.1).

        Con la auth desactivada cualquiera con acceso al puerto sería ADMIN.
        Solo se permite con el override explícito
        ``ALLOW_AUTH_DISABLED_IN_PROD=true``.
        """
        if (
            self.environment == "production"
            and self.auth_disabled
            and not self.allow_auth_disabled_in_prod
        ):
            raise ValueError(
                "AUTH_DISABLED=true no está permitido con ENVIRONMENT=production: "
                "cualquiera con acceso al puerto sería ADMIN. Usa AUTH_DISABLED=false "
                "o, si el puerto no es público y lo asumes, "
                "ALLOW_AUTH_DISABLED_IN_PROD=true."
            )
        return self

    @model_validator(mode="after")
    def validate_cors_for_env(self) -> "Settings":
        """Enforce strict CORS defaults for production (SEC-001).

        In development/test the existing localhost/Capacitor defaults are kept
        so local DX is not broken. In production:
        - `cors_origins` must be a non-empty, explicit list (no ``*``).
        - origins that look development-only (localhost / capacitor / ionic)
          are rejected when the whole list is dev-only.
        - a wildcard `cors_allow_headers` is hardened to an explicit list.
        """
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.environment == "production":
            if not origins:
                raise ValueError(
                    "CORS_ORIGINS must be set to explicit origins in production"
                )
            if "*" in origins:
                raise ValueError("CORS_ORIGINS cannot include '*' in production")
            dev_like = all(
                o.startswith("http://localhost")
                or o.startswith("https://localhost")
                or o.startswith("capacitor://")
                or o.startswith("ionic://")
                for o in origins
            )
            if dev_like:
                raise ValueError(
                    "CORS_ORIGINS in production looks like development-only origins. "
                    "Set real frontend HTTPS origins."
                )
            if self.cors_allow_headers.strip() == "*":
                object.__setattr__(
                    self,
                    "cors_allow_headers",
                    "Authorization,Content-Type,Accept,X-Request-ID,X-API-Key,X-Requested-With",
                )
        return self
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7  # 7 días
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080,capacitor://localhost,ionic://localhost,http://localhost,https://localhost"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "Authorization,Content-Type,Accept,X-Request-ID,X-API-Key,X-Requested-With"
    rate_limit_global: int = 60
    rate_limit_login: int = 5
    rate_limit_register: int = 10
    rate_limit_premium: int = 120
    rate_limit_user: int = 30
    rate_limit_readonly: int = 10
    password_reset_token_expire_hours: int = 1

    # API Key configuration
    api_key_prefix: str = "abp_live"
    api_key_length: int = 32

    # Audit configuration
    audit_retention_days: int = 365

    # Provider HTTP client configuration
    provider_http_timeout: float = 30.0
    provider_http_max_retries: int = 3
    provider_http_retry_backoff_min: int = 1
    provider_http_retry_backoff_max: int = 60
    # Proxy residencial (ej. http://user:pass@host:port). Vacío = sin proxy.
    provider_http_proxy: str = ""
    # Cookie header de navegador real (ej. "sid=abc; consent=1")
    provider_http_cookies: str = ""
    # Delay mínimo entre peticiones (ms). 0 = off. Prod: 800–1500
    provider_http_min_delay_ms: int = 0

    # =========================================================================
    # Scheduler / Jobs configuration
    # =========================================================================
    cache_refresh_interval: int = 3600
    """Seconds between automatic market cache refreshes (default 1h)."""

    search_history_ttl: int = 2592000
    """Seconds to keep search history records (default 30 days)."""

    market_cache_ttl: int = 21600
    """TTL in seconds for cached market data (default 6h)."""

    max_concurrent_jobs: int = 4
    """Maximum number of jobs that can run concurrently."""

    comparable_providers: str = ""
    """Allowlist de sources para comparables (ej. "mobile_de,autoscout24,es_market_fixture").

    Lista separada por comas. Vacía = usar todos los del ProviderRegistry
    (comportamiento actual). Se usa como fallback cuando el request no trae
    ``comparable_providers`` explícito.
    """

    enable_scheduler: bool = True
    """Master toggle to enable/disable the background scheduler."""

    provider_canary_interval: int = 21600
    """Seconds between provider canary runs (default 6h). 0 = disabled."""

    search_order_interval: int = 60
    """Seconds between search-order processing runs (PERSONAL.NOAUTH). 0 = off."""

    search_orders_per_run: int = 5
    """Maximum search orders processed per scheduler run."""

    search_order_stale_minutes: int = 15
    """Orden RUNNING más vieja que esto (min) se resetea a PENDING en el
    siguiente run (recovery de crashes/OOM). 0 = disabled."""

    search_order_max_attempts: int = 5
    """Máximo de intentos de procesamiento de una orden (J1). Una orden FAILED
    que supera este tope se abandona. 0 = sin límite (reintenta siempre)."""

    search_order_retry_cooldown_minutes: int = 30
    """Cooldown (min) entre reintentos de una orden FAILED (J1). Evita
    reintentar un fallo permanente de provider en cada ciclo del job."""

    search_order_max_pending_per_user: int = 10
    """Máximo de órdenes activas (PENDING/RUNNING/FAILED) por usuario (P3).

    Sin límite, un usuario puede encolar cientos de búsquedas que el job
    procesa una a una (cada una golpea providers live): backlog y abuso de
    recursos. Al superar el tope, crear otra orden responde 409."""

    job_failure_alert_enabled: bool = True
    """Master toggle for job consecutive-failure alerts (Task J.1)."""

    job_failure_alert_threshold: int = 3
    """Minimum consecutive failures to trigger a job failure alert."""

    job_failure_alert_cooldown_hours: int = 6
    """Do not re-send an alert for the same job within N hours."""

    job_failure_alert_to_email: str = ""
    """Ops email for job failure alerts. Empty -> log-only (no send)."""

    # =========================================================================
    # Economics / Import cost profile
    # =========================================================================
    default_import_cost_profile: str = "SPAIN"
    """Perfil de costes de importación por defecto (destino). Ver app/config/import_costs.py
    Valores: DEFAULT, SPAIN, PORTUGAL, GERMANY, FRANCE (o alias ES, PT, DE, FR)."""

    # =========================================================================
    # Mercado destino ES (fixtures offline; sin HTTP)
    # =========================================================================
    # Si True, registra provider es_market_fixture en ProviderRegistry al arrancar / en DI.
    # Además, cuando el perfil de costes destino es SPAIN/ES, se auto-registra
    # sin necesidad de activar este flag.
    enable_es_market_fixture: bool = False
    disable_es_market_auto: bool = False
    """Si True, desactiva el auto-registro de fixtures ES por perfil SPAIN."""

    # =========================================================================
    # AutoScout24 España (comparables destino HTTP)
    # =========================================================================
    # Sigue requiriendo flag explícito: no se auto-registra por perfil SPAIN.
    enable_autoscout24_es: bool = False
    """Si True, registra provider autoscout24_es en ProviderRegistry."""

    # =========================================================================
    # Coches.net offline (fixtures JSON)
    # =========================================================================
    # Si True, registra provider coches_net_fixture en ProviderRegistry.
    # Además, cuando el perfil de costes destino es SPAIN/ES, se auto-registra
    # sin necesidad de activar este flag.
    enable_coches_net_fixture: bool = False
    """Si True, registra provider coches_net_fixture (comparables ES offline)."""

    enable_coches_net_html_fixture: bool = False
    """Si True, registra provider coches_net_html_fixture (listados Coches.net offline desde HTML)."""

    # =========================================================================
    # Vision provider (Gemini or OpenAI)
    # =========================================================================
    gemini_api_key: str = ""
    """Google AI API key for Gemini vision analysis."""

    gemini_model: str = "gemini-2.0-flash"
    """Gemini model to use (default: gemini-2.0-flash)."""

    gemini_max_tokens: int = 2000
    """Max tokens for Gemini vision response."""

    gemini_temperature: float = 0.1
    """Temperature for Gemini vision (low = deterministic)."""

    openai_api_key: str = ""
    """OpenAI API key for GPT-4 Vision analysis of inspection photos (fallback)."""

    openai_model: str = "gpt-4o"
    """Vision model to use (default: gpt-4o)."""

    openai_max_tokens: int = 2000
    """Max tokens for OpenAI vision response."""

    openai_temperature: float = 0.1
    """Temperature for OpenAI vision (low = deterministic)."""

    # =========================================================================
    # Observability — Logging
    # =========================================================================
    log_level: str = "INFO"
    log_json: bool = False
    log_request_body: bool = False
    log_response_body: bool = False
    max_log_body_size: int = 4096
    enable_access_log: bool = True

    @property
    def database_url_for_environment(self) -> str:
        return self.database_url

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena de origins en una lista."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_methods_list(self) -> list[str]:
        """Convierte la cadena de métodos HTTP en una lista."""
        return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]

    @property
    def cors_headers_list(self) -> list[str]:
        """Convierte la cadena de headers en una lista."""
        if self.cors_allow_headers == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]

    # =========================================================================
    # SMTP / Email configuration
    # =========================================================================
    smtp_host: str = ""
    """SMTP server hostname. Leave empty to log emails instead of sending."""

    smtp_port: int = 587
    """SMTP server port."""

    smtp_user: str = ""
    """SMTP username."""

    smtp_password: str = ""
    """SMTP password."""

    smtp_from_email: str = "noreply@example.com"
    """From email address for outgoing emails."""

    smtp_use_tls: bool = True
    """Use TLS for SMTP connection."""

    # =========================================================================
    # Opportunity alerts (Task C.2)
    # =========================================================================
    opportunity_alert_enabled: bool = True
    """Master toggle for opportunity email alerts."""

    opportunity_alert_min_recommendation: str = "BUY"
    """Minimum recommendation to trigger an alert (BUY | CONSIDER)."""

    opportunity_alert_min_score: float = 0.0
    """Minimum opportunity_score to trigger an alert (0 = only by recommendation)."""

    opportunity_alert_cooldown_hours: int = 24
    """Do not re-send an alert for the same vehicle_id within N hours."""

    # =========================================================================
    # Redis configuration
    # =========================================================================
    redis_url: str = "redis://localhost:6379/0"
    """Redis connection URL for rate limiting and caching."""

    # =========================================================================
    # Firebase configuration
    # =========================================================================
    firebase_credentials_json: str = ""
    """Firebase service account credentials JSON string."""

    firebase_credentials_path: str = ""
    """Path to Firebase service account credentials JSON file."""

    firebase_required: bool = False
    """If True in production, the app refuses to boot without Firebase credentials.

    Read from env ``FIREBASE_REQUIRED`` (default ``false``). In development/test
    Firebase stays optional regardless: missing credentials only log a warning.
    """

    # =========================================================================
    # Upload directory for inspection photos
    # =========================================================================
    upload_dir: str = "uploads/inspection_photos"
    """Directory where uploaded inspection photos are stored."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
