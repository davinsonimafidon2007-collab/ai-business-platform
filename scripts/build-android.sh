#!/bin/bash
# scripts/build-android.sh
# Build de la aplicación Android (debug o release)

set -euo pipefail

BUILD_TYPE="${1:-debug}"  # debug o release
FRONTEND_DIR="frontend"

echo "🔨 Iniciando build de Android ($BUILD_TYPE)..."

cd "$FRONTEND_DIR"

# 1. Build del frontend web
echo "📦 Compilando frontend web..."
npm run build

# 2. Sincronizar con Capacitor
echo "🔄 Sincronizando con Capacitor..."
npx cap sync android

# 3. Build de Android
cd android

if [ "$BUILD_TYPE" = "release" ]; then
    echo "🔐 Generando APK de release firmado..."

    # Verificar que existe keystore.properties
    if [ ! -f "keystore.properties" ]; then
        echo "❌ ERROR: No se encontró keystore.properties"
        echo "💡 Copia keystore.properties.example a keystore.properties y rellena los valores"
        exit 1
    fi

    ./gradlew assembleRelease

    APK_PATH="app/build/outputs/apk/release/app-release.apk"

    if [ -f "$APK_PATH" ]; then
        echo "✅ APK de release generado exitosamente"
        echo "📁 Ruta: $APK_PATH"
        echo "📊 Tamaño: $(du -h "$APK_PATH" | cut -f1)"

        # Copiar a raíz para fácil acceso
        cp "$APK_PATH" "../../ai-business-platform-release.apk"
        echo "📋 Copiado a: ai-business-platform-release.apk"
    else
        echo "❌ ERROR: No se generó el APK"
        exit 1
    fi
else
    echo "🔧 Generando APK de debug..."
    ./gradlew assembleDebug

    APK_PATH="app/build/outputs/apk/debug/app-debug.apk"

    if [ -f "$APK_PATH" ]; then
        echo "✅ APK de debug generado exitosamente"
        echo "📁 Ruta: $APK_PATH"
        cp "$APK_PATH" "../../ai-business-platform-debug.apk"
    else
        echo "❌ ERROR: No se generó el APK"
        exit 1
    fi
fi

echo ""
echo "✅ Build completado"
