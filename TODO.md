# TODO — Modo personal (desactivar autenticación para uso local)

Estado: en progreso.

## Pasos

- [ ] 1. Backend: añadir config `app_mode`/`personal_user_*` a `app/core/config.py`
- [ ] 2. Backend: `app/main.py` — saltar JWT/Firebase fail-fast en modo personal
- [ ] 3. Backend: nuevo servicio `app/services/personal_user_service.py` (usuario persistente, una sola vez)
- [ ] 4. Backend: `app/dependencies/auth.py` — `get_current_user` devuelve usuario personal en personal mode
- [ ] 5. Backend: `app/middleware/authentication_middleware.py` — inyecta usuario personal en personal mode
- [ ] 6. Frontend: `frontend/src/app/config/app-mode.ts` — utilidad de detección de modo
- [ ] 7. Frontend: `auth-store.ts` — `initialize()` autentica al usuario personal
- [ ] 8. Frontend: `services/api/client.ts` — no redirigir por 401 en modo personal
- [ ] 9. Frontend: `page.tsx` (home) — redirige directo a /dashboard en modo personal
- [ ] 10. Frontend: `auth-guard.tsx` — permite siempre en modo personal
- [ ] 11. Frontend: `providers.tsx` — salta `initGoogleAuth()` en modo personal
- [ ] 12. Frontend: `layout/navbar.tsx` — oculta botón de logout en modo personal
- [ ] 13. Config: `.env`, `frontend/.env.local`, `.env.production` → `APP_MODE=personal` / `NEXT_PUBLIC_APP_MODE=personal`
- [ ] 14. Docs: `.env.example`, `docs/CONTEXT_PERSONAL_USE.md`, `docs/PERSONAL_MODE.md`
- [ ] 15. Verificación: tests backend, tests frontend, y **búsqueda real end-to-end desde el frontend**

