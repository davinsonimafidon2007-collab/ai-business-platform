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

# El script NO es interactivo (usa -storepass/-keypass, keytool no pregunta
# nada) — sin esto, sin querer firmarías el release de producción con la
# contraseña por defecto "changeit", conocida públicamente.
if [ -z "${KEYSTORE_PASSWORD:-}" ] || [ -z "${KEY_PASSWORD:-}" ]; then
    echo "❌ ERROR: exporta KEYSTORE_PASSWORD y KEY_PASSWORD antes de ejecutar este script."
    echo "   Este script NO es interactivo: sin esas variables firmaría el"
    echo "   release con la contraseña por defecto de keytool (\"changeit\")."
    echo ""
    echo "   Ejemplo (usa la MISMA contraseña en ambas — ver nota PKCS12 abajo):"
    echo "   export KEYSTORE_PASSWORD='una contraseña larga y aleatoria'"
    echo "   export KEY_PASSWORD=\"\$KEYSTORE_PASSWORD\""
    echo "   $0 $KEYSTORE_PATH $KEY_ALIAS $VALIDITY_DAYS"
    exit 1
fi

if [ "$KEYSTORE_PASSWORD" != "$KEY_PASSWORD" ]; then
    echo "⚠️  AVISO: KEYSTORE_PASSWORD y KEY_PASSWORD son distintos."
    echo "⚠️  keytool moderno genera PKCS12 por defecto, que NO admite"
    echo "⚠️  contraseñas de almacén y de clave distintas — ignorará"
    echo "⚠️  KEY_PASSWORD en silencio y usará KEYSTORE_PASSWORD para todo."
    echo "⚠️  Usa el MISMO valor en ambas para evitar un mismatch más adelante."
    echo ""
fi

# Crear directorio si no existe
mkdir -p "$(dirname "$KEYSTORE_PATH")"

echo "⚠️  Vas a generar un keystore de PRODUCCIÓN. Sin la contraseña que"
echo "⚠️  acabas de exportar no podrás volver a actualizar la app en"
echo "⚠️  Google Play — guárdala ya en un gestor de contraseñas seguro."
echo ""

keytool -genkeypair \
    -v \
    -keystore "$KEYSTORE_PATH" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity "$VALIDITY_DAYS" \
    -storepass "$KEYSTORE_PASSWORD" \
    -keypass "$KEY_PASSWORD" \
    -dname "CN=AI Business Platform, OU=Mobile, O=AI Business, L=Madrid, ST=Madrid, C=ES"

echo ""
echo "✅ Keystore generado exitosamente"
echo ""
echo "📋 Información del keystore:"
keytool -list -v -keystore "$KEYSTORE_PATH" -storepass "$KEYSTORE_PASSWORD" | grep -E "Alias|Owner|Valid"

# El base64 es el material de firma real — no lo imprimimos por stdout
# (queda en el historial de la shell / logs de terminal). Se escribe a un
# archivo local ya cubierto por .gitignore (*.jks, *.keystore).
BASE64_OUT="$(dirname "$KEYSTORE_PATH")/$(basename "$KEYSTORE_PATH" .jks).base64.txt"
base64 < "$KEYSTORE_PATH" | tr -d '\n' > "$BASE64_OUT"

echo ""
echo "⚠️  PRÓXIMOS PASOS:"
echo "1. Guarda KEYSTORE_PASSWORD y KEY_PASSWORD en un gestor seguro (1Password, Bitwarden, etc.)."
echo "2. Añade estos 4 GitHub Secrets (Settings → Secrets and variables → Actions)."
echo "   Los nombres deben ser EXACTOS — son los que lee .github/workflows/mobile-release-cicd.yml:"
echo "   - KEYSTORE_BASE64: contenido de $BASE64_OUT"
echo "   - KEYSTORE_PASSWORD: el valor de \$KEYSTORE_PASSWORD que exportaste"
echo "   - KEY_ALIAS: $KEY_ALIAS"
echo "   - KEY_PASSWORD: el valor de \$KEY_PASSWORD que exportaste"
echo "3. Borra $BASE64_OUT en cuanto lo hayas pegado en GitHub Secrets."
echo "4. NO subas $KEYSTORE_PATH ni $BASE64_OUT al repositorio (ya están en .gitignore)."
