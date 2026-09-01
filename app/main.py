from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.metrics import router as metrics_router
from app.api.v1.router import api_router
from app.api.v1.routes.health import router as health_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.redis import close_redis, init_redis
from app.database import db_manager
from app.jobs.base import JobContext
from app.jobs.factory import create_scheduler
from app.jobs.scheduler import Scheduler
from app.middleware.authentication_middleware import AuthenticationMiddleware
from app.middleware.logging_middleware import AccessLogMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.redirect_https import HTTPSRedirectMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.trusted_hosts_middleware import TrustedHostsMiddleware

setup_logging()

logger_main = getLogger("app.main")

# ---------------------------------------------------------------------------
# Startup validation — refuse to boot with insecure defaults
# ---------------------------------------------------------------------------
if not settings.jwt_secret_key:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. This is a security requirement. "
        "Generate a strong secret key and set it as an environment variable."
    )

if len(settings.jwt_secret_key) < 32:
    raise RuntimeError(
        f"JWT_SECRET_KEY is too short ({len(settings.jwt_secret_key)} chars). "
        "It must be at least 32 characters long."
    )

# PERS.CLOSE.1 — AUTH_DISABLED fail-fast: in production with auth disabled the
# app refuses to boot (anyone reaching the port would be ADMIN). Only an
# explicit ALLOW_AUTH_DISABLED_IN_PROD=true overrides this.
settings.auth_disabled_forbidden_in_production()

# SEC-001 — Firebase fail-fast: in production with FIREBASE_REQUIRED=true the
# app must not boot without Firebase credentials (Google Login would be dead).
if settings.environment == "production" and settings.firebase_required:
    from app.core.firebase import get_firebase_app

    get_firebase_app()  # raises RuntimeError if Firebase is not available

# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def scheduler_lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage the background scheduler lifecycle.

    Creates the DatabaseManager, instantiates the Scheduler with all
    registered jobs, starts it on startup and gracefully stops on shutdown.
    """
    # Poblar ProviderRegistry con los providers de runtime (DE + ES fixture
    # si el flag está activo) al boot, para que get_provider/list_providers
    # y los paths admin/canary/estimador vean el registry poblado (P.1a-bis).
    from app.providers.registry import ProviderRegistry

    ProviderRegistry.ensure_default_providers()

    await init_redis()
    await db_manager.init()

    # TASK-009: Recuperar al arrancar las órdenes de búsqueda que quedaron en
    # RUNNING (crash/reinicio anterior) reencolándolas a PENDING para que el
    # job de procesado las retome. Un solo UPDATE atómico, sin umbral de
    # antigüedad: al boot no puede haber workers procesando.
    try:
        from app.repositories.search_order_repository import SearchOrderRepository

        async with db_manager.get_session() as session:
            recovered = await SearchOrderRepository(session).recover_all_running()
        if recovered:
            logger_main.warning(
                "Startup recovery: reenqueued %d stuck RUNNING search order(s) -> PENDING",
                recovered,
            )
    except Exception:
        logger_main.exception("Failed to recover stuck RUNNING search orders on startup")

    context = JobContext(db_manager=db_manager, settings=settings)
    scheduler: Scheduler = create_scheduler(context)

    # Exponer el scheduler para que el endpoint admin (G.4) lea métricas.
    app.state.scheduler = scheduler

    if settings.enable_scheduler:
        await scheduler.start()

    try:
        yield
    finally:
        if settings.enable_scheduler:
            await scheduler.stop()

        await db_manager.shutdown()
        await close_redis()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=scheduler_lifespan,
)

# Registrar manejadores de excepciones
register_exception_handlers(app)

# Middlewares (ejecutados en orden inverso)
# RateLimitMiddleware and AuthenticationMiddleware are the new security layers
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIdMiddleware)
if settings.environment != "development" or settings.https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)

if settings.security_headers_enabled:
    from app.middleware.security_middleware import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)

if settings.environment == "production" and settings.trusted_hosts.strip():
    app.add_middleware(TrustedHostsMiddleware)

# Configuración CORS (debe ser el último middleware añadido, primero en ejecutarse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)

app.include_router(api_router, prefix="/api/v1")
# Health y métricas en raíz para healthcheck Docker / scraping Prometheus.
# api_router ya expone /api/v1/health y /api/v1/metrics; aquí solo raíz.
app.include_router(health_router)
app.include_router(metrics_router)


# ---------------------------------------------------------------------------
# Custom OpenAPI schema with security schemes
# ---------------------------------------------------------------------------

def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token obtained from /auth/login",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key with format: abp_live_<key>",
        },
    }

    # Apply security globally
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore
