#!/bin/bash
# scripts/backup-postgres.sh
# Backup automatizado de PostgreSQL con retención y verificación

set -euo pipefail

# Configuración
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_NAME="${POSTGRES_DB:-ai_business_platform}"
DB_USER="${POSTGRES_USER:-postgres}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"

# Crear directorio si no existe
mkdir -p "$BACKUP_DIR"

echo "🗄️  Iniciando backup de PostgreSQL: $DB_NAME"
echo "📁 Destino: $BACKUP_FILE"

# Ejecutar backup (desde el contenedor o local)
if [ -n "${DOCKER_CONTAINER:-}" ]; then
    # Backup desde contenedor Docker
    docker exec "$DOCKER_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom | gzip > "$BACKUP_FILE"
else
    # Backup local o desde variable DATABASE_URL
    if [ -n "${DATABASE_URL:-}" ]; then
        pg_dump "$DATABASE_URL" --format=custom | gzip > "$BACKUP_FILE"
    else
        pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom | gzip > "$BACKUP_FILE"
    fi
fi

# Verificar integridad del backup
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERROR: El archivo de backup no se creó"
    exit 1
fi

BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
if [ "$BACKUP_SIZE" -lt 1000 ]; then
    echo "❌ ERROR: El backup está vacío o corrupto (tamaño: $BACKUP_SIZE bytes)"
    rm "$BACKUP_FILE"
    exit 1
fi

# Verificar que el gzip es válido
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "❌ ERROR: El archivo gzip está corrupto"
    exit 1
fi

echo "✅ Backup completado exitosamente"
echo "📊 Tamaño: $(du -h "$BACKUP_FILE" | cut -f1)"

# Eliminar backups antiguos
echo "🧹 Limpiando backups antiguos (retención: $RETENTION_DAYS días)"
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -delete

# Listar backups actuales
echo "📋 Backups disponibles:"
ls -lh "$BACKUP_DIR"/backup_*.sql.gz | tail -5

echo "✅ Backup finalizado correctamente"
