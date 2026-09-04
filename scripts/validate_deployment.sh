#!/usr/bin/env bash
#
# validate_deployment.sh — Validación post-despliegue (Bloque 6 / DEVOPS).
#
# Verifica que todos los servicios están operativos después de un despliegue:
#   - Backend API        (puerto host ${API_PORT:-8001}, /health/live y /health)
#   - Frontend           (puerto host ${FRONTEND_PORT:-3001})
#   - PostgreSQL         (docker exec pg_isready en el contenedor db)
#   - Redis              (docker exec redis-cli ping en el contenedor redis)
#   - Prometheus/Grafana (perfil obs; aviso si no están, no falla)
#
# Uso:
#   ./scripts/validate_deployment.sh                 # http://localhost (puertos host)
#   ./scripts/validate_deployment.sh http://localhost https://app.ejemplo.com
#
# Modo dominio (despliegue personal con Caddy — sin puertos, HTTPS 443):
# API y frontend viven en subdominios distintos, sin puerto explícito.
# Pasa el segundo argumento (frontend) y vacía API_PORT/FRONTEND_PORT:
#   API_PORT= FRONTEND_PORT= ./scripts/validate_deployment.sh \
#     https://api.midominio.com https://midominio.com
#
# Códigos de salida: 0 = todo OK (obs opcional), 1 = algún servicio crítico falla.

set -uo pipefail

BASE_URL="${1:-http://localhost}"
FRONTEND_URL="${2:-$BASE_URL}"
API_PORT="${API_PORT-8001}"
FRONTEND_PORT="${FRONTEND_PORT-3001}"

# Puerto vacío (API_PORT= / FRONTEND_PORT=) => no se añade ":puerto" a la URL
# (modo dominio: Caddy sirve por subdominio en 443, sin puerto explícito).
api_url() { [[ -n "$API_PORT" ]] && echo "${BASE_URL}:${API_PORT}$1" || echo "${BASE_URL}$1"; }
frontend_url() { [[ -n "$FRONTEND_PORT" ]] && echo "${FRONTEND_URL}:${FRONTEND_PORT}$1" || echo "${FRONTEND_URL}$1"; }

fail=0

echo "==> Validando despliegue — api=$(api_url '') frontend=$(frontend_url '')"

check_http() {
  local name="$1" url="$2"
  if curl -fsS -o /dev/null --max-time 10 "$url"; then
    echo "  [OK] ${name} → ${url}"
  else
    echo "  [FAIL] ${name} → ${url}"
    fail=1
  fi
}

check_docker() {
  local name="$1" service="$2"; shift 2
  if "${DOCKER_BIN}" compose exec -T "$service" "$@" >/dev/null 2>&1; then
    echo "  [OK] ${name} (service ${service})"
  else
    echo "  [FAIL] ${name} (service ${service})"
    fail=1
  fi
}

# --- Backend ---
check_http "Backend liveness" "$(api_url /health/live)"
check_http "Backend health (compuesto)" "$(api_url /health)"
check_http "Backend metrics (Prometheus)" "$(api_url /metrics)"

# --- Frontend ---
check_http "Frontend" "$(frontend_url '')"

# --- Dependencias internas (docker compose) ---
# En Linux/CI `docker` funciona; en Windows (git-bash/WSL) el wrapper `docker`
# puede apuntar a un distro WSL sin daemon, mientras `docker.exe` (Docker
# Desktop) sí responde. Elegimos el primero que responde `docker version`.
DOCKER_BIN=""
for candidate in docker docker.exe; do
  if command -v "$candidate" >/dev/null 2>&1 \
     && "$candidate" version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    DOCKER_BIN="$candidate"
    break
  fi
done

if [[ -n "$DOCKER_BIN" ]]; then
  check_docker "PostgreSQL" "db" pg_isready -U postgres -d ai_business_platform
  check_docker "Redis" "redis" redis-cli ping
else
  echo "  [WARN] docker no disponible; no se validan contenedores."
fi

# --- Observabilidad (opcional, no falla si no está levantada) ---
check_optional_http() {
  local name="$1" url="$2"
  if curl -fsS -o /dev/null --max-time 5 "$url" 2>/dev/null; then
    echo "  [OK] ${name} → ${url}"
  else
    echo "  [WARN] ${name} → no disponible (perfil obs no levantado)"
  fi
}

check_optional_http "Prometheus" "${BASE_URL}:9090"
check_optional_http "Grafana" "${BASE_URL}:3002"

echo "==> Validación completada."

if [[ "$fail" -eq 1 ]]; then
  echo "!! Algunos servicios críticos fallaron."
  exit 1
fi
echo "OK: despliegue operativo."
exit 0
