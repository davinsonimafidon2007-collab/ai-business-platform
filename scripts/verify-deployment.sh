#!/bin/bash
# scripts/verify-deployment.sh
# Verifica que el despliegue completo funciona desde cero

set -euo pipefail

echo "🚀 Iniciando verificación de despliegue completo..."
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Función para verificar servicio
check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}

    echo -n "Verificando $service_name... "

    for i in {1..30}; do
        status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [ "$status_code" = "$expected_status" ]; then
            echo -e "${GREEN}✅ OK${NC} (HTTP $status_code)"
            return 0
        fi

        sleep 2
    done

    echo -e "${RED}❌ FAIL${NC} (HTTP $status_code, esperado $expected_status)"
    ERRORS=$((ERRORS + 1))
    return 1
}

# 1. Levantar servicios
echo "📦 Levantando servicios con Docker Compose..."
docker compose up -d

echo ""
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

# 2. Verificar health checks
echo ""
echo "🏥 Verificando health checks..."
check_service "API (liveness)" "http://localhost:8001/health/live"
check_service "API (readiness)" "http://localhost:8001/health/ready"
check_service "Frontend" "http://localhost:3001"

# 3. Verificar base de datos
echo ""
echo "🗄️  Verificando base de datos..."
if docker exec ai-business-platform-db-1 pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "PostgreSQL... ${GREEN}✅ OK${NC}"
else
    echo -e "PostgreSQL... ${RED}❌ FAIL${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 4. Verificar Redis
echo ""
echo "🔴 Verificando Redis..."
if docker exec ai-business-platform-redis-1 redis-cli ping | grep -q "PONG"; then
    echo -e "Redis... ${GREEN}✅ OK${NC}"
else
    echo -e "Redis... ${RED}❌ FAIL${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 5. Verificar migraciones
echo ""
echo "🔄 Verificando migraciones de base de datos..."
if docker exec ai-business-platform-api-1 alembic current | grep -q "head"; then
    echo -e "Migraciones... ${GREEN}✅ OK${NC} (en head)"
else
    echo -e "Migraciones... ${YELLOW}⚠️  WARNING${NC} (no está en head)"
fi

# 6. Verificar endpoints críticos
echo ""
echo "🔌 Verificando endpoints críticos..."
check_service "API Docs" "http://localhost:8001/docs"
check_service "API Metrics" "http://localhost:8001/metrics"

# 7. Resumen
echo ""
echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ DESPLIEGUE VERIFICADO CORRECTAMENTE${NC}"
    echo ""
    echo "Servicios disponibles:"
    echo "  - Frontend: http://localhost:3001"
    echo "  - API: http://localhost:8001"
    echo "  - API Docs: http://localhost:8001/docs"
    echo "  - Prometheus: http://localhost:9090 (perfil: monitoring)"
    echo "  - Grafana: http://localhost:3002 (perfil: monitoring)"
    exit 0
else
    echo -e "${RED}❌ SE ENCONTRARON $ERRORS ERRORES${NC}"
    echo ""
    echo "Revisa los logs con: docker compose logs -f"
    exit 1
fi
