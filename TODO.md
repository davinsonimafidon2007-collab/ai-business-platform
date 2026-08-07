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

## Residual (ops, no código)

- [ ] Pasar `docs/E2E_MANUAL_CHECKLIST.md` en local y anotar la fecha del PASS
- [ ] (opcional) SMTP real — solo si quieres alertas por email
- [ ] (opcional) Firebase — solo si quieres Google login (irrelevante sin auth)
- [ ] ~~Proxy residencial mobile.de~~ — no prioritario (AS24-first)
