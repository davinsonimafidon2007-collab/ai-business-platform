// Resolución centralizada de la URL base de la API (F1).
//
// Orden de precedencia:
//   1. Override en runtime persistido en localStorage (setApiBaseUrl) — permite
//      apuntar a la IP LAN del PC desde un móvil físico SIN rebuild.
//   2. NEXT_PUBLIC_API_URL (build-time, incrustada en el bundle estático).
//   3. Android nativo (Capacitor): 10.0.2.2 (alias del host SOLO en el emulador).
//   4. Navegador en localhost/127.0.0.1: mismo protocolo/host con puerto 8000.
//   5. Fallback http://localhost:8000.
import { Capacitor } from "@capacitor/core";

const API_BASE_URL_OVERRIDE_KEY = "api_base_url";

export const getApiBaseUrl = (): string => {
  // Override en runtime: IP LAN del PC para un móvil físico (sin rebuild).
  // Tiene prioridad sobre NEXT_PUBLIC_API_URL: en un APK, la URL de build suele
  // ser localhost/10.0.2.2 (no válida en un móvil real), así que el override
  // permite corregirla desde la app sin recompilar.
  if (typeof window !== "undefined") {
    const override = window.localStorage.getItem(API_BASE_URL_OVERRIDE_KEY);
    if (override && /^https?:\/\/.+/.test(override)) {
      return override.replace(/\/+$/, "");
    }
  }

  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl) {
    return envUrl;
  }

  // Android nativo (Capacitor WebView) sin NEXT_PUBLIC_API_URL ni override:
  // el emulador expone el host en 10.0.2.2. El network_security_config ya
  // permite cleartext a ese host en desarrollo.
  if (Capacitor.isNativePlatform() && Capacitor.getPlatform() === "android") {
    return "http://10.0.2.2:8000";
  }

  // En desarrollo, usar el mismo protocolo que la página actual
  // (evita errores de Mixed Content en Android/WebView).
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const port = window.location.port;

    if (host === "localhost" || host === "127.0.0.1") {
      return `${protocol}//${host}:8000`;
    }
  }

  // Fallback para desarrollo local
  return "http://localhost:8000";
};

export const setApiBaseUrl = (url: string): void => {
  if (typeof window === "undefined") {
    return;
  }
  const clean = url.trim().replace(/\/+$/, "");
  window.localStorage.setItem(API_BASE_URL_OVERRIDE_KEY, clean);
};
