#!/bin/bash
# scripts/validate-production-env.sh
# Valida que las variables de entorno críticas estén configuradas para producción

set -euo pipefail

echo "🔍 Validando variables de entorno para producción..."

ERRORS=0

# Función para verificar variable requerida
check_required() {
    local var_name=$1
    local var_value=${!var_name:-}

    if [ -z "$var_value" ]; then
        echo "❌ ERROR: $var_name no está configurada"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ $var_name está configurada"
    fi
}

# Función para verificar longitud mínima
check_min_length() {
    local var_name=$1
    local min_length=$2
    local var_value=${!var_name:-}

    if [ ${#var_value} -lt $min_length ]; then
        echo "❌ ERROR: $var_name debe tener al menos $min_length caracteres (actual: ${#var_value})"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ $var_name tiene longitud adecuada (${#var_value} chars)"
    fi
}

# Variables críticas para producción
check_required "ENVIRONMENT"
check_required "JWT_SECRET_KEY"
check_required "DATABASE_URL"
check_required "REDIS_URL"

# Validaciones específicas
if [ "${ENVIRONMENT:-}" = "production" ]; then
    echo ""
    echo "🔒 Validaciones específicas de producción:"

    check_min_length "JWT_SECRET_KEY" 32

    # Verificar que AUTH_DISABLED no esté activo
    if [ "${AUTH_DISABLED:-false}" = "true" ]; then
        echo "❌ ERROR: AUTH_DISABLED no puede ser true en producción"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ AUTH_DISABLED está desactivado"
    fi

    # Verificar HTTPS redirect
    if [ "${HTTPS_REDIRECT:-true}" != "true" ]; then
        echo "⚠️  WARNING: HTTPS_REDIRECT debería estar activo en producción"
    else
        echo "✅ HTTPS_REDIRECT está activo"
    fi

    # Verificar CORS origins
    if [ -z "${CORS_ORIGINS:-}" ]; then
        echo "❌ ERROR: CORS_ORIGINS debe estar configurada en producción"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ CORS_ORIGINS está configurada"
    fi

    # Verificar Firebase (si es requerido)
    if [ "${FIREBASE_REQUIRED:-false}" = "true" ]; then
        check_required "FIREBASE_CREDENTIALS_JSON"
    fi
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ Todas las validaciones pasaron correctamente"
    exit 0
else
    echo "❌ Se encontraron $ERRORS errores"
    exit 1
fi
