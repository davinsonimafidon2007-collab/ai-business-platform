#!/bin/bash
# scripts/generate-release-keystore.sh
# Genera un keystore de producción para firmar la app Android

set -euo pipefail

KEYSTORE_PATH="${1:-android/app/release-key.jks}"
KEY_ALIAS="${2:-prod-release}"
VALIDITY_DAYS="${3:-10000}"

echo "🔐 Generando keystore de producción..."
echo "📁 Ruta: $KEYSTORE_PATH"
echo "🏷️  Alias: $KEY_ALIAS"
echo "📅 Validez: $VALIDITY_DAYS días"
echo ""

# Verificar que keytool está disponible
if ! command -v keytool &> /dev/null; then
    echo "❌ ERROR: keytool no está instalado. Instala JDK 17 o superior."
    exit 1
fi

# Crear directorio si no existe
mkdir -p "$(dirname "$KEYSTORE_PATH")"

# Generar keystore
echo "⚠️  Se te pedirá crear una contraseña para el keystore."
echo "⚠️  GUARDA ESTA CONTRASEÑA EN UN GESTOR DE CONTRASEÑAS SEGuro."
echo "⚠️  Sin ella, no podrás actualizar la app en Google Play."
echo ""

keytool -genkeypair \
    -v \
    -keystore "$KEYSTORE_PATH" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity "$VALIDITY_DAYS" \
    -storepass "${KEYSTORE_PASSWORD:-changeit}" \
    -keypass "${KEY_PASSWORD:-changeit}" \
    -dname "CN=AI Business Platform, OU=Mobile, O=AI Business, L=Madrid, ST=Madrid, C=ES"

echo ""
echo "✅ Keystore generado exitosamente"
echo ""
echo "📋 Información del keystore:"
keytool -list -v -keystore "$KEYSTORE_PATH" -storepass "${KEYSTORE_PASSWORD:-changeit}" | grep -E "Alias|Owner|Valid"

echo ""
echo "⚠️  PRÓXIMOS PASOS:"
echo "1. Guarda la contraseña del keystore en un gestor seguro (1Password, Bitwarden, etc.)"
echo "2. Añade estas variables a tu CI/CD (GitHub Secrets):"
echo "   - ANDROID_KEYSTORE_BASE64: $(base64 < "$KEYSTORE_PATH" | tr -d '\n')"
echo "   - ANDROID_KEYSTORE_PASSWORD: <tu_contraseña>"
echo "   - ANDROID_KEY_ALIAS: $KEY_ALIAS"
echo "   - ANDROID_KEY_PASSWORD: <tu_contraseña>"
echo "3. NO subas este archivo .jks al repositorio (ya está en .gitignore)"
