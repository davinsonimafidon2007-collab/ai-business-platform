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
