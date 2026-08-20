#!/bin/bash
# scripts/update-cert-pin.sh
# Extrae el hash SHA-256 del certificado de un dominio y actualiza network_security_config.xml

set -euo pipefail

DOMAIN="${1:-api.aibusiness.com}"
PORT="${2:-443}"
CONFIG_FILE="frontend/android/app/src/main/res/xml/network_security_config.xml"

echo "🔒 Extrayendo Certificate Pin para $DOMAIN:$PORT..."

# Verificar que openssl está disponible
if ! command -v openssl &> /dev/null; then
    echo "❌ ERROR: openssl no está instalado"
    exit 1
fi

# Extraer hash SHA-256 de la clave pública
echo "🔍 Conectando con $DOMAIN:$PORT..."
CERT_HASH=$(openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:$PORT" < /dev/null 2>/dev/null | \
    openssl x509 -pubkey -noout | \
    openssl pkey -pubin -outform der | \
    openssl dgst -sha256 -binary | \
    openssl enc -base64)

if [ -z "$CERT_HASH" ]; then
    echo "❌ ERROR: No se pudo extraer el hash del certificado"
    echo "💡 Verifica que el dominio es accesible y tiene un certificado válido"
    exit 1
fi

echo "✅ Hash SHA-256 extraído: $CERT_HASH"
echo ""

# Verificar que el archivo de configuración existe
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ ERROR: No se encontró $CONFIG_FILE"
    exit 1
fi

# Generar hash de respaldo (backup pin)
# En producción, deberías generar un segundo certificado y extraer su hash
# Por ahora, usamos un placeholder que el desarrollador debe reemplazar
BACKUP_HASH="REPLACE_WITH_BACKUP_CERTIFICATE_HASH"

echo "📝 Actualizando $CONFIG_FILE..."

# Crear backup del archivo original
cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"

# Reemplazar el placeholder del pin principal
sed -i.bak "s|REPLACE_WITH_REAL_SHA256_HASH_OF_PROD_CERT=|$CERT_HASH|g" "$CONFIG_FILE"

# Reemplazar el placeholder del pin de respaldo (si existe)
if [ "$BACKUP_HASH" != "REPLACE_WITH_BACKUP_CERTIFICATE_HASH" ]; then
    sed -i.bak "s|REPLACE_WITH_BACKUP_SHA256_HASH=|$BACKUP_HASH|g" "$CONFIG_FILE"
fi

# Eliminar archivos de backup de sed
rm -f "${CONFIG_FILE}.bak"

echo "✅ Certificate Pin actualizado correctamente"
echo ""
echo "📋 Cambios realizados:"
echo "   - Pin principal: $CERT_HASH"
echo "   - Pin de respaldo: $BACKUP_HASH (debes generar un certificado de respaldo)"
echo ""
echo "⚠️  PRÓXIMOS PASOS:"
echo "1. Reconstruye la app: ./scripts/build-android.sh release"
echo "2. Prueba la app en un dispositivo real"
echo "3. Verifica que las conexiones HTTPS funcionan correctamente"
echo "4. Genera un certificado de respaldo y actualiza el backup pin"
echo ""
echo "💡 El archivo original se guardó en: ${CONFIG_FILE}.backup"
