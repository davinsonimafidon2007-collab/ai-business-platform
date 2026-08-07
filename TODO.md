## Hecho (2026-08) — no rehacer

- CODE-001 — higiene: dead code quitado (paquetes vacíos `app/agents`, `app/orchestrator`, `app/tasks`, `app/telemetry`, `app/workers`; `app/__pycache__.zip`), `.gitignore` endurecido, config `ruff` (`[tool.ruff.lint]`), `scripts/lint.ps1`, refactor `_matches_filters` en `search_orchestrator.py`. Ver `TODO.CODE-001.steps.md`.
- ROI.1 — coherence_warnings (profit_coherence + search mapper)
- REC.1 — recommendation_labels / risk labels ES
- OPP.LIST.1 — labels ES en listado opportunities
- SCORE.1 — category_key + category_label_es
- SEARCH.EMPTY.1 — empty/error search ES + hint Admin
- NEG.1 — script negociación UI en ES
- Providers 1b / MKT.1-2 / PROFIT.1 cost_lines — ver HANDOFF

Ver: `docs/HANDOFF_GROK_NEXT_SESSION.md`

## Siguiente

1. Commit/push desde raíz si hay cambios locales sin subir
2. E2E manual: search → drawer (labels + warnings)
3. Ops con credencial: proxy mobile.de (A.5b), SMTP, Firebase
4. Portales ES live (largo plazo)

---

# TODO — DEVOPS-001 (P3-002): Health compuesto + backups + observabilidad mínima ✅

## Entregado
- [x] `GET /health` (y `/api/v1/health`) compuesto: `checks.api/database/redis`.
      `ok`→200, `degraded` (Redis down/disabled)→200, `error` (DB down)→**503**.
      DB nunca dice `ok` si está caída. Checks async con timeout corto.
- [x] `scripts/backup_postgres.sh` — `pg_dump -Fc` → `backups/` + retención N=7,
      normaliza `DATABASE_URL` async a `postgres://`. Documentado (cron).
- [x] `scripts/restore_postgres.sh` — `pg_restore` (confirmación o `--force`).
- [x] `backups/` en `.gitignore`.
- [x] Access log ya incluye `request_id` + `duration_ms` (PERF-001); sin SaaS.
- [x] `JobFailureAlertService` documentado + vars `JOB_FAILURE_ALERT_*` en
      `.env.example` (sin SMTP → solo log). No se reescribió el servicio.
- [x] `docs/ops.md` — health contract, runbook backup/restore, logging/corr.,
      job failure alerts, observabilidad phase 2.
- [x] `docker-compose.obs.yml` — Prometheus + Grafana con `profiles: [obs]`
      (NO arrancan con `docker compose up` por defecto ni en CI).
- [x] `app/telemetry/__init__.py` placeholder (phase 2). Sin `opentelemetry-*`.
- [x] `.env.example` — `BACKUP_DIR` / `BACKUP_RETENTION`.
- [x] Tests: `tests/unit/test_health.py` (matriz ok/degraded/error/disabled) +
      `tests/integration/api/test_health_api.py` real.
- [x] README — sección "Ops — Health compuesto / Backups / Observabilidad" + link.

## Siguiente / fase 2 (no bloqueante)
- Exponer `/metrics` Prometheus desde la API y activar perfil `obs`.
- Ops reales: SMTP live, credencial Firebase, proxy mobile.de.

## Verificación
```bash
uv run pytest tests/unit/test_health.py tests/unit/test_logging_middleware.py -q
uv run pytest tests/unit -q
```

---

# TODO — REC.1: labels ES recommendation/risk ✅

## Entregado
- [x] `app/services/recommendation_labels.py` — `RECOMMENDATION_LABELS_ES` y `RISK_LABELS_ES` alineados a códigos reales del repo (incluye BUY, CONSIDER, WALK_AWAY, CRITICAL, NONE, UNKNOWN).
- [x] `OpportunityAnalysisSchema`, `ProfitAnalysisSchema`, `OpportunityRead` y `SearchResultItem` con `recommendation_label_es` y `risk_label_es`.
- [x] Mapper `_build_search_result_item` y listado `/opportunities` inyectan las labels ES.
- [x] Types TS `OpportunityAnalysis`, `ProfitAnalysis` y `Opportunity` incluyen labels ES.
- [x] UI prioriza `*_label_es` con fallback al código crudo en drawer y `/opportunities`.
- [x] Tests unitarios `test_recommendation_labels.py` + ampliación `test_opportunities_api.py`.
- [x] `release_check --skip-smoke` verde.

## Siguiente
- Validación de rangos ROI / coherencia de perfiles (producto).
- Ops: A.5b / SMTP / FIRE live cuando haya credencial.


# TODO — ROI.1: coherence_warnings en profit ▲✅

## Entregado
- [x] `app/services/profit_coherence.py` — `build_coherence_warnings` (mensajes ES, no bloqueante; ROI extremo, precios ≤ 0, desglose inconsistente, beneficio vs ROI, beneficio implícito vs mercado).
- [x] `ProfitAnalysisSchema.coherence_warnings: list[str]` en `app/api/v1/schemas/common.py` (default []).
- [x] Mapper `_build_search_result_item` compute + inyecta `coherence_warnings` desde `pa` (`purchase_price`, `total_cost`, `net_profit`, `roi_percentage`) + `me.market_price` (si > 0).
- [x] Frontend type `coherence_warnings?: string[]` en `ProfitAnalysis` (`types/vehicle.ts`).
- [x] Drawer `VehicleDrawer` "Avisos de coherencia" en sección Profit (amber, no bloqueante).
- [x] Tests unitarios `tests/unit/test_profit_coherence.py` (9) — verdes.
- [x] `release_check --skip-smoke` verde (1055 passed).

## Alcance
- No se cambió ninguna fórmula de profit/ROI (solo capa de aviso, MVP en mapper).
- No se tocaron scrapers, scoring/opportunity umbrales, Redis/Compose ni proxy.

## Siguiente
- Ops con credencial, o afinar umbrales con fixtures reales de profit si saltan warnings siempre.


# TODO — PROFIT.1: cost_lines label_es en profit API + drawer ✅

## Entregado
- [x] `app/services/cost_breakdown_labels.py` — `COST_LABELS_ES` y `build_cost_lines` alineados a `CostBreakdown._COMPONENTS`.
- [x] `CostBreakdownSchema` + `CostLineSchema` en `app/api/v1/schemas/common.py`.
- [x] Mapper `_build_search_result_item` inyecta `cost_lines`.
- [x] Drawer `VehicleDrawer` lista partidas en español con fallback al grid actual.
- [x] Types TS `CostLine` y `cost_lines?:` en `CostBreakdown`.
- [x] Tests unitarios `test_cost_breakdown_labels.py` (labels, None, dict-like, orden).
- [x] `release_check --skip-smoke` verde.

## Siguiente
- Validación de rangos ROI / coherencia de perfiles (producto).
- Ops: A.5b / SMTP / FIRE live cuando haya credencial.


# TODO — SEC.001: CORS estricto + Firebase fail-fast + auditoría API keys ✅

## Entregado
- [x] CORS estricto en production: `Settings.validate_cors_for_env` rechaza `*`, lista vacía y solo-devs (localhost/capacitor/ionic). `CORS_ALLOW_HEADERS=*` se endurece a lista explícita en prod. Dev/test conserva defaults.
- [x] Firebase fail-fast: setting `firebase_required` (env `FIREBASE_REQUIRED=false`). En production+required sin credenciales → `RuntimeError` al boot (main.py + `_handle_firebase_unavailable`). Dev/test siguen WARNING sin credenciales.
- [x] Auditoría API keys: solo `key_hash` (Argon2/pwdlib recommended) + prefix; raw key solo se muestra una vez; listado no devuelve `key_hash`. Sin cambio de algoritmo.
- [x] `.env.example` — secciones CORS + Firebase con comentarios de producción (SEC-001).
- [x] README — sección "Seguridad (SEC-001)".
- [x] Tests: `test_cors.py`, `test_config.py`, `test_firebase.py` ampliados; `test_config_env.py::test_settings_case_insensitive` actualizado a CORS de producción.

## Verificación
```powershell
uv run pytest tests/unit/test_cors.py tests/unit/test_config.py tests/unit/test_config_env.py tests/unit/test_firebase.py tests/unit/test_api_key_service.py -q
# ENVIRONMENT=production CORS='*' -> Settings() no carga
```


---

- [x] Inventario y borrado de `_diag_*`, logs, one-shot `_fix_*`, dumps
- [x] `.gitignore` actualizado con patrones de higiene
- [x] `release_check --skip-smoke` verde
## No reintroducir
Logs de pytest/debug van a `/tmp` o se borran; no se comitean en la raíz.


---

# TODO — MKT.2: explanation en API search + VehicleDrawer ✅
- [x] MarketEstimationSchema.explanation
- [x] mapper _build_search_result_item
- [x] unit test schema/mapper
- [x] types TS + drawer "Diferencial de mercado"
## Siguiente
- P.1 provider mercado ES (grande)
- Ops: A.5b / SMTP / FIRE live cuando haya credencial


---


# TODO — MKT.3: provider_sources en search API + drawer ✅
- [x] MarketEstimationSchema.provider_sources
- [x] mapper desde notes providers= o atributo dominio
- [x] UI chips Fuentes en VehicleDrawer

---

# TODO — CI.2: Postgres en Actions + INT.1 obligatorio ✅

## Estado
- [x] service postgres:16-alpine + healthcheck en `.github/workflows/ci.yml`
- [x] DATABASE_URL del job apunta al service Postgres + step `alembic upgrade head` antes de integration
- [x] step INT.1 activo (no comentado), misma lista que `INTEGRATION_SUBSET` de `scripts/release_check.py`
- [x] unit (907) + requirements sync siguen en el job
- [x] README — sección CI actualizada (CI.1 + CI.2)
- [x] Verificado local: `alembic upgrade head` OK sobre Postgres 16 limpio (port 5433); INT.1 (50 tests) verde con y sin `DATABASE_URL` postgres
- [ ] (ops) Primer run verde en GitHub tras push

## CI.3 (después, opcional)
- smoke_critical_path solo en workflow `workflow_dispatch` / branch staging
- ruff gate (CI.1b) si `ruff check app tests` ya limpio

## Verificación local (mismo contrato que CI)
```powershell
$env:ENVIRONMENT="test"
$env:JWT_SECRET_KEY="test_secret_key_that_is_at_least_32_characters_long_1234567890"
python scripts/check_requirements_sync.py
python -m pytest tests/unit -q --tb=line
python scripts/release_check.py --skip-smoke --with-integration
```


---
# TODO — FIRE.1: Google/Firebase smoke — BLOQUEADA POR CREDENCIAL

## Estado
**Bloqueada por credencial — no por código.** No hay service account de Firebase
disponible en este entorno (`.env` local con `FIREBASE_CREDENTIALS_JSON=` y
`FIREBASE_CREDENTIALS_PATH=` vacíos). Se entrega todo el código y la documentación;
falta probar verify + login live (FIX 4). El resto del login Google (front web +
endpoint) ya existía y no se rehízo.

**Entregado:**
- [x] Unit: `authenticate_with_google` (5 tests) + `tests/unit/test_firebase.py` (6 tests mock) — verde.
- [x] Integration: `POST /api/v1/auth/google` (mock) → 200 + `/me` con email Google; 401 token inválido; 422 sin `id_token`.
- [x] `scripts/smoke_firebase.py` — init / `--id-token` / `--call-api`. Exit 2 sin credenciales; exit 0 init-only; exit 1 errores.
- [x] `app/core/firebase.py` — `get_firebase_app()` lee credenciales desde `settings` (`.env`) como fallback (FIX 5).
- [x] `.env.example` — bloque `FIREBASE_CREDENTIALS_*` documentado (sin secretos).
- [x] README — sección "Runbook — Firebase / Google login (FIRE.1)".

**Paths verificados (sin credencial real):**
```
python scripts/smoke_firebase.py → exit 2 "configure FIREBASE_CREDENTIALS_*"
```

## Para desbloquear live
1. Firebase Console → Project settings → Service accounts → Generate new private key
2. `FIREBASE_CREDENTIALS_PATH=/path/to/sa.json` (o JSON en `FIREBASE_CREDENTIALS_JSON`)
3. `python scripts/smoke_firebase.py` → exit 0 "Firebase OK (init only)"
4. Front login Google → `python scripts/smoke_firebase.py --id-token <tok> --call-api`

**Siguiente tras FIRE.1 (o en paralelo mientras sigue bloqueada):** desbloqueo ops
A.5b (proxy mobile.de) **o** SMTP real, **o** task de calidad **CI.1** (GitHub Actions:
`check_requirements_sync` + `pytest unit` + opcional integration).

---


# TODO — SMTP.1: Alertas email reales (C.2 + J.1) — BLOQUEADA POR CREDENCIAL

## Estado (2026-08-06)
**Bloqueada por credencial — no por código.** No hay cuenta SMTP / relay
disponible en este entorno (`.env` local con `SMTP_HOST=`/`SMTP_USER=` vacíos).
Se entrega todo el código y la documentación; falta probar envío real (FIX 4).

**Entregado:**
- [x] `.env.example` — `SMTP_*`, `OPPORTUNITY_ALERT_*` (C.2) y `JOB_FAILURE_ALERT_*` (J.1) ya documentadas sin secretos.
- [x] `scripts/smoke_smtp.py` — smoke de envío SMTP real. Exit 2 sin `SMTP_HOST`/`SMTP_USER`; Exit 0/1 con SMTP; `--to`; `--job-failure` (J.1 casi-E2E, requiere `SMOKE_SMTP=1`).
- [x] README — sección "Runbook — Alertas por email (SMTP)" con variables + smoke + nota "sin SMTP → solo log, no falla la app".
- [x] FIX 0 baseline verde: `tests/unit/test_job_failure_alert_service.py` (6 tests) en `ENVIRONMENT=test` (log-only, sin crash).

**Paths verificados (sin credencial real):**
```
python scripts/smoke_smtp.py            → exit 2 "configure SMTP_*"
SMTP_HOST=inval.id... python scripts/smoke_smtp.py --to ops@example.com → exit 1 "error de envío SMTP"
```

## Para desbloquear (ops externo)
1. Rellenar `SMTP_*` reales (incluido `SMTP_PASSWORD`) en `.env` local — no en git.
2. `python scripts/smoke_smtp.py --to <tu-email>` → debe llegar `[AI Business] SMTP smoke` (evidencia: captura/local nota).
3. (Opcional) `JOB_FAILURE_ALERT_THRESHOLD=1` + forzar fallo de un job → email J.1; o `SMOKE_SMTP=1 python scripts/smoke_smtp.py --job-failure --to <tu-email>`.
4. Restaurar threshold; confirmar que no hay secretos en git (`git grep SMTP_PASSWORD=`).

**Siguiente tras desbloquear (o en paralelo):** **CI.1** — GitHub Actions
(`check_requirements_sync` + `pytest unit` + opcional integration). FIRE.1 ya tiene
tests + `scripts/smoke_firebase.py` (bloqueada por credencial, ver arriba).

---


# TODO — A.5b: mobile.de live PASS (proxy / anti-bot) — BLOQUEADA POR CREDENCIAL

## Estado (2026-08-05)
**Bloqueada por credencial — no por código.** No hay proxy residencial ni cookies
de navegador real disponibles en este entorno.

**Evidencia live (sin proxy):**
```
config: proxy=none  min_delay_ms=0
mobile_de: FAIL ProviderConnectionError (HTTP 403 anti-bot)  elapsed_ms=312
autoscout24: search: OK  count=20  (BMW 316, 6900 EUR)
            detail: OK  brand=BMW model='316 316i /ALU/...' price=6900.0
RESULT mobile_de=False autoscout24=True
```

**Infraestructura ya lista (no requiere cambios de código):**
- `app/providers/http_client.py` — lee `PROVIDER_HTTP_PROXY`, `PROVIDER_HTTP_COOKIES`,
  `PROVIDER_HTTP_MIN_DELAY_MS` desde settings/env.
- `app/jobs/provider_canary.py` — `strict_mobile=True` si hay proxy/cookies;
  403 con proxy → FAIL; sin proxy → WARN (no tumba el job).
- `app/api/v1/admin_status.py` — `GET/POST /admin/status/canary` expone
  `mobile_status`, `mobile_de`, `strict_mobile`.
- `docs/PROXY_MOBILE_DE.md` — runbook completo (config, verificación, troubleshooting 403 vs 429 vs count=0).
- `.env.example` / `.env` — variables `PROVIDER_HTTP_*` documentadas (sin secretos).

**Unit tests en verde (66):** `test_mobile_de_provider`, `test_provider_canary`,
`test_canary_state` — incluidos los 4 escenarios de canary proxy/no-proxy.

## Para desbloquear (ops externo)
1. Configurar `PROVIDER_HTTP_PROXY=http://user:pass@residential-proxy:port` (o `PROVIDER_HTTP_COOKIES`) en `.env` local/staging.
2. `uv run python scripts/verify_providers_live.py` → esperar `mobile_de: search: OK count>0` + `detail: OK`.
3. `POST /api/v1/admin/status/canary` con user ADMIN → `canary.mobile_status="ok"`, `success=true`.
4. Si `count=0` con 200 → posible drift de selectores → aplicar FIX 3 (guardar HTML con `--save-html`, ajustar selectores en `mobile_de.py`, re-correr unit).

**Siguiente tras desbloquear:** SMTP real para J.1/C.2 **o** CI.1 (GitHub Actions). FIRE.1 ya entregado (ver arriba).

---

# TODO — ENV.1: Python 3.13 como runtime soportado

- [x] README.md: documentar "Requiere Python 3.13.x (3.14 no soportado aún por wheels)"
- [x] pyproject.toml: acotar `requires-python` a `>=3.13,<3.14`
- [x] scripts/release_check.py: exit 2 si `sys.version_info >= (3, 14)` (syntax OK)
- [ ] Instalar Python 3.13 (`uv python install 3.13`) y recrear `.venv`
- [ ] Verificar en 3.13: `python scripts/release_check.py --skip-smoke` → verde

---

# REL.1 — Checklist de release local (un comando) ✅

- [x] `scripts/release_check.py`: orquesta en orden C.1 (requirements sync) → pytest unit → smoke (camino crítico + ext. opcionales)
- [x] `--skip-requirements` / `--skip-pytest` / `--skip-smoke` para debug
- [x] `--with-api` exige API up (exit 2 si down); sin él, smoke opcional → `SKIP` si API no responde
- [x] `--with-opportunities` / `--with-admin` (requiere `SMOKE_ADMIN_*` o `--admin-email/--admin-password`)
- [x] `--pytest-args "tests/unit -q"` (default `tests/unit -q`)
- [x] README.md: sección "Checklist release local" documentada
- [x] Exit 0 = `RELEASE CHECK PASSED`; exit ≠ 0 al primer fallo

**Verificación:**
```bash
python scripts/release_check.py --skip-smoke
# → requirements OK + pytest unit OK
# Con API levantada:
python scripts/release_check.py --with-api
```

---

# TODO — ADMIN.1b: UI providers en admin status ✅
- [x] Tipos TS alineados al API
- [x] Sección Providers en admin page
- [x] Muestra registered + flags + perfil


---

# TODO — ARCH-002: SQLAlchemy relationships + selectinload ✅

## Estado
- [x] `relationship()` con `back_populates` en User, Vehicle, Deal, Search, Opportunity, SearchHistory, VehicleEvaluation, ApiKey, RefreshToken, InspectionSession/Observation/Photo
- [x] Cascade ORM alineado con ondelete de FKs existentes (CASCADE -> delete-orphan + passive_deletes; SET NULL -> sin delete-orphan)
- [x] selectinload en repositorios de listado críticos: vehicle, deal, opportunity, search, inspection
- [x] Tests mínimos de relationship (tests/unit/test_relationships.py)
- [x] Sin migraciones / schema SQL modificados
- [x] Suite unitaria verde


---

# TODO — PERF-001 (P1-004): rate-limit/cache distribuido + paginación segura + métricas ✅

## Rate limit / Redis
- [x] `RateLimitMiddleware` sigue usando Redis primero; fallback a memoria si falta
- [x] Header `X-RateLimit-Mode: redis|memory` en respuestas 200 y 429
- [x] Production + Redis down → `logger.error` (no silencioso), throttled ~1 log/10s por proceso (`_TinyRateThrottle`)
- [x] Development/test + Redis down → solo `logger.debug` (app sigue, fail-soft)
- [x] `rate_limit_hit` sigue devolviendo `(allowed: bool, retry_after: int)`; sin romper la API pública (P0-001 no revertido: producción sigue fail-fast al boot)
- [x] No se cambian `ROLE_RATE_LIMITS`/`DEFAULT_RATE_LIMIT`

## Paginación segura (server-side caps)
- [x] `app/core/limits.py`: `MAX_LIST_LIMIT=100`, `clamp_limit()` (min 1, max 100)
- [x] Endpoints: vehicles & searches `limit` `le=1000 → le=100`; deals & opportunities ya `le=100`
- [x] Repositorios (vehicle, search, deal, opportunity) recortan con `clamp_limit` (defensa en profundidad)
- [x] `limit` `ge=1`, `offset` `ge=0`
- [x] `limit=1000` → 422 en vehicles/deals/opportunities/searches (tests API)

## Métricas mínimas de latencia
- [x] `AccessLogMiddleware` ya emite `duration_ms` en el log estructurado (verificado, sin OTEL/Prometheus)

## Cache de mercado
- [x] Verificado L1 Redis (`market:est:*` vía `cache_get/set` + `market_cache_key`) + L2 Postgres (`cached_market`) + `_local_cache`; fail-soft intacto

## Tests
- [x] `tests/unit/test_rate_limit_mode.py` — header redis|memory, 429 header, fallback production ERROR, fallback dev DEBUG, caída runtime
- [x] `tests/unit/test_rate_limit_redis.py` — sin cambios (verde)
- [x] `tests/unit/test_pagination_caps.py` — `clamp_limit` + 422 para `limit=1000` (4 endpoints) + 200 con `limit=100`
- [x] Suite unitaria completa verde


---

# TODO — ECON-001 (P1-005): Modelo económico externalizado + validación ✅

## Estado
- [x] Perfiles externalizados a `app/config/import_costs_data.json` (version: 2026.08) con valores idénticos a los defaults embebidos (sin recalibrar fiscalidad).
- [x] Carga al importar `app.config.import_costs` con fallback a defaults embebidos + warning si falta el archivo.
- [x] Validación de rangos en `ImportCostProfile` (`__post_init__`/`validate()`/`from_dict`): costes fijos `[0,50000]`, tasas `[0,0.5]`, ROI `0<=low<high<=1`, profit `0<=low<high`, cost_ratio `0<=low<high<=3` (tope sobre 1 para no romper el DEFAULT legado). Fuera de rango → `ValueError` (fail-fast).
- [x] Alias intactos (`ES`≡`SPAIN`, etc.).
- [x] `ProfitAnalyzer.analyze(...)` mantiene la API pública; solo se añade `ProfitAnalysis.warnings` (disclaimer + aviso costes > 50% del precio) — sin tocar schemas/endpoints.
- [x] Tests: `test_import_costs_validation.py` (nuevo) + regresión snapshot en `test_profit_analyzer.py`.
- [x] README / `.env.example` documentan cómo actualizar costes 2026.
- [x] `_load_profiles_from_file` devuelve None si el archivo no existe → fallback probado.

## Verificación
```powershell
uv run python -c "from app.config.import_costs import get_profile; p=get_profile('ES'); print(p)"
uv run pytest tests/unit/test_profit_analyzer.py tests/unit/test_import_costs_validation.py tests/unit/test_import_cost_default_wiring.py -q
uv run pytest tests/unit -q
```

## Nota
No se recalibró a fiscalidad real 2026 (requiere fuente oficial; follow-up aparte).
El tope de `cost_ratio` se fijó en 3.0 (desviación documentada de la tabla del task,
que pedía `<= 1`) para conservar el `DEFAULT` legado con `risk_high_cost_ratio=2.0`.


---

# TODO — P2-001 / FE-001: Auth/Zustand/React Query consistentes (Next 15 + React 19) ✅

## Objetivo
Reducir estados inconsistentes entre JWT (localStorage), `useAuthStore` (Zustand),
React Query cache, login email/password vs Google (web + Capacitor) y `AuthGuard`.

## Entregado
- [x] `auth-store.ts`: nuevo `setSession({ accessToken, refreshToken, user })` — path
  canónico de persistencia (tokens + user en localStorage + update de store).
  `logout()` limpia localStorage + store. `initialize()` hidrata desde localStorage
  y deja `TODO(FE-001)` comentado para validación de `exp` del JWT (opcional, no
  implementado para mantener el cambio mínimo). `TOKEN_KEYS` centraliza las claves.
- [x] `hooks/use-logout.ts` (nuevo): path canónico de logout → `queryClient.clear()`
  + `auth.logout()` (+ `signOutOfGoogle`). Usado en `navbar.tsx`.
- [x] `api/client.ts`: refresh fallido → `clearTokens()` + `window.dispatchEvent(new
  Event("auth:logout"))` + redirect. Sin import circular del store (estrategia evento).
- [x] `providers.tsx`: `AuthInitializer` escucha `auth:logout` → `queryClient.clear()`
  + `logout()` del store (mantiene store + query cache coherentes).
- [x] `login-page.tsx` / `register-page.tsx`: persistencia unificada vía `setSession()`
  + `queryClient.clear()` tras login/register/Google (no mostrar datos de usuario previo).
- [x] `google-auth.ts`: usa `setSession()` en vez de copiar localStorage a mano.
- [x] `AuthGuard`: ya cumplía (isLoading → spinner sin redirect; no auth → redirect login;
  children solo cuando autenticado). Sin cambios necesarios.
- [x] Tests Vitest nuevos (9): `store/auth-store.test.ts` (5), `components/auth-guard.test.tsx`
  (3), `hooks/use-logout.test.tsx` (1). Todos pasan.

## Criterios
1. Login/logout dejan store + localStorage + React Query coherentes (setSession + clear).
2. Sin flash de contenido protegido antes de `initialize` (AuthGuard isLoading → spinner).
3. 401 con refresh fallido limpia sesión y manda a login (evento auth:logout + redirect).
4. No se muestran datos de un usuario previo tras login de otro (`queryClient.clear()`).
5. Tests Vitest de auth-store/guard pasan (9/9).
6. `tsc --noEmit` sin errores. `npm run test:run` → 13 archivos OK; 2 fallos PRE-EXISTENTES
   en `use-search.test.tsx` (`formatFiltersForApi` brand/model/year), ajenos a este task.
7. Backend NO modificado.
8. Cambios acotados a auth/providers/client/hooks.

## Verificación
```powershell
cd frontend
npm run test:run        # mis tests (9) pasan; 2 fallos pre-existentes en use-search
npx tsc --noEmit        # sin errores
```

## Nota
No se migró a cookies httpOnly ni se reescribió Google Auth nativo (eso es AND-001).


