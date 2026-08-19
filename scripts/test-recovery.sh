#!/bin/bash
# scripts/test-recovery.sh
# Pruebas de recuperación ante fallos

set -euo pipefail

echo "🧪 Iniciando pruebas de recuperación ante fallos..."
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Función para esperar recuperación
wait_for_recovery() {
    local service_name=$1
    local url=$2
    local max_attempts=${3:-30}

    echo -n "Esperando recuperación de $service_name... "

    for i in $(seq 1 $max_attempts); do
        status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [ "$status_code" = "200" ]; then
            echo -e "${GREEN}✅ Recuperado${NC} (${i} intentos)"
            return 0
        fi

        sleep 2
    done

    echo -e "${RED}❌ No recuperó después de $max_attempts intentos${NC}"
    ERRORS=$((ERRORS + 1))
    return 1
}

# Test 1: Reinicio de PostgreSQL
echo "🗄️  Test 1: Reinicio de PostgreSQL"
echo "Deteniendo PostgreSQL..."
docker compose stop db

sleep 5

echo "Verificando que API reporta unhealthy..."
status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/health/ready" 2>/dev/null || echo "000")
if [ "$status" = "503" ]; then
    echo -e "API reporta unhealthy correctamente... ${GREEN}✅${NC}"
else
    echo -e "API no reporta unhealthy correctamente... ${YELLOW}⚠️${NC} (HTTP $status)"
fi

echo "Reiniciando PostgreSQL..."
docker compose start db

wait_for_recovery "PostgreSQL" "http://localhost:8001/health/ready" 30

echo ""

# Test 2: Reinicio de Redis
echo "🔴 Test 2: Reinicio de Redis"
echo "Deteniendo Redis..."
docker compose stop redis

sleep 5

echo "Reiniciando Redis..."
docker compose start redis

wait_for_recovery "Redis" "http://localhost:8001/health/ready" 20

echo ""

# Test 3: Reinicio de API
echo "🔌 Test 3: Reinicio de API"
echo "Deteniendo API..."
docker compose stop api

sleep 5

echo "Reiniciando API..."
docker compose start api

wait_for_recovery "API" "http://localhost:8001/health/ready" 30

echo ""

# Resumen
echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ TODAS LAS PRUEBAS DE RECUPERACIÓN PASARON${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS PRUEBAS FALLARON${NC}"
    exit 1
fi
