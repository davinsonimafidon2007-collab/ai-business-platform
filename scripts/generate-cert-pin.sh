#!/bin/bash
# scripts/generate-cert-pin.sh
# Uso: ./scripts/generate-cert-pin.sh tu-dominio.com 443

DOMAIN=${1:-"api.aibusiness.com"}
PORT=${2:-"443"}

echo "🔒 Generando Certificate Pin (SHA-256) para $DOMAIN:$PORT..."
echo "⚠️  Asegúrate de ejecutar esto contra el servidor de PRODUCCIÓN, no staging."

# Obtiene la cadena de certificados y extrae el hash SHA-256 de la clave pública
openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:$PORT" < /dev/null 2>/dev/null | \
  openssl x509 -pubkey -noout | \
  openssl pkey -pubin -outform der | \
  openssl dgst -sha256 -binary | \
  openssl enc -base64

echo "✅ Copia el valor anterior y pégalo en frontend/android/app/src/main/res/xml/network_security_config.xml"
