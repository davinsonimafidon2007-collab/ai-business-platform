#!/usr/bin/env bash
#
# restore_postgres.sh — Restaura un backup lógico (pg_restore, formato custom).
#
# DEVOPS-001 (Task P3-002): script mínimo de restore documentado.
#
# Uso:
#   ./scripts/restore_postgres.sh <archivo.dump>          # pide confirmación
#   ./scripts/restore_postgres.sh <archivo.dump> --force  # sin confirmar
#
# Entorno:
#   - ARCHIVO: ruta al dump (1er argumento posicional).
#   - DATABASE_URL (normalizada automáticamente) o variables PG* estándar.
#
# ADVERTENCIA: restaura DESTRUYENDO los datos existentes de la base de destino
# (usa --clean --if-exists). Ten un backup reciente antes de ejecutar.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <archivo.dump> [--force]" >&2
  exit 2
fi

DUMP="$1"
FORCE="${2:-}"

if [[ ! -f "$DUMP" ]]; then
  echo "ERROR: no existe el archivo: $DUMP" >&2
  exit 1
fi

if [[ "$FORCE" != "--force" ]]; then
  echo "Este comando DESTRUIRÁ los datos actuales de la base de destino."
  read -r -p "¿Continuar? [y/N] " confirm
  if [[ "${confirm,,}" != "y" && "${confirm,,}" != "yes" ]]; then
    echo "Cancelado."
    exit 0
  fi
fi

# Normalizar DATABASE_URL async -> postgres:// (igual que backup_postgres.sh).
_normalize_url() {
  local url="$1"
  url="${url//postgresql+asyncpg:\/\//postgres://}"
  url="${url//postgresql+psycopg:\/\//postgres://}"
  echo "$url"
}

if [[ -n "${DATABASE_URL:-}" ]]; then
  PGURL="$( _normalize_url "$DATABASE_URL" )"
  echo "==> Restaurando $DUMP a $PGURL"
  pg_restore --exit-on-error --clean --if-exists -d "$PGURL" "$DUMP"
else
  echo "==> Restaurando $DUMP (variables PG* estándar)"
  pg_restore --exit-on-error --clean --if-exists -d "$DUMP"
fi

echo "OK: restauración completada."
