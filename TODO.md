# TODO — Modo personal (sin login) — PERS.CLOSE.1 ✅

Estado: **cerrado**. La app funciona en local sin registro ni login.

Fuente de verdad única del bypass:

```bash
AUTH_DISABLED=true               # backend  (.env)
NEXT_PUBLIC_AUTH_DISABLED=true   # frontend (frontend/.env)
```

`APP_MODE=personal` es **solo documentación de intención**: no altera la
autenticación. Si quieres entrar sin login, activa `AUTH_DISABLED`.

## Hecho

- [x] Backend: `settings.auth_disabled` + `allow_auth_disabled_in_prod`
- [x] Backend: `app/core/local_user.py` (UUID fijo `…0001`, `local@localhost`, ADMIN)
- [x] Backend: `PersonalUserService.ensure_local_user()` — get-or-create idempotente
- [x] Backend: `get_current_user` → un solo camino; nunca devuelve `None`
- [x] Backend: eliminado el branch paralelo `app_mode == "personal"` (devolvía `None`)
- [x] Backend: middleware salta pre-auth con el flag ON
- [x] Backend: `production` + `AUTH_DISABLED=true` sin override → **no arranca**
- [x] Frontend: `config/app-mode.ts` (`isAuthDisabled()`, `LOCAL_USER`)
- [x] Frontend: `auth-store.initialize()` autentica al usuario local
- [x] Frontend: `auth-guard.tsx` renderiza children (sin violar Rules of Hooks)
- [x] Frontend: `api/client.ts` no entra en el loop 401 → logout → login
- [x] Frontend: `page.tsx` va directo a `/dashboard`
- [x] Frontend: `providers.tsx` no inicializa Google Auth
- [x] Frontend: `navbar.tsx` oculta "Cerrar sesión"
- [x] Tests: `tests/unit/test_auth_disabled.py` (10) + `test_auth_disabled_api.py` (2)
- [x] Docs: `docs/CONTEXT_PERSONAL_USE.md` + README

No se ha borrado el código de login/JWT: solo se bypasea. Volver a multiusuario
es poner `AUTH_DISABLED=false`.

---

# CI.LINT.1 — Ruff como gate en CI ✅

- [x] Step `Ruff check` en el job backend, **antes** de pytest (falla rápido).
- [x] Baseline 438 → **0**. `ruff check app tests` exit 0.
- [x] 507 + 33 arreglos automáticos (`--fix`) + fixes manuales:
      F821 (3, anotaciones sin símbolo → `TYPE_CHECKING`), B904 (10, `raise
      ... from`), F841 en producción (2), B007, B905 (3, `strict=True`),
      B017 (`pytest.raises(Exception)` → `ValidationError`).
- [x] `per-file-ignores` justificados en `pyproject.toml`:
      - **E712** en `app/repositories/*`: en SQLAlchemy `Column == True` NO se
        puede sustituir por `if col:` — el truthiness del objeto `Column` es
        siempre verdadero y generaría un WHERE incorrecto. Falso positivo.
      - **E402** en scripts con `sys.path.insert` previo a los imports.
      - **F841** en 5 ficheros de test (residual heredado, CODE-001).
- [x] **UP042** ignorado repo-wide con motivo: migrar los 14 enums de
      `(str, Enum)` a `StrEnum` cambia `str(x)`/f-strings (`"Role.ADMIN"` →
      `"admin"`) y afectaría a payloads de API y logs. Es cambio de
      comportamiento, no higiene → task propio.
- [x] Suite verde tras los autofixes.

---

# COV.GATE.1 — Gates de coverage ✅

**Backend** (gate 70 % sobre módulos críticos, actual **97.43 %**):

| Módulo | Cobertura |
|---|---|
| `app/services/profit_analyzer.py` | 100 % |
| `app/services/opportunity_finder.py` | 98 % |
| `app/services/auth_service.py` | 88 % |
| `app/dependencies/auth.py` | 64 % → **100 %** |

- [x] `pytest-cov` en dev deps + `[tool.coverage.*]` en `pyproject.toml`.
- [x] Gate por paths en CI (no `fail_under` global: evita premiar módulos
      triviales y no exige 80 % del monorepo).
- [x] +7 tests en `test_dependencies_auth_paths.py`: el gate destapó que solo
      se cubría el bypass `auth_disabled`, no el camino JWT ni las denegaciones
      de rol/permiso (o sea, la lógica de seguridad).

**Frontend** (thresholds lines/stmts/funcs 30 %, branches 20 %; actual
**57.4 % / 60.9 % / 69.6 %**):

- [x] `@vitest/coverage-v8` añadido: **faltaba**, el job habría fallado con
      `MISSING DEPENDENCY`.
- [x] `coverage.include` acotado a `src/app/store/**` y `src/app/services/**`.
- [x] `services/api/client.ts` excluido (wrapper axios con interceptores y
      refresh: necesita harness de red, se cubrirá aparte). Documentado.
- [x] +2 ficheros de test: `search.ts` 0 → 100 %, `theme-store.ts` 0 → 100 %.
- [x] Gate verificado: baja el umbral y `vitest` sale con exit 1.

Pendiente: `google-auth.ts` e `inspection.ts` siguen a 0 %; subir umbrales
cuando se cubran.

---

# SMOKE.AS24.LIVE.1 — Canary AS24-first + smoke live ✅

- [x] `provider_canary`: `data.policy = "as24_first"` + `status` por provider
      (`ok|fail|error` / `ok|warn_antibot|fail|error`). mobile.de sin proxy →
      `warn_antibot` con log WARN (antes ERROR aunque no contribuyera al FAIL).
      `mobile_status` y `strict_mobile` se mantienen (los usa admin/status).
- [x] `scripts/smoke_as24_live.py`: exit 0 con ≥1 listing, 1 en 0 listings o
      error. `--json`, `--url`, `--timeout`. Hint según el fallo, sin traceback.
- [x] `admin_status` expone `canary.policy`.
- [x] Tests: +4 canary (AS24 0 listings, AS24 error, mobile warn no tumba,
      error genérico de mobile) y +7 del script con mocks.
- [x] README + CONTEXT: sección "Providers (uso personal) — AS24-first".
- [x] Live verificado: 20 listings. Suite 1139 passed.

El smoke live **no** es gate de CI (red flaky); en CI corren solo los mocks.

---

# CI.FE.1 — Job frontend en GitHub Actions ✅

- [x] Job `frontend` (Node 22, `npm ci`, `npm run test:run`), paralelo al backend
      (sin `needs:`), `timeout-minutes: 15`, caché npm por `package-lock.json`.
- [x] `NEXT_PUBLIC_AUTH_DISABLED=false` en el step de tests.
- [x] Job `backend` sin cambios (9 steps intactos).
- [x] Arreglados 2 tests obsoletos en `use-search.test.tsx`: esperaban filtros
      concatenados en `query` (`"BMW BMW 320d"`, `"year_from:2015"`), pero
      `formatFiltersForApi` los manda como campos tipados. Eran los 2 fallos
      pre-existentes que arrastraba P2-001.
- [x] Local: **66 passed (15 archivos)**.
- [ ] Pendiente: primer run verde en GitHub tras el push.

Lint queda para **CI.LINT.1** (step comentado en el workflow); `next build` para
CI.FE.BUILD.1.

---

# E2E.MANUAL.PASS.1 — Camino crítico ejecutado ✅

**2026-08-08 · PASS con SKIP** · evidencia en `docs/e2e_runs/2026-08-08_PASS.md`

Preflight verde (integrations_ready, smoke_es_providers, release_check 1128,
/health) y camino `search → drawer → opportunities → admin` recorrido vía API
sin un solo 401.

## Bugs bloqueantes corregidos durante el run

- [x] `docker-compose.yml` no pasaba `AUTH_DISABLED` al contenedor → 401 pese al
      `.env`. Passthrough añadido (+ `ALLOW_AUTH_DISABLED_IN_PROD`, `APP_MODE`).
- [x] El flag inyectado contaminaba `ENVIRONMENT=test` (13 tests rojos). Escape
      dedicado `AUTH_DISABLED_IN_TESTS` + guard `mode="before"` bajo pytest.
- [x] `SearchOrchestrator` pasaba el término crudo a AS24 → `/BMW` 404 tragado
      como 200 con 0 resultados. Añadido `build_search_url()` (0 → 5 resultados).
- [x] `local@localhost` no valida como `EmailStr` → `/auth/me` 500. Cambiado a
      `local@example.com` (RFC 2606); UUID intacto, fila migrada.
- [x] 11 tests de regresión (`test_autoscout24_search_url.py`,
      `test_local_user_email.py`, +2 en `test_auth_disabled.py`).

## Pendiente de este run

- [ ] **Recorrer la UI en navegador** (filas 0.5 / 1.1 / 1.2, SKIP): no había
      `node_modules` ni navegador en el entorno. `npm ci && npm run dev` y
      confirmar que la home entra directa al dashboard.
- [ ] (nota) El `except Exception` del orquestador convierte fallos de provider
      en 200 vacío; sigue pudiendo enmascarar errores. Candidato a task propio.

---

## Residual (ops, no código)

- [ ] (opcional) SMTP real — solo si quieres alertas por email
- [ ] (opcional) Firebase — solo si quieres Google login (irrelevante sin auth)
- [ ] ~~Proxy residencial mobile.de~~ — no prioritario (AS24-first)
