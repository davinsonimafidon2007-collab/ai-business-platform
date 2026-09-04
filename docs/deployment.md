# Deployment — Guía de despliegue (Bloque 6 / DEVOPS)

Guía para desplegar y operar la AI Business Platform en entornos
**staging** y **producción**, con health checks, backups, observabilidad
(Prometheus/Grafana), logging centralizado opcional y validación
post-despliegue.

---

## 1. Arquitectura de despliegue

`docker compose up -d` levanta el stack principal (definido en
`docker-compose.yml`):

| Servicio  | Imagen/contexto      | Puerto host (default) | Puerto interno |
|-----------|----------------------|-----------------------|----------------|
| `api`     | `./Dockerfile`       | `8001` (`API_PORT`)   | `8000`         |
| `frontend`| `./frontend/Dockerfile` | `3001` (`FRONTEND_PORT`) | `3000`     |
| `db`      | `postgres:16-alpine` | `5433`                | `5432`         |
| `redis`   | `redis:7-alpine`     | `6380` (`REDIS_PORT`) | `6379`         |

Los puertos host se evitaron deliberadamente contra el rango por defecto
(8000/3000/5432/6379) para no chocar con otros proyectos del host (p.ej.
`agentesdeia`). **Dentro de la red docker** la API se llama `api:8000`, la BD
`db:5432` y Redis `redis:6379` (esto importa para Prometheus y los exporters).

### Perfiles opcionales

- **Observabilidad**: `docker compose --profile obs up -d`
  (Prometheus + Grafana + exporters; ver §5).
- **Logging centralizado**: `docker compose --profile logging up -d`
  (Fluentd + Elasticsearch + Kibana; ver §6).

---

## 2. Health checks

Todos los servicios del stack principal tienen healthcheck en
`docker-compose.yml`:

- `db` → `pg_isready -U postgres -d ai_business_platform`
- `redis` → `redis-cli ping`
- `api` → `curl -f http://localhost:8000/health/live` (liveness puro,
  TASK-004; no depende de DB/Redis para evitar reinicios en cascada)
- `frontend` → `node` HTTP GET `http://localhost:3000` (Bloque 6)

`depends_on` con `condition: service_healthy` garantiza el orden de arranque:

```
api  → (db healthy, redis healthy)
frontend → (api healthy)
```

La **semántica de `/health`** (endpoint compuesto) en la API:

| `status` | HTTP | Significado |
|----------|------|-------------|
| `ok`      | 200  | API + DB ok; Redis ok (o disabled porque es opcional). |
| `degraded`| 200  | API + DB ok; Redis error/disabled. La API sigue sirviendo. |
| `error`   | 503  | **DB caída** — el servicio no es operativo. |

```bash
docker compose up -d
docker compose ps            # todos "healthy"
curl -s http://localhost:8001/health | jq .status
```

> El healthcheck del contenedor usa `http://localhost:8000/health/live` **dentro
> del contenedor** (puerto interno 8000). Desde el host la API se consulta en
> `http://localhost:8001/health`.

---

## 3. Entornos

> **Este proyecto se despliega en modo PERSONAL (ver §3-bis), no
> multiusuario.** La tabla de abajo describe `.env.production.example` /
> `.env.staging.example`, escritos para un hipotético SaaS multiusuario
> futuro (login real, Firebase) — **no es el modo que se usa hoy**. Si vas
> a desplegar esta app para uso propio, ve directamente a §3-bis y usa
> `.env.personal.example`. Esta sección se conserva por si el proyecto
> pivota a multiusuario más adelante.

Cada entorno usa un archivo **`.env.<entorno>`** en el servidor y variables
propias. Los templates (sin secretos) son `.env.staging.example` y
`.env.production.example`.

| Entorno      | `ENVIRONMENT` | Autenticación            | CORS                     |
|--------------|---------------|--------------------------|--------------------------|
| `development`| `development` | `AUTH_DISABLED=true` (personal) | localhost + Capacitor |
| `staging`    | `staging`     | **siempre auth** (`AUTH_DISABLED=false`) | dominio staging |
| `production` | `production`  | **siempre auth** + `FIREBASE_REQUIRED=true` | solo dominio prod |

Reglas de seguridad de la app (apply-on-boot):

- `JWT_SECRET_KEY` obligatorio y ≥ 32 caracteres (la app no arranca si no).
- `AUTH_DISABLED=true` + `ENVIRONMENT=production` → **no arranca** salvo
  `ALLOW_AUTH_DISABLED_IN_PROD=true` explícito.
- CORS en producción: NUNCA `*`, nunca vacío, no solo localhost/producto
  (SEC-001).
- `FIREBASE_REQUIRED=true` en producción exige credenciales Firebase válidas
  (Google Login vivo) — fail-fast si faltan.

**Pasos por servidor (modo multiusuario, NO es el que usa este proyecto hoy):**

```bash
# 1) Clonar y preparar variables
git clone ... /opt/ai-business-platform
cd /opt/ai-business-platform
cp .env.production.example .env.production   # y rellena con valores reales

# 2) Elegir entorno (docker-compose.yml ya sustituye ${JWT_SECRET_KEY} etc.)
export COMPOSE_ENV_FILE=.env.production      # o usa docker compose --env-file

# 3) Arrancar el stack (con observabilidad)
docker compose --profile obs up -d --build

# 4) Validar despliegue
./scripts/validate_deployment.sh http://localhost
```

---

## 3-bis. Despliegue PERSONAL (el que usa este proyecto hoy) — VPS único + Docker + Caddy

Este proyecto es de **uso personal, sin login** (`AUTH_DISABLED=true`,
ver `AGENTS.md`). No necesita staging, no necesita Firebase/Google Login,
y no tiene sentido pagar dos servidores para un único usuario. Este es el
despliegue real preparado para este proyecto.

### Arquitectura

```
Internet ─▶ Caddy (80/443, único punto público, HTTPS automático)
              ├─▶ api.$DOMAIN      → api:8000
              └─▶ $DOMAIN          → frontend:3000
                                        │
                                   (red interna docker, sin puertos publicados)
                                        ├─▶ db:5432 (Postgres)
                                        └─▶ redis:6379
```

`docker-compose.caddy.yml` es el override que añade Caddy y **quita** la
publicación directa de puertos de `api`/`frontend` al host — el único
punto de entrada público pasa a ser Caddy en 80/443.

### Qué necesitas (recursos externos — ver §"Qué necesitas contratar" al final de este documento)

1. Un VPS pequeño con Docker instalado (2 vCPU / 2-4 GB RAM es de sobra
   para este stack: api + frontend + Postgres + Redis, sin observabilidad).
2. Un **dominio real** con dos registros DNS tipo A apuntando a la IP del
   VPS: `$DOMAIN` y `api.$DOMAIN`. **Sin dominio no hay HTTPS posible** —
   Let's Encrypt (lo que usa Caddy) no emite certificados para IPs desnudas.

### Pasos en el servidor

```bash
# 1) Instalar Docker + compose plugin (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh

# 2) Clonar el repo
git clone https://github.com/<tu-usuario>/ai-business-platform.git /opt/ai-business-platform
cd /opt/ai-business-platform

# 3) Preparar variables — RELLENA los CHANGE_ME antes de continuar
cp .env.personal.example .env.personal
nano .env.personal   # DOMAIN, ACME_EMAIL, JWT_SECRET_KEY, POSTGRES_*, REDIS_PASSWORD

# 4) Arrancar el stack completo (hardening de producción + Caddy)
docker compose \
  -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.caddy.yml \
  --env-file .env.personal \
  up -d --build

# 5) Validar (contra el dominio real, no localhost — confirma que Caddy sirve HTTPS)
API_PORT= FRONTEND_PORT= ./scripts/validate_deployment.sh \
  "https://api.tu-dominio.com" "https://tu-dominio.com"
```

La primera vez que Caddy arranca, pide el certificado a Let's Encrypt
automáticamente — puede tardar hasta 1-2 minutos. Si el DNS todavía no ha
propagado, Caddy reintentará solo; no hace falta reiniciarlo a mano.

### ⚠️ Decisión de seguridad pendiente: API pública sin login

Con `AUTH_DISABLED=true` (el modo de este proyecto), **cualquiera que
descubra `https://api.tu-dominio.com` tiene acceso admin completo** — no
hay login que lo impida (`app/core/config.py::auth_disabled_forbidden_in_production`
lo permite explícitamente con `ALLOW_AUTH_DISABLED_IN_PROD=true`, pero no
añade ninguna barrera de acceso por sí solo). Esto es aceptable si:

- el dominio no se comparte/publicita en ningún sitio indexable, o
- se añade una capa de protección adicional delante de Caddy (elige una,
  no viene preconfigurada — requiere decisión consciente):
  - **VPN/Tailscale**: el VPS solo acepta tráfico de tu red privada; ni
    siquiera queda expuesto a internet. Es la opción más segura, pero el
    móvil necesita la VPN activa para usar la app fuera de casa.
  - **HTTP Basic Auth en Caddy** (`basicauth` directive) delante de
    `api.$DOMAIN`: sencillo de añadir al Caddyfile, pero requiere que la
    app Android también envíe esas credenciales en cada petición — no
    implementado hoy en el cliente HTTP del frontend/mobile.
  - **IP allowlist en Caddy** (`@allowed remote_ip ...`) si tu IP pública
    es estable.

No se implementó ninguna de estas por defecto: es una decisión de
producto (facilidad de acceso vs. superficie de exposición), no algo que
deba decidirse sin ti.

### Backups automáticos (cron)

Igual que en §4 (Backups), pero contra el `.env.personal`:

```cron
0 3 * * * cd /opt/ai-business-platform && \
  DATABASE_URL="postgresql+asyncpg://ai_business:TU_PASSWORD@localhost:5433/ai_business_platform" \
  BACKUP_ENCRYPTION_PASSPHRASE="$SECRET" ./scripts/backup_postgres.sh \
  >> /var/log/backup_postgres.log 2>&1
```

(Postgres no publica puerto al host en este modo — ejecuta el backup
desde dentro del propio servidor, o usa `docker compose exec db pg_dump`
directamente si prefieres no depender de un `localhost:5433` que no existe
en este modo.)

### CI/CD para este despliegue

`.github/workflows/deploy.yml` — un único job `production`, disparado por
cualquier tag `v*`. Ver §7 para los secrets/variables exactos que necesita.

---

## 4. Backups de PostgreSQL

Scripts en `scripts/`:

- **`scripts/backup_postgres.sh`** — `pg_dump -Fc` (formato custom) a
  `backups/postgres_YYYYMMDD_HHMMSS.dump`. Normaliza `DATABASE_URL`
  (`postgresql+asyncpg://` → `postgres://` para pg_dump). Retención de los
  últimos `BACKUP_RETENTION` (default 7). Encriptación opcional AES256 con
  `BACKUP_ENCRYPTION_PASSPHRASE` (gpg) — **recomendada en producción**.
- **`scripts/restore_postgres.sh <dump> [--force]`** — `pg_restore
  --clean --if-exists`; desencripta `.gpg`; pide confirmación salvo `--force`.
  **Destructivo**: restaura reemplazando los datos actuales.

```bash
chmod +x scripts/*.sh
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5433/ai_business_platform" \
  ./scripts/backup_postgres.sh

./scripts/restore_postgres.sh backups/postgres_20260810_030000.dump
```

`backups/` está en `.gitignore` — nunca se commitean dumps con datos reales.

### Cron de backup diario (03:00)

```cron
0 3 * * * cd /opt/ai-business-platform && \
  BACKUP_ENCRYPTION_PASSPHRASE="$SECRET" ./scripts/backup_postgres.sh \
  >> /var/log/backup_postgres.log 2>&1
```

O, si prefieres que docker lo gestione, añade el servicio `db` con volumes y
un job/sidecar que ejecute el script periódicamente.

### Prueba de recuperación (6.7)

```bash
# 1) Backup de prueba
./scripts/backup_postgres.sh && ls -lh backups/

# 2) Restaurar a una BD temporal y verificar
createdb -h localhost -p 5433 -U postgres restore_test
DATABASE_URL="postgresql://postgres:postgres@localhost:5433/restore_test" \
  ./scripts/restore_postgres.sh backups/postgres_*.dump --force
psql -h localhost -p 5433 -U postgres -d restore_test -c '\dt'
```

---

## 5. Observabilidad: Prometheus + Grafana (perfil `obs`)

Stack en `docker-compose.yml` (servicios con `profiles: ["obs"]`, se activan con `--profile obs`):

| Servicio            | Imagen                                      | Puerto host |
|---------------------|---------------------------------------------|-------------|
| `prometheus`        | `prom/prometheus:v2.53.0`                   | `9090`      |
| `grafana`           | `grafana/grafana:11.1.0`                    | `3002`      |
| `node_exporter`     | `prom/node-exporter:v1.8.2`                | `9100`      |
| `postgres_exporter` | `prometheuscommunity/postgres-exporter:v0.15.0` | `9187`  |

Config: `monitoring/prometheus.yml` (scrape targets `api:8000`,
`node_exporter:9100`, `postgres_exporter:9187`, todo en la red interna docker).

Grafana provisiona automáticamente el datasource Prometheus y el dashboard
`AI Business Platform` (`monitoring/grafana/dashboards/ai_business.json`).

```bash
docker compose --profile obs up -d
# Prometheus: http://localhost:9090  · Targets: /targets
# Grafana:    http://localhost:3002  · user: admin / $GRAFANA_ADMIN_PASSWORD
#             dashboard "AI Business Platform" ya provisionado
```

**Métricas disponibles** (exposición prometheus text/plain, sin auth — solo
red interna):

- `search_requests_total{provider}` — búsquedas por proveedor
- `opportunities_generated_total` — oportunidades creadas por jobs
- `search_order_duration_seconds` (histograma) — latencia de órdenes

Métricas vía `GET /metrics` (público, para scraping interno) y
`GET /api/v1/admin/metrics` (mismo payload, protegido por admin; ADR-003).

> En un despliegue **público**, no expongas `/metrics` al exterior sin
> restringir la red (firewall / proxy). Es de solo lectura, pero la exposición
> del puerto 8001 debe ir tras TLS + red privada.

---

## 6. Logging centralizado (opcional, perfil `logging`)

El proyecto ya emite **logging estructurado JSON** por request
(`request_id`, `correlation_id`, `duration_ms`) en `app/middleware/`. El stack
opcional `docker-compose.logging.yml` agrega Fluentd → Elasticsearch → Kibana:

```bash
docker compose --profile logging up -d
# Kibana: http://localhost:5601  (índices ai_business-YYYY.MM.DD)
```

Para que la API envíe sus logs a Fluentd, añade en `docker-compose.yml` del
servicio `api`:

```yaml
logging:
  driver: fluentd
  options:
    fluentd-address: localhost:24224
    tag: ai-business.{.Name}
```

Config de Fluentd en `logging/fluentd.conf` (forward → elasticsearch con
formato logstash).

---

## 7. CI/CD (GitHub Actions)

Workflows en `.github/workflows/`:

- **`ci.yml`** — en push a `main`/`master` y PRs: backend (Python 3.13, uv,
  ruff, `alembic upgrade head`, unit + coverage gate en módulos críticos,
  subconjunto de integración con Postgres service) y frontend (Node 22, npm,
  Vitest + coverage). Es el gate de calidad antes de cualquier release.
- **`deploy.yml`** — en push de tag `v*`: despliega directamente a
  **producción** (un único VPS, ambiente `production` de GitHub —
  simplificado respecto a un esquema staging+producción, que para un
  único usuario solo duplicaría el coste sin aportar nada). Necesita, en
  el environment `production` de GitHub (Settings → Environments):

  **Secrets:**
  | Secret | Para qué |
  |--------|----------|
  | `PRODUCTION_HOST` | IP o dominio del VPS (SSH) |
  | `PRODUCTION_USER` | Usuario SSH con Docker instalado |
  | `PRODUCTION_KEY` | Clave privada SSH (par con la pública ya autorizada en el VPS) |

  **Variables** (Settings → Variables, no secretas — son solo el dominio público):
  | Variable | Para qué |
  |----------|----------|
  | `DOMAIN` | Dominio real, ej. `midominio.com` (usado por `validate_deployment.sh` tras el despliegue) |

  El propio `.env.personal` en el servidor (no en GitHub) lleva `DOMAIN` y
  `ACME_EMAIL` para Caddy — ver §3-bis.

```bash
git tag v1.2.0
git push origin v1.2.0      # → CI primero; luego Deploy a producción (VPS único)
```

---

## 8. Validación post-despliegue

`scripts/validate_deployment.sh` verifica: liveness + health compuesto +
`/metrics` de la API, frontend, PostgreSQL y Redis (vía `docker compose exec`),
y avisa (sin fallar) si Prometheus/Grafana no están levantados.

```bash
./scripts/validate_deployment.sh http://localhost
./scripts/validate_deployment.sh https://app.example.com
```

Código de salida `0` = operativo, `1` = algún servicio crítico falla.

---

## 9. Checklist de release (producción)

- [ ] `ci.yml` verde (unit + integración + coverage + frontend).
- [ ] Health checks de los 4 servicios `healthy` en `docker compose ps`.
- [ ] `.env.production` con `ENVIRONMENT=production`, `AUTH_DISABLED=false`,
      CORS restringido, `JWT_SECRET_KEY` real (≥32 chars), Firebase configurado.
- [ ] Backup manual probado y restore probado (ver §4).
- [ ] `docker compose --profile obs up -d` → `/metrics` scrapeado por Prometheus
      (Jobs `up` = 1) y dashboard de Grafana con datos.
- [ ] `./scripts/validate_deployment.sh` → `OK: despliegue operativo`.
- [ ] Tag `v*` pusheado → Deploy a staging y producción.