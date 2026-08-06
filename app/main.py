from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from app.api.v1.admin_api_keys import router as admin_api_keys_router
from app.api.v1.admin_status import router as admin_status_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.auth import router as auth_router
from app.api.v1.searches import router as searches_router
from app.api.v1.users import router as users_router
from app.api.v1.vehicles import router as vehicles_router
from app.api.v1.router import api_router
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
from app.middleware.request_id import RequestIdMiddleware

setup_logging()

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

# SEC-001 — Firebase fail-fast: in production with FIREBASE_REQUIRED=true the
# app must not boot without Firebase credentials (Google Login would be dead).
if settings.environment == "production" and settings.firebase_required:
    from app.core.firebase import get_firebase_app

    get_firebase_app()  # raises RuntimeError if Firebase is not available

# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def scheduler_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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

# Configuración CORS (debe ser el último middleware añadido, primero en ejecutarse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(admin_api_keys_router, prefix="/api/v1")
app.include_router(admin_status_router, prefix="/api/v1")
app.include_router(searches_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(vehicles_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/health",
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
def get_health() -> dict[str, str]:
    return {"status": "operational"}


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

