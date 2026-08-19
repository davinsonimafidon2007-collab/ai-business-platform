#!/bin/bash
# scripts/restore-postgres.sh
# Restauración de backup de PostgreSQL con verificación

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Uso: $0 <archivo_backup.sql.gz>"
    echo ""
    echo "Ejemplos:"
    echo "  $0 /backups/postgres/backup_ai_business_platform_20260819_120000.sql.gz"
    echo "  $0 latest  # Restaura el backup más reciente"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${POSTGRES_DB:-ai_business_platform}"
DB_USER="${POSTGRES_USER:-postgres}"

# Si se especifica "latest", buscar el backup más reciente
if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | head -1)

    if [ -z "$BACKUP_FILE" ]; then
        echo "❌ ERROR: No se encontraron backups en $BACKUP_DIR"
        exit 1
    fi

    echo "📦 Usando backup más reciente: $BACKUP_FILE"
fi

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERROR: El archivo de backup no existe: $BACKUP_FILE"
    exit 1
fi

# Verificar integridad del gzip
echo "🔍 Verificando integridad del backup..."
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "❌ ERROR: El archivo gzip está corrupto"
    exit 1
fi

echo "⚠️  ADVERTENCIA: Esto restaurará la base de datos '$DB_NAME'"
echo "📦 Archivo: $BACKUP_FILE"
echo "📊 Tamaño: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
read -p "¿Continuar? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Restauración cancelada"
    exit 1
fi

# Crear backup de seguridad antes de restaurar
echo "🛡️  Creando backup de seguridad antes de restaurar..."
PRE_RESTORE_BACKUP="/tmp/pre_restore_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

if [ -n "${DOCKER_CONTAINER:-}" ]; then
    docker exec "$DOCKER_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom | gzip > "$PRE_RESTORE_BACKUP"
else
    pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom | gzip > "$PRE_RESTORE_BACKUP"
fi

echo "✅ Backup de seguridad creado: $PRE_RESTORE_BACKUP"

# Restaurar backup
echo "🔄 Restaurando base de datos..."
if [ -n "${DOCKER_CONTAINER:-}" ]; then
    gunzip -c "$BACKUP_FILE" | docker exec -i "$DOCKER_CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner --no-privileges
else
    gunzip -c "$BACKUP_FILE" | pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner --no-privileges
fi

# Verificar que la restauración fue exitosa
echo "🔍 Verificando restauración..."
TABLE_COUNT=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)

if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "❌ ERROR: La restauración falló (0 tablas encontradas)"
    echo "💡 Puedes restaurar el backup de seguridad: $PRE_RESTORE_BACKUP"
    exit 1
fi

echo "✅ Restauración completada exitosamente"
echo "📊 Tablas restauradas: $TABLE_COUNT"
echo "💾 Backup de seguridad disponible en: $PRE_RESTORE_BACKUP"
