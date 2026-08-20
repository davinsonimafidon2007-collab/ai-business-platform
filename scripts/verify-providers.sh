#!/bin/bash
# scripts/verify-providers.sh
# Verifica la conectividad con proveedores externos

set -euo pipefail

echo "🔌 Verificando conectividad con proveedores..."
echo ""

ERRORS=0

# Función para verificar proveedor
check_provider() {
    local provider_name=$1
    local url=$2

    echo -n "Verificando $provider_name... "

    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [ "$status_code" = "200" ]; then
        echo "✅ OK (HTTP $status_code)"
        return 0
    elif [ "$status_code" = "403" ]; then
        echo "⚠️  WARNING: Acceso bloqueado (HTTP 403 - posiblemente anti-bot)"
        return 0
    elif [ "$status_code" = "404" ]; then
        echo "⚠️  WARNING: Recurso no encontrado (HTTP 404)"
        return 0
    else
        echo "❌ FAIL (HTTP $status_code)"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Verificar AutoScout24
check_provider "AutoScout24" "https://www.autoscout24.es"

# Verificar mobile.de
check_provider "mobile.de" "https://www.mobile.de"

# Verificar API propia
echo -n "Verificando API propia... "
api_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/health/ready" 2>/dev/null || echo "000")

if [ "$api_status" = "200" ]; then
    echo "✅ OK (HTTP $api_status)"
else
    echo "⚠️  API local no detectada en http://localhost:8001/health/ready (HTTP $api_status)"
    # Do not treat non-running local API in dev environment as script failure if external connectivity works
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ Todos los proveedores son accesibles"
    exit 0
else
    echo "❌ $ERRORS proveedores no son accesibles"
    exit 1
fi
