#!/bin/bash
# scripts/verify-apk-signature.sh
# Verifica que un APK está firmado correctamente

set -euo pipefail

APK_PATH="${1:-ai-business-platform-release.apk}"

if [ ! -f "$APK_PATH" ]; then
    echo "❌ ERROR: No se encontró el APK en $APK_PATH"
    exit 1
fi

echo "🔍 Verificando firma del APK..."
echo "📁 Archivo: $APK_PATH"
echo ""

# Verificar con apksigner (Android SDK)
if command -v apksigner &> /dev/null; then
    echo "✅ APK firmado correctamente:"
    apksigner verify --verbose "$APK_PATH"

    echo ""
    echo "📋 Información de la firma:"
    apksigner verify --print-certs "$APK_PATH"
else
    echo "⚠️  apksigner no está disponible. Usando jarsigner..."

    if command -v jarsigner &> /dev/null; then
        jarsigner -verify -verbose -certs "$APK_PATH"

        if [ $? -eq 0 ]; then
            echo "✅ APK firmado correctamente"
        else
            echo "❌ ERROR: El APK no está firmado o la firma es inválida"
            exit 1
        fi
    else
        echo "❌ ERROR: Ni apksigner ni jarsigner están disponibles"
        echo "💡 Instala Android SDK Build Tools o JDK"
        exit 1
    fi
fi

echo ""
echo "✅ Verificación completada"
