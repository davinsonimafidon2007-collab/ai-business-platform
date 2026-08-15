#!/usr/bin/env bash
#
# restore_postgres.sh — Restaura un backup lógico (pg_restore, formato custom).
#
# TASK-014 (FASE 7): si el archivo termina en `.gpg` se desencripta con
# BACKUP_ENCRYPTION_PASSPHRASE antes de restaurar. El `.dump` plano temporal
# se elimina al terminar.
#
# DEVOPS-001 (Task P3-002): script mínimo de restore documentado.
#
# Uso:
#   ./scripts/restore_postgres.sh <archivo.dump>             # pide confirmación
#   ./scripts/restore_postgres.sh <archivo.dump> --force     # sin confirmar
#   BACKUP_ENCRYPTION_PASSPHRASE="sec" ./scripts/restore_postgres.sh backups/postgres_x.dump.gpg
#
# Entorno:
#   - ARCHIVO: ruta al dump/archivo encriptado (1er argumento posicional).
#   - DATABASE_URL (normalizada automáticamente) o variables PG* estándar.
#   - BACKUP_ENCRYPTION_PASSPHRASE: obligatoria si el backup es `.gpg`.
#
# ADVERTENCIA: restaura DESTRUYENDO los datos existentes de la base de destino
# (usa --clean --if-exists). Ten un backup reciente antes de ejecutar.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <archivo.dump|archivo.dump.gpg> [--force]" >&2
  exit 2
fi

BACKUP_FILE="$1"
FORCE="${2:-}"
BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: no existe el archivo: $BACKUP_FILE" >&2
  exit 1
fi

# ---- Desencriptación (TASK-014) -------------------------------------------
CLEANUP_PLAIN=0
RESTORE_FILE="$BACKUP_FILE"

if [[ "$BACKUP_FILE" == *.gpg ]]; then
  if [[ -z "$BACKUP_ENCRYPTION_PASSPHRASE" ]]; then
    echo "ERROR: backup encriptado (.gpg) pero BACKUP_ENCRYPTION_PASSPHRASE vacía." >&2
    exit 1
  fi
  PLAIN_FILE="${BACKUP_FILE%.gpg}"
  echo "==> Desencriptando backup con gpg..."
  gpg --decrypt --passphrase "$BACKUP_ENCRYPTION_PASSPHRASE" --batch --yes \
      --output "$PLAIN_FILE" "$BACKUP_FILE"
  RESTORE_FILE="$PLAIN_FILE"
  CLEANUP_PLAIN=1
fi

if [[ "$FORCE" != "--force" ]]; then
  echo "Este comando DESTRUIRÁ los datos actuales de la base de destino."
  read -r -p "¿Continuar? [y/N] " confirm
  if [[ "${confirm,,}" != "y" && "${confirm,,}" != "yes" ]]; then
    echo "Cancelado."
    [[ "$CLEANUP_PLAIN" -eq 1 ]] && rm -f "$PLAIN_FILE"
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

echo "==> Restaurando desde: $RESTORE_FILE"

if [[ -n "${DATABASE_URL:-}" ]]; then
  PGURL="$( _normalize_url "$DATABASE_URL" )"
  pg_restore --exit-on-error --clean --if-exists -d "$PGURL" "$RESTORE_FILE"
else
  pg_restore --exit-on-error --clean --if-exists -d "$RESTORE_FILE"
fi

echo "OK: restauración completada."

[[ "$CLEANUP_PLAIN" -eq 1 ]] && rm -f "$PLAIN_FILE"