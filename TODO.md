# Plan de Arreglos de Tests Desincronizados

Objetivo: `pytest -q` con `JWT_SECRET_KEY` → 0 failed / 0 errors.

## Progreso

### Categoría 1 — Falta prefijo `/api/v1` en rutas auth ✅ APLICADA
- [x] `tests/integration/test_security_api.py`
- [x] `tests/integration/test_auth_api.py`
- [x] `tests/integration/test_password_reset_api.py`

### Categoría 2 — Métodos async sin `await` / mocks con firma obsoleta ✅ COMPLETADA
- [x] `tests/unit/test_comparable_market_estimator.py` (13)
  - Fix aplicado: conversión a `async` con `@pytest.mark.asyncio` + `await estimator.estimate(...)` vía `_apply_category2_fix.py`.
  - Estado: 13/13 PASS.
- [x] `tests/unit/test_search_orchestrator.py` (8)
  - Fix aplicado en `app/services/search_orchestrator.py`: `_analyze_vehicle()` ahora prefiere `estimate_async` y hace fallback a `estimate` (awaited si es coroutine).
  - Estado: 53/53 PASS.

### Categoría 3 — Mocks/fixtures con firmas obsoletas
- [ ] 3a. `tests/unit/test_api_key_service.py` (2)
  - Causa: `ApiKeyService.validate_api_key()` usa `repository.list_active_by_prefix()`.
  - Fix: mockear `list_active_by_prefix` en `test_validate_api_key_valid` y `test_validate_api_key_expired`.
- [ ] 3b. `tests/unit/test_inspection_service.py` (1)
  - Causa: `InspectionService.create_session()` ahora requiere `user_id`.
  - Fix: pasar `user_id` en la llamada.
- [ ] 3c. `tests/integration/database/conftest.py` + `test_opportunity_repository.py` (8)
  - Causa: `Vehicle.user_id` es `NOT NULL`. El fixture `sample_vehicle` no lo provee.
  - Fix: crear un `User` antes del `Vehicle` y asignar `user_id`.

### Categoría 4 — Endpoints requieren auth no mockeada (404/401)
- [ ] `tests/integration/test_rbac_api.py` (5) — rutas `/api/v1/users/...`
- [ ] `tests/integration/test_user_api.py` (4) — rutas `/api/v1/users/...`
- [ ] `tests/integration/api/test_search_api.py` (10) — mockear `get_current_user`
- [ ] `tests/integration/test_vehicles_api.py` (8) — mockear `get_current_user`
- [ ] `tests/integration/test_searches_api.py` (4) — ruta `/api/v1/searches` + mock `get_current_user`
- [ ] `tests/integration/test_inspection_api.py` (2) — mockear `get_current_user`
- [ ] `tests/integration/test_negotiation_integration.py` (7) — solo async/await de `estimate` en stubs
- [ ] `tests/integration/test_search_engine.py` (6) — solo async/await de `estimate` en stubs
- [ ] `tests/integration/test_vision_api.py` (10) — mockear `get_current_user`
- [ ] Re-ejecutar `test_rbac_api.py` y `test_user_api.py` tras el fix de ruta para confirmar que NO queda ningún 429 escondido.

### Categoría 5 — Falso positivo entorno (1 test) — NO TOCAR
- [ ] `tests/unit/test_config_env.py`

### Categoría 6 — `test_database_manager.py` (2 tests)
- [ ] Importar modelos en `app/models/__init__.py` para poblar `Base.metadata` (o crear tablas con `Base.metadata.create_all(manager.engine)`).

### Diagnóstico rate limiter 429
- [ ] Confirmar que no hay 429 reales tras los fixes (los fallos actuales son 404/401 y errores de coroutine, NO rate limiting).

### Verificación final
- [ ] `pytest -q` con `JWT_SECRET_KEY` → 0 failed / 0 errors
- [ ] `env -u JWT_SECRET_KEY pytest -q tests/unit/test_config_env.py`

