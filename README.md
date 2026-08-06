# ai-business-platform

### Continuidad entre sesiones de IA

Ver [docs/HANDOFF_GROK_NEXT_SESSION.md](docs/HANDOFF_GROK_NEXT_SESSION.md) antes de proponer el siguiente task.

## Bootstrap local

### Requisitos

- **Python 3.13.x** (obligatorio). Python 3.14 **no está soportado** todavía:
  algunas dependencias con binarios nativos (p. ej. `lxml`) aún no publican
  wheels para 3.14 en Windows y fallan al compilar. Usa 3.13.x.
- PostgreSQL 15+ (o 14+)
- Node 20+ (solo si levantas el frontend)
- [uv](https://github.com/astral-sh/uv) recomendado

> **Python 3.14:** `scripts/release_check.py` abortará con exit 2 si detecta
> 3.14. Fija el runtime con `uv python pin 3.13` (o `uv venv --python 3.13`).

### 1. Clonar / abrir el proyecto

```bash
cd "ruta/al/proyecto"
```

### 2. Entorno Python

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

Head actual esperado: `f8a9b0c1d2e3`

```bash
alembic upgrade head
alembic heads
alembic current
```

Si `upgrade` falla por huérfanos / FK:

- Leer el mensaje de la migración `f8a9b0c1d2e3` / `d6e7f8a9b0c1`
- En dev es aceptable vaciar tablas de tokens/keys/vehicles huérfanos y reintentar

Migraciones recientes que deben aplicarse si vienes de un schema viejo:

- `d6e7f8a9b0c1` — vehicles.user_id NOT NULL + índices
- `e7f8a9b0c1d2` — search_history.user_id
- `f8a9b0c1d2e3` — FK api_keys / refresh_tokens → users

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

### Smoke camino crítico
```bash
# API en marcha en :8000
python scripts/smoke_critical_path.py
# BASE_URL=http://127.0.0.1:8000 python scripts/smoke_critical_path.py
```
Exit 0 = flujo register→vehicle→deal→simulation→OFFER OK.
Exit 1 = fallo de aserción/HTTP; Exit 2 = API caída o setup.

Variantes opcionales (Task E2E.2):

```bash
python scripts/smoke_critical_path.py --with-opportunities   # GET /opportunities?limit=5 → 200
python scripts/smoke_critical_path.py --with-admin           # requiere user ADMIN
```

- `--with-opportunities`: además del camino crítico, valida el listado de
  oportunidades (puede estar vacío en una DB limpia).
- `--with-admin`: además del camino crítico, hace login como ADMIN y llama
  `GET /api/v1/admin/status` (imprime `redis_ok`, `jobs` count y
  `canary.success`). Sin credenciales sale con exit 1.

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

> **CI pendiente:** cuando exista GitHub Actions u otro CI, añadir un workflow que
> ejecute `python scripts/check_requirements_sync.py` (Task C.1). El script ya
> existe; solo hay que invocarlo.

### Fuera de este bootstrap

- Tests (`TODO.md`, sesión paralela)
- Redis como backend de rate limit
- CRUD HTTP de API keys
