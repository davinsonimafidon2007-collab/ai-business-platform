# Ops — Operabilidad básica (DEVOPS-001 / Task P3-002)

Esta guía cubre la **operabilidad mínima de producción temprana**: healthcheck
compuesto, backups Postgres, correlación de logs y alertas de jobs. El stack
completo de observabilidad (Prometheus/Grafana/OpenTelemetry) queda como **fase 2
documentada**, no bloqueante.

---

## 1. Healthcheck compuesto (API + DB + Redis)

`GET /health` (también en `GET /api/v1/health`) devuelve:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "providers": ["mobile_de", "autoscout24", "..."],
  "checks": {
    "api": "ok",
    "database": "ok",
    "redis": "ok"
  }
}
```

### Semántica

| `status` | HTTP | Significado |
|----------|------|-------------|
| `ok`      | 200 | API + DB ok; Redis ok (o `disabled` porque es opcional). |
| `degraded`| 200 | API + DB ok; Redis `error` o `disabled`. La API sigue sirviendo. |
| `error`   | 503 | **DB caída** — el servicio no es operativo. |

Reglas de decisión (implementadas en `app/api/v1/routes/health.py`):

- `database`: `SELECT 1` vía el engine compartido (`app.database.db_manager`) con
  timeout corto (2s) para no bloquear el event loop.
- `redis`: `PING` soft si hay cliente (`app.core.redis.get_redis()`). Si no hay
  cliente → `disabled`; si el PING falla → `error`.
- **DB down → 503** (nunca `ok`). **Redis error/disabled → `degraded`** (200),
  coherente con INFRA-001: en producción Redis es obligatorio al boot, pero una
  caída en runtime degrada sin tumbar la API.

### Verificación

```bash
docker compose up -d
curl -s http://localhost:8000/health | jq .

# Parar redis → status degraded, checks.redis=error (o disabled si no había client)
docker compose stop redis
curl -s http://localhost:8000/health | jq .status   # "degraded"

# Parar db → status error, HTTP 503
docker compose stop db
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health   # 503
# Restaurar
docker compose start db redis
```

> El healthcheck del contenedor `api` en `docker-compose.yml` usa
> `curl -f http://localhost:8000/health`; con DB caída devuelve 503 y el
> contenedor se marca unhealthy (correcto).

---

## 2. Backups Postgres

Scripts en `scripts/`:

- **`backup_postgres.sh`** — `pg_dump -Fc` (custom) a `backups/postgres_YYYYMMDD_HHMMSS.dump`,
  retención de los últimos `BACKUP_RETENTION` (default 7). Usa `DATABASE_URL`
  (normaliza `postgresql+asyncpg://` → `postgres://`) o variables `PG*`.
- **`restore_postgres.sh <dump> [--force]`** — `pg_restore --clean --if-exists`.
  Pide confirmación salvo `--force`. **Destructivo**: restaura reemplazando los
  datos actuales.

```bash
chmod +x scripts/backup_postgres.sh scripts/restore_postgres.sh

# Backup manual
./scripts/backup_postgres.sh

# Restore (pedirá confirmación)
./scripts/restore_postgres.sh backups/postgres_20260810_030000.dump
# Sin confirmar:
./scripts/restore_postgres.sh backups/postgres_20260810_030000.dump --force
```

### Cron de ejemplo (diario 03:00)

```cron
0 3 * * * cd /app && ./scripts/backup_postgres.sh >> /var/log/backup_postgres.log 2>&1
```

### Variables

```env
BACKUP_DIR=./backups
BACKUP_RETENTION=7
```

`backups/` está en `.gitignore` — **nunca** se commitean dumps con datos reales.

---

## 3. Logging estructurado y correlación

El access log (`app/middleware/logging_middleware.py`) ya emite por request:

```json
{
  "timestamp": "...",
  "request_id": "<uuid o X-Request-ID>",
  "correlation_id": "...",
  "method": "GET",
  "path": "/health",
  "status": 200,
  "duration_ms": 12.34,
  "ip": "...",
  "user_agent": "..."
}
```

- `request_id` lo genera `RequestIdMiddleware` (o se respeta el `X-Request-ID`
  del cliente); se propaga en estado de request y en la respuesta
  (`X-Request-ID` / `X-Correlation-ID`).
- `duration_ms` ya está presente (PERF-001) — no se añade proveedor SaaS
  (Sentry) obligatorio. Si algún día se quiere, el hook queda documentado aquí
  como opcional, sin añadir dependencia en este task.

### Fase 2 (documentada, no bloqueante)

- Exponer `/metrics` Prometheus desde la API (aún no existe).
- `docker-compose.obs.yml` ya prepara el perfil `obs` (Prometheus + Grafana):

```bash
docker compose --profile obs up -d
# Prometheus: http://localhost:9090 · Grafana: http://localhost:3001 (admin/$GRAFANA_ADMIN_PASSWORD)
```

- `app/telemetry/` es un placeholder a la espera de esa fase. No se añaden
  dependencias `opentelemetry-*` aquí.

---

## 4. Alertas de jobs (JobFailureAlertService)

`app/services/job_failure_alert_service.py` notifica (email o log) cuando un job
acumula `consecutive_failures >= JOB_FAILURE_ALERT_THRESHOLD`, con cooldown por
job de `JOB_FAILURE_ALERT_COOLDOWN_HOURS`.

### Variables (`.env`)

```env
JOB_FAILURE_ALERT_ENABLED=true
JOB_FAILURE_ALERT_THRESHOLD=3
JOB_FAILURE_ALERT_COOLDOWN_HOURS=6
# Vacio = solo log (dry-run), no envia email
JOB_FAILURE_ALERT_TO_EMAIL=
```

Comportamiento (cubierto por `tests/unit/test_job_failure_alert_service.py`):

- Sin `JOB_FAILURE_ALERT_TO_EMAIL` ni SMTP → **solo log** (WARNING), nunca
  crashea.
- Con `SMTP_*` configurado y `JOB_FAILURE_ALERT_TO_EMAIL` → envía email real.
- Cooldown por `job_name` para no spamear mientras la racha persiste.

> No se reescribe el servicio: ya está testeado. Este task solo verifica su
> cableado con `config.py` / `.env.example` y lo documenta.

Smoke de envío real (SMTP):

```bash
python scripts/smoke_smtp.py --job-failure --to ops@example.com
# requiere SMOKE_SMTP=1 para enviar por SMTP; si no, solo log
```

---

## 5. Observabilidad fase 2 (opcional)

Stack completo Prometheus/Grafana/OpenTelemetry queda como **fase 2 documentada
y no bloqueante**. Se puede activar con el perfil `obs` de
`docker-compose.obs.yml` cuando la API exponga `/metrics`. No se fuerza en
`docker compose up` por defecto ni en CI.

---

## Checklist de aceptación (task)

1. `GET /health` reporta checks de DB y Redis.
2. DB down → health no dice `ok` (503 + `status=error`).
3. Scripts `backup_postgres.sh` / `restore_postgres.sh` existen y están documentados.
4. `backups/` ignorado por git.
5. Access logs con `request_id` (+ `duration_ms`).
6. Alertas de jobs documentadas en `.env.example` + esta doc.
7. Tests unitarios de health verdes.
8. No se fuerza Grafana en `docker compose up` por defecto (perfil `obs`).
