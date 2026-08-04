# Task F.4 — Admin: listar y revocar API keys de cualquier usuario

## Steps
- [x] FIX 1: `app/services/api_key_service.py` — `list_keys_for_user(user_id, *, active_only=True)`
- [x] FIX 2: `app/api/v1/admin_api_keys.py` (GET `/admin/api-keys?user_id=` + DELETE `/admin/api-keys/{id}`, `require_manage_api_keys`)
- [x] FIX 2b: wire `admin_api_keys_router` en `app/main.py` (`prefix="/api/v1"`)
- [x] FIX 2c: añadir `/api/v1/admin/` a la skip list de `AuthenticationMiddleware` (la auth se aplica vía deps de ruta `require_manage_api_keys -> get_current_user`)
- [x] FIX 3: `get_by_user_id` en `FakeApiKeyRepository` (conftest) + `tests/integration/test_admin_api_keys_api.py` (9 casos: listar ajeno, active_only, 403 USER, 401 anon, 422 sin user_id, revocar ajeno→dueño ya no la ve, 404 inexistente, 403 revocar, 401 delete anon)
- [x] Verificación: `pytest -q tests/integration/test_admin_api_keys_api.py tests/integration/test_api_keys_api.py tests/unit/test_api_key_service.py` → **24 passed, 94 warnings** (solo deprecation warnings asyncio/Starlette)

## Aceptación
- [x] `GET /api/v1/admin/api-keys?user_id=` con ADMIN → lista metadata del usuario indicado
- [x] `DELETE /api/v1/admin/api-keys/{id}` con ADMIN → 204; key queda inactiva
- [x] USER → 403 en rutas admin; sin auth → 401
- [x] CRUD own F.2 intacto (mismo path `/api/v1/auth/api-keys`)
- [x] Sin raw key / hash en respuestas admin
- [x] pytest del comando de verificación → all passed

# Task F.2 — CRUD HTTP de API keys

## Steps
- [x] FIX 1: Crear `app/schemas/api_key.py` (ApiKeyCreate, ApiKeyRead, ApiKeyCreated, ApiKeyListResponse)
- [x] FIX 2: Crear `app/api/v1/api_keys.py` (router POST/GET/GET {id}/DELETE bajo `/auth/api-keys`) + wire en `app/main.py`
- [x] FIX 3: Crear `tests/integration/test_api_keys_api.py` (5 tests de CRUD)
- [x] Añadir `client` fixture + repos fake en `tests/integration/conftest.py` (register/login + get_api_key_service override)
- [x] Añadir fixture autouse `_reset_rate_limits` en conftest (aisla buckets in-memory de F.1 entre tests)
- [x] Verificación: `pytest -q tests/integration/test_api_keys_api.py tests/unit/test_api_key_service.py tests/integration/test_security_api.py::TestApiKeyAuthentication` → **18 passed**

# Task F.3 — Suite integración: auth + paths alineados

## Resumen
Los criterios de aceptación de F.3 ya se cumplían en el código actual. No se modificó ningún test ni código de producto.

## Verificación
- [x] `POST /api/v1/search` → 200 con `override_auth` (test_search_api.py)
- [x] `POST /api/v1/vehicles` → 201 con `override_auth` (test_vehicles_api.py)
- [x] `/api/v1/searches` (no `/searches`) con `override_auth` (test_searches_api.py)
- [x] inspection `/api/v1/inspections` con auth (test_inspection_api.py)
- [x] RBAC `/api/v1/users` con tokens admin/user + 401 sin token (test_rbac_api.py)
- [x] `/api/v1/users` con auth admin (test_user_api.py)
- [x] F.1/F.2 intactos: fixture autouse `_reset_rate_limits` + `client` fixture presentes en conftest

## Comando de verificación
`pytest -q tests/integration/api/test_search_api.py tests/integration/test_vehicles_api.py tests/integration/test_searches_api.py tests/integration/test_inspection_api.py tests/integration/test_rbac_api.py tests/integration/test_user_api.py`

→ **37 passed, 121 warnings** (solo deprecation warnings de asyncio/Starlette, aceptables)

## Nota
Los helpers opcionales `_register_and_login` / `auth_headers` / `authenticated_client` no se añadieron (decisión explícita): no aportan cobertura nueva porque los tests ya usan `override_auth` / JWT real. Los tests pasan sin la suite de conftest.

## Fuera de alcance
- mobile.de + proxy → Task A.5 (necesita credenciales)
- Admin CRUD de API keys ajenas → producto menor

# Task A.5 — mobile.de live con proxy (canary PASS)

## Steps
- [x] FIX 1: `app/jobs/provider_canary.py` — `_anti_bot_configured()`, `strict_mobile`, logs WARN (sin proxy) vs FAIL (con proxy), `success` condicionado
- [x] FIX 2: `tests/unit/test_provider_canary.py` — 5 casos: sin proxy 403→success; con proxy 403→failure; con proxy listings→success; con proxy 0 listings→failure; toggle `_anti_bot_configured`
- [x] Verificación: `pytest -q tests/unit/test_provider_canary.py` → **5 passed**; `tests/unit/test_jobs.py` intacto → **19 passed**

## Fuera de alcance (A.5)
- Contratar/configurar cuenta de proxy (operativa)
- Reescribir selectores mobile.de (solo si HTML real muestra drift)
- Hacer AS24 opcional (AS24 sigue obligatorio)
- Admin API keys

## Nota
- FIX 3 (operativa `.env` + `verify_providers_live.py`) se deja pendiente hasta tener credenciales de proxy. No requiere cambios de código.

# Task G.2 — Admin: disparar canary de providers a demanda

## Resumen
Endpoint admin-only `POST /api/v1/admin/status/canary` que ejecuta `ProviderCanaryJob` **ahora** (sin esperar al scheduler) y devuelve el mismo snapshot que `GET /api/v1/admin/status`.

## Steps
- [x] FIX 1: `app/api/v1/admin_status.py` — extraer helper `_build_admin_system_status()` (Redis ping + `get_last_canary_result`) compartido por GET y POST
- [x] FIX 1b: `POST /admin/status/canary` con `require_admin`; crea `JobContext(db_manager, settings)` + `ProviderCanaryJob().execute(context)` síncrono; devuelve `AdminSystemStatus` actualizado
- [x] FIX 2: `tests/integration/test_admin_status_api.py` — `TestRunProviderCanary` (6 casos: 401 anon, 403 USER, 200 success con mock, FAIL de negocio ≠ 500, GET posterior ve mismo snapshot, mock job ejecutado)
- [x] FIX 3: docstring del endpoint + esta entrada en `TODO.md` (`POST /api/v1/admin/status/canary` — admin only; ejecuta canary síncrono)

## Aceptación
- [x] `POST /api/v1/admin/status/canary` solo ADMIN (401/403)
- [x] Respuesta = mismo shape que GET status, con canary actualizado
- [x] GET posterior ve el mismo resultado (via `canary_state`)
- [x] Canary de negocio en FAIL ≠ HTTP 500
- [x] Tests sin red real (job mockeado); A.5/G.1 intactos

## Fuera de alcance (G.2)
- Cola async / Celery → overkill
- Proxy mobile.de real → Ops A.5
- UI frontend → track aparte
- Cambiar reglas AS24/mobile del canary → A.5 cerrado
</content>
