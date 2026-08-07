#!/usr/bin/env bash
#
# backup_postgres.sh — Backup lógico de Postgres en formato custom (pg_dump -Fc).
#
# DEVOPS-001 (Task P3-002): script de backup documentado para operabilidad
# básica de producción temprana.
#
# Uso:
#   ./scripts/backup_postgres.sh
#   BACKUP_RETENTION=14 BACKUP_DIR=/var/backups ./scripts/backup_postgres.sh
#
# Entorno:
#   - DATABASE_URL (p.ej. postgresql+asyncpg://user:pass@host:5432/db)
#     o variables PG* estándar (PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE).
#   - BACKUP_DIR      (default: ./backups)
#   - BACKUP_RETENTION (default: 7) — nº de dumps a conservar.
#
# Ejemplo de cron (3:00 AM diario):
#   0 3 * * * cd /app && ./scripts/backup_postgres.sh >> /var/log/backup_postgres.log 2>&1
#
# Nota: NO se guardan dumps con datos reales en el repo; este script escribe
# fuera de git (ver .gitignore → backups/).

set -euo pipefail

# ---- Configuración con defaults -------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION="${BACKUP_RETENTION:-7}"

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
OUT_FILE="$BACKUP_DIR/postgres_${TS}.dump"

echo "==> Backup Postgres (custom format) a: $OUT_FILE"

if [[ -n "${DATABASE_URL:-}" ]]; then
  PGURL="$( _normalize_url "$DATABASE_URL" )"
  echo "    Usando DATABASE_URL (normalizada)."
  pg_dump -Fc -f "$OUT_FILE" "$PGURL"
else
  echo "    Sin DATABASE_URL; usando variables PG* estándar."
  pg_dump -Fc -f "$OUT_FILE"
fi

# Comprobar que el dump no está vacío
if [[ ! -s "$OUT_FILE" ]]; then
  echo "ERROR: dump vacío o no generado: $OUT_FILE" >&2
  rm -f "$OUT_FILE"
  exit 1
fi

echo "OK: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"

# ---- Retención: conservar los últimos N -----------------------------------
# Ordenamos por nombre (YYYYMMDD_HHMMSS) y borramos los más antiguos sobrantes.
ls -1 "$BACKUP_DIR"/postgres_*.dump 2>/dev/null \
  | sort \
  | head -n -"$RETENTION" \
  | while read -r old; do
      echo "    Purgando backup antiguo: $old"
      rm -f "$old"
    done

echo "==> Retención: manteniendo los últimos $RETENTION backups en $BACKUP_DIR"
