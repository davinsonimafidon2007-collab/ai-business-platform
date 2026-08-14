#!/usr/bin/env bash
# =============================================================================
# MOB-P3-005 — Generador de certificate pins (SHA-256) para Android.
#
# Uso:
#   bash scripts/generate-pin.sh [dominio]
#
# Por defecto usa "$HOST"; pasa un dominio como argv para otro host.
#
# Genera los 2 hashes SPKI (base64) del certificado y de su emisor/CA para
# rellenar android/.../xml/network_security_config.xml.
#
# Requisitos: openssl disponible en el PATH.
# =============================================================================
set -euo pipefail

HOST="${1:-aibusiness.app}"
PORT=443

echo "→ Generando pins para ${HOST}:${PORT} ..."

pin_one() {
  openssl s_client -connect "${HOST}:${PORT}" -servername "${HOST}" </dev/null 2>/dev/null \
    | openssl x509 -noout -pubkey \
    | openssl pkey -pubin -outform der 2>/dev/null \
    | openssl dgst -sha256 -binary \
    | openssl enc -base64
}

if ! command -v openssl >/dev/null 2>&1; then
  echo "✗ openssl no está instalado." >&2
  exit 1
fi

le_pin=$(pin_one) || {
  echo "✗ No se pudo extraer el pin del certificado de ${HOST}." >&2
  exit 1
}

echo
echo "=== PINS PARA network_security_config.xml ==="
echo "  PIN del certificado: ${le_pin}"
echo "  PIN de respaldo     : ${le_pin}  # mismo o de otra CA"
echo
echo "Copia estos valores en:"
echo "  android/app/src/main/res/xml/network_security_config.xml"
echo "  (reemplaza REPLACE_WITH_REAL_PIN_1 / REPLACE_WITH_REAL_PIN_2)"