# TODO — HYGIENE.1: basura raíz + gitignore ✅
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
