#!/usr/bin/env bash
#
# backup_postgres.sh — Backup lógico de Postgres en formato custom (pg_dump -Fc).
#
# TASK-014 (FASE 7): si BACKUP_ENCRYPTION_PASSPHRASE está definida, el dump se
# encripta con AES256 (gpg --symmetric) y el archivo `.dump` plano se elimina.
# Sin passphrase se genera un dump plano (modo dev) con un warning.
#
# DEVOPS-001 (Task P3-002): script de backup documentado para operabilidad.
#
# Uso:
#   BACKUP_ENCRYPTION_PASSPHRASE="supersecreta" ./scripts/backup_postgres.sh
#   BACKUP_RETENTION=14 BACKUP_DIR=/var/backups ./scripts/backup_postgres.sh
#
# Entorno:
#   - DATABASE_URL (p.ej. postgresql+asyncpg://user:pass@host:5432/db)
#     o variables PG* estándar (PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE).
#   - BACKUP_DIR                    (default: ./backups)
#   - BACKUP_RETENTION              (default: 7) — nº de dumps a conservar.
#   - BACKUP_ENCRYPTION_PASSPHRASE  (opcional) — passphrase AES256; vacío = sin encriptar.
#
# Ejemplo de cron (3:00 AM diario):
#   0 3 * * * cd /app && BACKUP_ENCRYPTION_PASSPHRASE="$SECRET" ./scripts/backup_postgres.sh \
#     >> /var/log/backup_postgres.log 2>&1
#
# Nota: NO se guardan dumps con datos reales en el repo; este script escribe
# fuera de git (ver .gitignore → backups/).

set -euo pipefail

# ---- Configuración con defaults -------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION="${BACKUP_RETENTION:-7}"
BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

# Normalizar DATABASE_URL: el proyecto usa SQLAlchemy async
# (postgresql+asyncpg://...), que pg_dump no entiende. Convertimos el driver
# a postgres:// para que pg_dump/pg_restore funcionen igual.
_normalize_url() {
  local url="$1"
  # postgresql+asyncpg:// -> postgres://
  url="${url//postgresql+asyncpg:\/\//postgres://}"
  # postgresql+psycopg:// -> postgres://
  url="${url//postgresql+psycopg:\/\//postgres://}"
  echo "$url"
}

mkdir -p "$BACKUP_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
PLAIN_FILE="$BACKUP_DIR/postgres_${TS}.dump"
ENC_FILE="$BACKUP_DIR/postgres_${TS}.dump.gpg"

echo "==> Backup Postgres (custom format)"

if [[ -n "${DATABASE_URL:-}" ]]; then
  PGURL="$( _normalize_url "$DATABASE_URL" )"
  pg_dump -Fc -f "$PLAIN_FILE" "$PGURL"
else
  pg_dump -Fc -f "$PLAIN_FILE"
fi

# Comprobar que el dump no está vacío
if [[ ! -s "$PLAIN_FILE" ]]; then
  echo "ERROR: dump vacío o no generado: $PLAIN_FILE" >&2
  rm -f "$PLAIN_FILE"
  exit 1
fi

# ---- Encriptación (TASK-014) ----------------------------------------------
if [[ -n "$BACKUP_ENCRYPTION_PASSPHRASE" ]]; then
  gpg --symmetric --cipher-algo AES256 --compress-algo 1 \
      --passphrase "$BACKUP_ENCRYPTION_PASSPHRASE" --batch --yes \
      --output "$ENC_FILE" "$PLAIN_FILE"
  rm -f "$PLAIN_FILE"
  echo "OK (encriptado AES256): $ENC_FILE ($(du -h "$ENC_FILE" | cut -f1))"
else
  echo "WARN: BACKUP_ENCRYPTION_PASSPHRASE vacía; dump SIN encriptar (solo dev)." >&2
  echo "OK: $PLAIN_FILE ($(du -h "$PLAIN_FILE" | cut -f1))"
fi

# ---- Retención: conservar los últimos N -----------------------------------
# Ordenamos por nombre (YYYYMMDD_HHMMSS) y borramos los más antiguos sobrantes.
ls -1 "$BACKUP_DIR"/postgres_*.dump "$BACKUP_DIR"/postgres_*.dump.gpg 2>/dev/null \
  | sort \
  | head -n -"$RETENTION" \
  | while read -r old; do
      echo "    Purgando backup antiguo: $old"
      rm -f "$old"
    done

echo "==> Retención: manteniendo los últimos $RETENTION backups en $BACKUP_DIR"