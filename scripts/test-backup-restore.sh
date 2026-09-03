#!/bin/bash
# scripts/test-backup-restore.sh
# Prueba automatizada del flujo completo de backup y restore

set -euo pipefail

echo "🧪 Iniciando prueba de backup/restore..."
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DB_NAME="${POSTGRES_DB:-ai_business_platform}"
DB_USER="${POSTGRES_USER:-postgres}"
DOCKER_CONTAINER="${DOCKER_CONTAINER:-ai-business-platform-db-1}"
TEST_TABLE="backup_test_$(date +%s)"

ERRORS=0

# Función para verificar tabla
check_table_exists() {
    local table_name=$1
    local exists=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table_name');" | xargs)

    if [ "$exists" = "t" ]; then
        return 0
    else
        return 1
    fi
}

# 1. Crear datos de prueba
echo "📝 Paso 1: Creando datos de prueba..."
docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    CREATE TABLE IF NOT EXISTS $TEST_TABLE (
        id SERIAL PRIMARY KEY,
        test_data VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW()
    );
    INSERT INTO $TEST_TABLE (test_data) VALUES
        ('test_record_1'),
        ('test_record_2'),
        ('test_record_3');
"

if check_table_exists "$TEST_TABLE"; then
    echo -e "${GREEN}✅ Tabla de prueba creada${NC}"
else
    echo -e "${RED}❌ ERROR: No se pudo crear la tabla de prueba${NC}"
    exit 1
fi

# Contar registros antes del backup
RECORDS_BEFORE=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM $TEST_TABLE;" | xargs)
echo "📊 Registros antes del backup: $RECORDS_BEFORE"

# 2. Ejecutar backup
echo ""
echo "💾 Paso 2: Ejecutando backup..."
./scripts/backup-postgres.sh

BACKUP_FILE=$(ls -t /backups/postgres/backup_*.sql.gz ./backups/postgres_*.dump 2>/dev/null | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ ERROR: No se encontró el archivo de backup${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ Backup creado: $BACKUP_FILE${NC}"
fi

# 3. Simular corrupción (eliminar tabla)
echo ""
echo "💥 Paso 3: Simulando corrupción (eliminando tabla)..."
docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $TEST_TABLE;"

if ! check_table_exists "$TEST_TABLE"; then
    echo -e "${GREEN}✅ Tabla eliminada correctamente${NC}"
else
    echo -e "${RED}❌ ERROR: La tabla aún existe${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 4. Restaurar backup
echo ""
echo "🔄 Paso 4: Restaurando backup..."
echo "s" | ./scripts/restore-postgres.sh "$BACKUP_FILE" --force

# 5. Verificar restauración
echo ""
echo "🔍 Paso 5: Verificando restauración..."

if check_table_exists "$TEST_TABLE"; then
    echo -e "${GREEN}✅ Tabla restaurada${NC}"

    RECORDS_AFTER=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM $TEST_TABLE;" | xargs)
    echo "📊 Registros después del restore: $RECORDS_AFTER"

    if [ "$RECORDS_BEFORE" = "$RECORDS_AFTER" ]; then
        echo -e "${GREEN}✅ Todos los registros fueron restaurados${NC}"
    else
        echo -e "${RED}❌ ERROR: Número de registros no coincide${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}❌ ERROR: La tabla no fue restaurada${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 6. Limpieza
echo ""
echo "🧹 Paso 6: Limpiando datos de prueba..."
docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE IF EXISTS $TEST_TABLE;"

# Resumen
echo ""
echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ PRUEBA DE BACKUP/RESTORE COMPLETADA EXITOSAMENTE${NC}"
    echo ""
    echo "El sistema de backup y restore funciona correctamente."
    exit 0
else
    echo -e "${RED}❌ PRUEBA FALLÓ CON $ERRORS ERRORES${NC}"
    exit 1
fi
