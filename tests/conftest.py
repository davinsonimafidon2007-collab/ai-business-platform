"""Conftest raíz de la suite (TEST.INFRA.1).

Hace la suite AUTOCONTENIDA: los módulos de ``app`` leen ``Settings()`` al
importarse y fallan si no hay ``JWT_SECRET_KEY``. CI exportaba esas variables
pero una máquina local sin ``.env`` no podía ni COLECTAR tests (81 errores de
pydantic). Aquí replicamos los mismos valores por defecto que usa CI, solo si
el entorno no los define ya (``setdefault``), ANTES de cualquier import de
``app``.

Reglas heredadas de ``app/core/config.py``:
- ``ENVIRONMENT=test`` → JWT de test autogenerado + auth ON por defecto
  (los tests de JWT/401 siguen validando el camino multiusuario).
- Para tests del modo personal sin login existe el opt-in explícito
  ``AUTH_DISABLED_IN_TESTS=true`` (ver test_auth_disabled*).
"""

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test_secret_key_that_is_at_least_32_characters_long_1234567890",
)
# Nunca heredar AUTH_DISABLED=true de una máquina de uso personal: la suite
# decide por test vía AUTH_DISABLED_IN_TESTS (misma protección que config.py).
os.environ.pop("AUTH_DISABLED", None)


@pytest.fixture(autouse=True)
def _reset_rate_limit_buckets():
    """Aísla los buckets in-memory de RateLimitMiddleware entre tests.

    TEST.D fix (flaky): el middleware es un singleton registrado en ``app`` y
    sus contadores sobreviven entre tests; un fichero que agote el límite
    global dejaba 429 a los siguientes (p.ej. test_system_metrics fallaba solo
    al correr la suite completa). Solo se ejecuta si el middleware existe.
    """
    yield
    try:
        from app.main import app
        from app.middleware.rate_limit_middleware import RateLimitMiddleware

        current = getattr(app, "middleware_stack", None)
        for _ in range(10):
            if current is None:
                return
            if isinstance(current, RateLimitMiddleware):
                current._ip_limits.clear()
                current._endpoint_limits.clear()
                current._user_limits.clear()
                current._api_key_limits.clear()
                return
            current = getattr(current, "app", None)
    except Exception:
        # Si la app no llegó a importarse/arrancarse, nada que limpiar.
        pass
