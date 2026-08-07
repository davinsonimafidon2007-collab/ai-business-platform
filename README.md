# ai-business-platform

### Continuidad entre sesiones de IA

Ver [docs/HANDOFF_GROK_NEXT_SESSION.md](docs/HANDOFF_GROK_NEXT_SESSION.md) antes de proponer el siguiente task.

## Bootstrap local

### Requisitos

- **Python 3.13.x** (obligatorio). Python 3.14 **no está soportado** todavía:
  algunas dependencias con binarios nativos (p. ej. `lxml`) aún no publican
  wheels para 3.14 en Windows y fallan al compilar. Usa 3.13.x.
- PostgreSQL 15+ (o 14+)
- Redis 7 (opcional en local; obligatorio en producción)
- Node 20+ (solo si levantas el frontend)
- [uv](https://github.com/astral-sh/uv) recomendado
- Docker + Docker Compose (si usas el stack contenedorizado)

> **Python 3.14:** `scripts/release_check.py` abortará con exit 2 si detecta
> 3.14. Fija el runtime con `uv python pin 3.13` (o `uv venv --python 3.13`).

### 1. Clonar / abrir el proyecto

```bash
cd "ruta/al/proyecto"
```

### 2. Docker Compose (stack completo API + Postgres + Redis)

```bash
docker compose up --build
```

Esto levanta:

- API → http://localhost:8000
- Postgres → localhost:5432
- Redis → localhost:6379

La API solo pasa el healthcheck cuando Redis y Postgres están `healthy`.
Para parar:

```bash
docker compose down -v   # -v elimina los volúmenes (DB y Redis)
```

### 2-alt. Entorno Python local (sin Docker)

```bash
uv sync --group dev
# o: python -m venv .venv && .venv/Scripts/activate  # Windows
#    pip install -e ".[dev]"
```

### 3. Archivo .env

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegar el valor generado en `.env`:

```env
JWT_SECRET_KEY=<el_valor_generado>
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/ai_business_platform
ENVIRONMENT=development
```

Crear la base si no existe:

```bash
# psql como superuser
createdb ai_business_platform
# o: CREATE DATABASE ai_business_platform;
```

### 4. Migraciones (OBLIGATORIO)

Head canónico actual: `g1h2i3j4k5l6`

```bash
uv run alembic upgrade head
uv run alembic heads          # debe devolver exactamente 1 head
uv run alembic current
```

Si `upgrade` falla por datos huérfanos / FK en una DB ya existente:

- Revisar el mensaje de la migración que falla (habitualmente `d6e7f8a9b0c1` o `f8a9b0c1d2e3`).
- En **development** es aceptable limpiar tablas de tokens/keys/vehicles huérfanos y reintentar.
- En **production** usar un plan de migración de datos (no `DROP`).

Migraciones recientes relevantes si vienes de un schema antiguo:

- `d6e7f8a9b0c1` — vehicles.user_id NOT NULL + índices
- `e7f8a9b0c1d2` — search_history.user_id
- `f8a9b0c1d2e3` — FK api_keys / refresh_tokens → users
- `e2f3a4b5c6d7` — tabla deals
- `f2a3b4c5d6e8` — last_simulation en deals
- `g1h2i3j4k5l6` — explanation en cached_market_data

> **Nota:** Los revision IDs históricos (`g1h2i3j4k5l6`, `a1b2c3d4e5f7`, etc.) se mantienen
> por compatibilidad con bases de datos ya migradas. Las **nuevas** migraciones deben
> generarse con `alembic revision --autogenerate -m "..."`.

### 5. Arrancar API

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Smoke:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/v1/health
```

Ambos deben responder 200.

### Release local (orden recomendado) — SMOKE.CRIT.1

```powershell
$env:ENVIRONMENT="test"
$env:JWT_SECRET_KEY="test_secret_key_that_is_at_least_32_characters_long_1234567890"

# 1) Integraciones (informe; smtp/firebase/proxy pueden BLOCKED)
python scripts/check_integrations_ready.py

# 2) Unit + sync deps (sin HTTP)
python scripts/release_check.py --skip-smoke

# 3) API arriba (compose o uvicorn)

# 4) Smoke HTTP camino crítico
$env:BASE_URL="http://localhost:8000"
python scripts/smoke_critical_path.py
python scripts/smoke_critical_path.py --with-opportunities
# Admin + bloque providers (credenciales ADMIN):
python scripts/smoke_critical_path.py --with-admin
```

| Exit | Significado |
|------|-------------|
| 0 | OK |
| 1 | Aserción / HTTP inesperado |
| 2 | Setup (API caída) |

**E2E manual (UI):** [docs/E2E_MANUAL_CHECKLIST.md](docs/E2E_MANUAL_CHECKLIST.md) — drawer labels, cost_lines, warnings. El smoke HTTP **no** sustituye esa pasada visual.

#### Usuario ADMIN para smoke

Para `--with-admin` necesitas un user con rol `ADMIN`. Puedes crearlo (o
promover uno existente) con el script idempotente ya incluido:

```bash
# Crea/promueve un admin (interactivo, o con ADMIN_EMAIL/ADMIN_PASSWORD en .env)
uv run python -m app.scripts.create_admin
```

Después, pasa las credenciales al smoke:

```powershell
$env:SMOKE_ADMIN_EMAIL="ops@example.com"
$env:SMOKE_ADMIN_PASSWORD="..."
python scripts/smoke_critical_path.py --with-admin
# o: python scripts/smoke_critical_path.py --with-admin --admin-email ... --admin-password ...
```

Alternativa manual en DB:

```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'ops@example.com';
```

### E2E manual (camino crítico)

Checklist: [docs/E2E_MANUAL_CHECKLIST.md](docs/E2E_MANUAL_CHECKLIST.md) (Task E2E.MANUAL.1).

Antes: `check_integrations_ready`, `smoke_es_providers`, API + front up.

### 6. Registro de prueba

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"demo@example.com\",\"password\":\"password123\"}"
```

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"demo@example.com\",\"password\":\"password123\"}"
```

Guardar `access_token` y llamar:

```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### 7. Frontend (opcional)

```bash
cd frontend
cp .env.example .env.local   # si existe; si no, NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Abrir `http://localhost:3000`.

### 8. Scheduler

Con `ENABLE_SCHEDULER=true` los jobs arrancan con la API (cleanup diario, refresh opportunities paginado). Para desactivar en debug:

```env
ENABLE_SCHEDULER=false
```

### Problemas frecuentes

| Síntoma | Causa | Acción |
|---------|--------|--------|
| `JWT_SECRET_KEY must be set and at least 32 characters` | `.env` vacío o corto | Generar secreto ≥32 |
| Error al importar settings | JWT / env | Revisar `ENVIRONMENT` y `.env` cargado desde el cwd |
| Tablas no existen | Migraciones no corridas | `alembic upgrade head` |
| Login 401 inactive | User desactivado | Admin reactiva o nuevo registro |
| 429 en login | Rate limit login=5/min | Esperar o reiniciar proceso API (límites en memoria) |
| Scrapers vacíos | HTML de mobile.de/AS24 cambió | Revisar logs del provider; no es fallo de bootstrap |

### Seguridad (SEC-001) — CORS / Firebase / secretos

- **JWT obligatorio**: `JWT_SECRET_KEY` debe tener ≥ 32 caracteres o la app no
  arranca (excepto `environment=test`, que inyecta un secret de test).
- **CORS estricto en production**: con `ENVIRONMENT=production`, `CORS_ORIGINS`
  debe ser una lista explícita y real (dominios HTTPS del frontend). Están
  prohibidos `*`, la lista vacía y una lista con **solo** orígenes de desarrollo
  (localhost / capacitor / ionic). Si se infringe, `Settings` no carga y la API
  no arranca. En production un `CORS_ALLOW_HEADERS=*` se endurece
  automáticamente a una lista explícita
  (`Authorization,Content-Type,Accept,X-Request-ID,X-API-Key,X-Requested-With`).
  En development/test se mantienen los defaults de localhost/Capacitor.
- **Firebase opcional en dev, configurable como requerido en prod**:
  `FIREBASE_REQUIRED=false` por defecto. Sin credenciales en development/test la
  API arranca igual (WARNING, Google Login deshabilitado). En production:
  - `FIREBASE_REQUIRED=false` → WARNING/ERROR al boot; los endpoints de Google
    Login devuelven error claro al usarse.
  - `FIREBASE_REQUIRED=true` → la API **no arranca** si no hay credenciales
    (`RuntimeError` en el boot, fail-fast).
- **API keys hasheadas (Argon2)**: solo se persiste `key_hash` (vía
  `pwdlib.PasswordHash.recommended()`) + `prefix`. El secreto bruto solo se
  muestra **una vez** al crear la key; ningún listado devuelve `key_hash` ni la
  key completa. `verify` usa `password_hasher.verify` (con sal aleatoria, no se
  busca por igualdad de hash).

### 9. Verificación en vivo de providers (mobile.de / AutoScout24)

> **Runbook mobile.de con proxy:** ver [`docs/PROXY_MOBILE_DE.md`](docs/PROXY_MOBILE_DE.md)
> para configurar proxy residencial / cookies y pasar el canary de mobile.de a PASS.

Smoke script que instancia el cliente HTTP anti-bot de producción y lanza
una búsqueda + detalle contra cada provider:

```bash
uv run python scripts/verify_providers_live.py
uv run python scripts/verify_providers_live.py --save-html $env:TEMP\provider_html   # Windows
```

Proxy/cookies/delay se leen de `.env` (`PROVIDER_HTTP_PROXY`,
`PROVIDER_HTTP_COOKIES`, `PROVIDER_HTTP_MIN_DELAY_MS`); no hay secretos en
el código. Salida esperada por provider: `search: OK count=N` y
`detail: OK brand=... model=... price=...`. Significado de fallos:

- **403 / `ProviderConnectionError`** → IP bloqueada por anti-bot. Hace
  falta proxy residencial o cookies de navegador real.
- **429 / `ProviderRateLimitError`** → rate limit del provider. Subir
  `PROVIDER_HTTP_MIN_DELAY_MS` (800–1500) o usar proxy rotativo.
- **`count=0`** → la página llegó pero los selectores no encontraron
  anuncios (selector drift o página anti-bot vacía). Guardar con
  `--save-html` para revisar selectores en A.4.

Exit 0 = ambos providers OK; 1 = alguno falló; 2 = error de setup.
### Smoke mercado ES (SMOKE.ES)

Verifica los providers offline de destino ES y, opcionalmente, un search real
contra AutoScout24 España **sin tocar** proxy / SMTP / Firebase.

```bash
# Offline (fixtures; siempre)
python scripts/smoke_es_providers.py

# Snapshot del registry (flags + perfil)
python scripts/smoke_es_providers.py --registry

# Live AS24-ES (opcional; requiere ENABLE_AUTOSCOUT24_ES=true)
python scripts/smoke_es_providers.py --live-as24-es
```

Exit 0 = OK; 1 = fallo de aserción / error inesperado; 2 = skip de live.


### Ops — readiness (OPS.READY)

```bash
python scripts/check_integrations_ready.py
python scripts/check_integrations_ready.py --strict   # jwt + db + fixtures
```

BLOCKED en smtp/firebase/proxy es esperado sin credenciales (app sigue up).

### Ops — Health compuesto / Backups / Observabilidad (DEVOPS-001 / P3-002)

Guía completa en [`docs/ops.md`](docs/ops.md). Resumen:

- **Health compuesto**: `GET /health` (y `GET /api/v1/health`) reporta
  `checks.api / database / redis`. `ok`→200, `degraded` (Redis down/disabled)→200,
  `error` (DB down)→**503**. DB nunca puede decir `ok` si está caída.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "providers": ["..."],
  "checks": {"api": "ok", "database": "ok", "redis": "ok"}
}
```

- **Backups Postgres**: `scripts/backup_postgres.sh` (`pg_dump -Fc` +
  retención, default 7) y `scripts/restore_postgres.sh` (pide confirmación).

```bash
chmod +x scripts/backup_postgres.sh scripts/restore_postgres.sh
./scripts/backup_postgres.sh
# cron: 0 3 * * * cd /app && ./scripts/backup_postgres.sh
```

  `backups/` está en `.gitignore` — no se commitean dumps con datos reales.

- **Logging**: access log ya incluye `request_id`, `correlation_id`, `method`,
  `path`, `status` y `duration_ms` (PERF-001). Sin proveedor SaaS obligatorio.
- **Alertas de jobs**: `JobFailureAlertService` documentado con vars
  `JOB_FAILURE_ALERT_*` (ver `.env.example`). Sin SMTP/to_email → solo log.
- **Observabilidad fase 2 (opcional)**: `docker compose --profile obs up -d`
  activa Prometheus (9090) + Grafana (3001) sin forzarlo el `docker compose up`
  normal ni CI. No se añade dependencia `opentelemetry-*` en este task.

### Runbook — Alertas por email (SMTP) — Task SMTP.1

El backend ya incorpora dos servicios de alerta por email que reutilizan el
mismo `SmtpEmailProvider` (`app/notifications/email_provider.py`):

- **J.1 — `JobFailureAlertService`**: avisa por email cuando un job acumula una
  racha de fallos `>= JOB_FAILURE_ALERT_THRESHOLD` (default 3), con cooldown por
  job (`JOB_FAILURE_ALERT_COOLDOWN_HOURS`, default 6h).
- **C.2 — `OpportunityAlertService`**: avisa cuando una oportunidad supera el
  umbral (`OPPORTUNITY_ALERT_MIN_RECOMMENDATION`/`..._MIN_SCORE`), con cooldown
  por vehículo (`OPPORTUNITY_ALERT_COOLDOWN_HOURS`, default 24h).

#### Variables (`.env`)

```env
# --- SMTP / Email ---
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<secreto>
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_USE_TLS=true

# Oportunidades (C.2)
OPPORTUNITY_ALERT_ENABLED=true
OPPORTUNITY_ALERT_MIN_RECOMMENDATION=BUY
OPPORTUNITY_ALERT_MIN_SCORE=0
OPPORTUNITY_ALERT_COOLDOWN_HOURS=24

# Job failure (J.1)
JOB_FAILURE_ALERT_ENABLED=true
JOB_FAILURE_ALERT_THRESHOLD=3
JOB_FAILURE_ALERT_COOLDOWN_HOURS=6
JOB_FAILURE_ALERT_TO_EMAIL=ops@yourdomain.com
```

> **Sin `SMTP_HOST` / sin `JOB_FAILURE_ALERT_TO_EMAIL` → solo log; no falla la
> app.** Ambos servicios (y el `EmailProvider`) entran en modo *dry-run*: loguean
> el email que habrían enviado y no lanzan excepciones. Esto es intencional y
> está cubierto por los tests unitarios.

#### Smoke de envío real

```bash
# Verifica que SMTP está configurado y envía 1 email de prueba.
# Exit 2 = falta configurar SMTP_HOST/SMTP_USER; Exit 1 = error de envío; Exit 0 = enviado.
python scripts/smoke_smtp.py
python scripts/smoke_smtp.py --to ops@example.com

# Smoke casi-E2E de J.1 (JobFailureAlertService con umbral=1 y sender real).
# Solo envía por SMTP si está activado SMOKE_SMTP=1.
$env:SMOKE_SMTP="1"; python scripts/smoke_smtp.py --to ops@example.com --job-failure
```

Para una prueba manual J.1 sin esperar 3 fallos reales: pon
`JOB_FAILURE_ALERT_THRESHOLD=1` temporalmente, fuerza un fallo de un job y
revisa el email; restaura el umbral después. **No dejes secretos SMTP en el
repo** (`SMTP_PASSWORD` vive solo en `.env`, que está en `.gitignore`).


### Runbook — Firebase / Google login — Task FIRE.1

El login con Google ya está implementado de punta a punta (front + backend):

- **Front** (`frontend/src/app/config/firebase.ts` + `frontend/src/app/services/google-auth.ts`):
  flujo popup (web) / Capacitor → `POST /api/v1/auth/google` con el `id_token` de
  Firebase Auth. La configuración web es **pública** (apiKey, projectId, etc.) y no
  requiere service account.
- **Backend** (`app/core/firebase.py` → `app/api/v1/auth.py` → `AuthService.authenticate_with_google`):
  verifica el `id_token` con el **Admin SDK** y, por tanto, **necesita una service
  account** (`FIREBASE_CREDENTIALS_JSON` o `FIREBASE_CREDENTIALS_PATH`).

> **Sin `FIREBASE_*` → la app arranca igual y no crashea.** `verify_google_id_token`
> responde un error de autenticación (401) y el resto de flows (register/login email)
> siguen funcionando. Esto está cubierto por los tests.

#### Variables (`.env`)

```env
# --- Firebase (Google Login) ---
# Service account JSON string OR path. Never commit real credentials.
FIREBASE_CREDENTIALS_JSON=
FIREBASE_CREDENTIALS_PATH=
```

Solo necesitas **una** de las dos. El JSON/path se lee desde `settings` (pydantic,
`.env`) y desde env, por si pruebas manualmente.

#### Smoke

```bash
# 1) Sin credenciales → exit 2 (setup)
python scripts/smoke_firebase.py

# 2) Con service account en .env, sin token → exit 0 "Firebase OK (init only)"
python scripts/smoke_firebase.py

# 3) Con un ID token real → verify + email/uid (exit 0/1)
python scripts/smoke_firebase.py --id-token "eyJ..."

# 4) + API en marcha: además POST /api/v1/auth/google (espera 200 + tokens)
python scripts/smoke_firebase.py --id-token "eyJ..." --call-api
```

Exit codes: **0** init/verify/API OK · **1** error de verify/API · **2** setup sin
`FIREBASE_*`.

#### Cómo obtener un ID token de prueba

1. Login Google en el **front** → DevTools **Network** → `POST .../auth/google` →
   copiar el `id_token` del body.
2. O desde **Firebase Auth emulator / console**: `firebase.auth().currentUser.getIdToken()`.
3. Usarlo en el smoke: `python scripts/smoke_firebase.py --id-token "<tok>" [--call-api]`.

> **No** comprometas la service account: `FIREBASE_CREDENTIALS_JSON` /
> `FIREBASE_CREDENTIALS_PATH` viven solo en `.env` (gitignored) y nunca en el repo.


### Dependencias — `requirements.txt` es GENERATED

`requirements.txt` es un **fichero generado** (NO editar a mano). La fuente de
verdad es `pyproject.toml` (+ `uv.lock`). Para regenerarlo:

```powershell
uv export --no-hashes --no-dev --no-emit-project -o requirements.txt
# o, para runtime + dev:
powershell -ExecutionPolicy Bypass -File scripts/export_requirements.ps1
```

### Checklist release local
Un solo comando para orquestar las comprobaciones mínimas antes de considerar un
build "listo para staging": sync de `requirements.txt` → pytest unitario → smoke
(camino crítico + ext. opcionales). Se detiene con exit ≠ 0 al primer fallo.

```bash
# Solo deps + unit (sin API)
python scripts/release_check.py --skip-smoke

# Completo con API en :8000
python scripts/release_check.py --with-api --with-opportunities

# Unit + integración crítica (INT.1) sin smoke
python scripts/release_check.py --skip-smoke --with-integration
```

Semántica de exit y flags:

- **exit 0** = `RELEASE CHECK PASSED`. **exit ≠ 0** = falló algún paso
  (1 = requirements out-of-sync / fallo de aserción; 2 = setup, p.ej. API caída).
- Sin `--with-api`, el smoke es **opcional**: si la API no responde (exit 2 del
  smoke) el release de solo `deps + unit` se marca `SKIP: smoke (API not
  reachable)` y continúa. Para **exigir** que la API esté up, usa `--with-api`
  (recomendado para staging).
- `--skip-requirements` / `--skip-pytest` / `--skip-smoke`: debug rápido.
- `--with-integration`: además de unit, ejecuta el subconjunto crítico de
  integration (Task INT.1): `test_admin_status_api`, `test_api_keys_api`,
  `test_admin_api_keys_api`, `test_auth_api`, `test_vehicles_api`. Corre bajo
  `ENVIRONMENT=test` y un `JWT_SECRET_KEY` de test (≥32 chars). Default: off.
- `--with-opportunities` / `--with-admin`: extienden el smoke (ver
  "Smoke camino crítico"). `--with-admin` requiere `SMOKE_ADMIN_EMAIL` /
  `SMOKE_ADMIN_PASSWORD` o `--admin-email` / `--admin-password`.
- `--pytest-args "tests/unit -q"`: subset de tests (default `tests/unit -q`).

### Verificar sync (CI / local)

```bash
python scripts/check_requirements_sync.py
# exit 0 = OK; exit 1 = regenerar con scripts/export_requirements.ps1
```

### CI (GitHub Actions) — CI.1 + CI.2

Workflow: `.github/workflows/ci.yml`

En cada push/PR a `main` (y `master` si existe):

1. `uv sync --locked --group dev`
2. `python scripts/check_requirements_sync.py` (exit 0 = `requirements.txt` alineado con `uv export`)
3. Service **Postgres 16** (`postgres:16-alpine` + healthcheck) y `alembic upgrade head`
4. `pytest tests/unit -q`
5. Integration crítico (INT.1): `test_admin_status_api`, `test_api_keys_api`,
   `test_admin_api_keys_api`, `test_auth_api`, `test_vehicles_api` — mismo
   subconjunto que `release_check.py --with-integration`

Local equivalente:

```bash
python scripts/release_check.py --skip-smoke
# o con integration crítico:
python scripts/release_check.py --skip-smoke --with-integration
```

Verificar migraciones contra un Postgres limpio (como hace CI):

```powershell
docker run --rm -d --name abp-pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ai_business_platform_test -p 5432:5432 postgres:16-alpine
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_business_platform_test"
uv run alembic upgrade head
# docker stop abp-pg-test
```

No incluye: smoke E2E, providers live, SMTP, Firebase verify real, frontend.

### Rendimiento (PERF-001) — rate-limit/cache distribuido + paginación segura

- **Rate limiting**: Redis primero (distribuido); si Redis no está disponible cae
  a contadores en memoria (fail-soft, mismo patrón que el cache L1). Toda
  respuesta del middleware incluye `X-RateLimit-Mode: redis|memory`. En
  **production**, una degradación a memoria loguea `ERROR` (throttled a ~1
  log/10s por proceso) — nunca es silenciosa. En production la app no arranca
  sin Redis (P0-001), así que este fallback solo cubre caídas en runtime.
- **Cache de mercado**: L1 en **Redis** (`market:est:*`) + L2 en **Postgres**
  (`cached_market`) + `_local_cache` en proceso. Si Redis cae, se sigue sirviendo
  desde Postgres / cómputo en vivo (fail-soft). Sin Redis no se debilita: en
  production Redis es obligatorio.
- **Paginación segura**: los listados críticos (`/vehicles`, `/deals`,
  `/opportunities`, `/searches`) validan `limit` en `[1, 100]` (422 si se supera)
  y los repositorios además recortan a 100 por defensa en profundidad
  (`app/core/limits.py::clamp_limit`). `offset >= 0`.
- **Métricas mínimas de latencia**: `AccessLogMiddleware` ya emite
  `duration_ms` en el log estructurado de cada request (sin Prometheus/OTEL;
  eso es DEVOPS-001).

Verificación local:

```bash
docker compose up -d redis
.venv/Scripts/python.exe -m pytest tests/unit/test_rate_limit_mode.py tests/unit/test_pagination_caps.py -q
.venv/Scripts/python.exe -m pytest tests/unit -q
```

### Modelo de costes de importación (ECON-001)

Los perfiles de costes viven en `app/config/import_costs_data.json` (versionado,
`version: "2026.08"`). Al importar `app.config.import_costs`, el módulo carga los
perfiles desde el archivo; si el archivo falta, usa los defaults embebidos con un
warning (fallback).

Campos del perfil:
- Costes fijos (EUR): `transport_cost`, `registration_cost`, `inspection_cost`
  (ITV), `paperwork_cost` (gestoría), `miscellaneous_cost`.
- Costes variables (fracción del precio de compra): `tax_rate` (impuestos),
  `commission_rate` (comisión), `repair_estimate_rate` (reparación estimada).
- Umbrales de riesgo: `risk_{high,low}_{roi,profit,cost_ratio}_threshold`.

Los valores fuera de rango lanzan `ValueError` (fail-fast) al cargar/construir:
- costes fijos en `[0, 50000]`; tasas en `[0, 0.5]`; ROI `0 <= low < high <= 1`;
  profit `0 <= low < high`; cost_ratio `0 <= low < high <= 3` (el perfil DEFAULT
  legado usa `2.0`, por lo que el tope sube por encima de 1 — ver nota en el código).

`ProfitAnalysis.warnings` ofrece avisos no bloqueantes (disclaimer de estimación y
aviso si los costes de importación superan el 50% del precio de compra).

El `CostBreakdown` expone cada componente con label legible vía
`breakdown.components()` (lista de `{key, label, kind, amount}` en EUR, p. ej.
`transport_cost` → "Transporte", `registration_cost` → "Matriculación",
`inspection_cost` → "ITV / inspección", `taxes` → "Impuestos (sobre compra)",
`commission_cost` → "Comisión", `repair_estimate` → "Reparaciones estimadas") y
`breakdown.as_dict()` para serialización plana. Útil para explicar en el front
cada partida sin duplicar nombres técnicos.

Para actualizar costes 2026:
1. Editar `app/config/import_costs_data.json`.
2. Ejecutar `pytest tests/unit/test_profit_analyzer.py tests/unit/test_import_costs_validation.py tests/unit/test_import_cost_default_wiring.py -q`.
3. No hardcodear valores en el analyzer.

> Los valores son **estimaciones de trabajo**, no asesoramiento fiscal. Deben
> contrastarse con gestoría, ITV, DGT/ISV según el caso.

### Fuera de este bootstrap

- Tests (`TODO.md`, sesión paralela)
- CRUD HTTP de API keys
