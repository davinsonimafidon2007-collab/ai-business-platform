# Task F.1 — Rate limit distribuido con Redis

## Steps
- [x] FIX 1: Añadir `rate_limit_hit` en `app/core/redis.py` (INCR+TTL+EXPIRE, RuntimeError si no Redis)
- [x] FIX 2: Refactor `app/middleware/rate_limit_middleware.py` → `_allow` (Redis primero, fallback local) + `_check_limit_local`
- [x] FIX 3: Crear `tests/unit/test_rate_limit_redis.py` (6 tests: 4 rate_limit_hit + 2 fallback/redis _allow)
- [x] Verificación: `pytest -q tests/unit/test_rate_limit_redis.py tests/unit/test_rate_limit_middleware.py tests/unit/test_rate_limiting.py` → **17 passed**
