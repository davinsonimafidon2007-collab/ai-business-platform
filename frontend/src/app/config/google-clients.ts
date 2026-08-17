// MED.008/SEC-001: client IDs de Google centralizados en un solo lugar.
//
// SEC-001: NO commitear valores reales en este archivo. El fallback de cada
// variable es una cadena vacía; el guard scripts/check-capacitor-config.mjs
// (y el check pre-build) fallan el build a propósito si faltan las variables
// cuando la autenticación móvil está activa.
//
// Se aceptan las dos nomenclaturas de env: con prefijo NEXT_PUBLIC_ (para el
// bundle de Next) y sin prefijo (GOOGLE_*, para el proceso de `cap sync`).
// Web: client_type 3 de google-services.json. Android: client_type 1.
//
// La fuente de verdad para el build de Capacitor es capacitor.config.ts, que
// importa estos valores. capacitor.config.json ya no se commitea (SEC-001).

function getClientId(varName: string, nextPublicVarName: string): string {
  const value = process.env[nextPublicVarName] || process.env[varName] || "";
  return value.trim();
}

export const GOOGLE_WEB_CLIENT_ID = getClientId(
  "GOOGLE_WEB_CLIENT_ID",
  "NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID"
);

export const GOOGLE_ANDROID_CLIENT_ID = getClientId(
  "GOOGLE_ANDROID_CLIENT_ID",
  "NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID"
);

export const GOOGLE_IOS_CLIENT_ID = getClientId(
  "GOOGLE_IOS_CLIENT_ID",
  "NEXT_PUBLIC_GOOGLE_IOS_CLIENT_ID"
);
