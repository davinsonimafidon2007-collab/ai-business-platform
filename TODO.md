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

**Siguiente tras desbloquear (o en paralelo):** **FIRE.1** — smoke login Google/Firebase en front + backend.

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

**Siguiente tras desbloquear:** Firebase auth smoke **o** SMTP real para J.1/C.2.

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
