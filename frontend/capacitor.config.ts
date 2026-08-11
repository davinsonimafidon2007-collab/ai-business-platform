import type { CapacitorConfig } from '@capacitor/cli';
import {
  GOOGLE_ANDROID_CLIENT_ID,
  GOOGLE_IOS_CLIENT_ID,
  GOOGLE_WEB_CLIENT_ID,
} from './src/app/config/google-clients';

// Google OAuth client IDs reales del proyecto, centralizados en
// src/app/config/google-clients.ts (MED.008). Capacitor CLI compila este
// fichero en Node y resuelve los import relativos, así que google-auth.ts y
// capacitor.config.ts siempre usan los mismos valores.
// CRIT.002: el guard scripts/check-capacitor-config.mjs (y pre-build-check.sh)
// falla el build a proposito si se conserva un valor placeholder sin rellenar.

// GRAVE.001: el scheme del WebView debe coincidir con el backend. En local
// (APK debug contra http://IP:8000 o http://localhost:8000) usar 'http':
// con 'https' el WebView sirve en https://localhost y los fetch a http://...
// caen en mixed-content, por mucho que el network_security_config permita
// cleartext. En producción con backend HTTPS usar 'https'.
const androidScheme = process.env.CAPACITOR_ANDROID_SCHEME || 'http';

const config: CapacitorConfig = {
  appId: 'com.aibusiness.platform',
  appName: 'AI Business Platform',
  webDir: 'out',
  server: {
    androidScheme,
  },
  plugins: {
    Camera: {
      permissions: true,
    },
    GoogleAuth: {
      clientId: GOOGLE_WEB_CLIENT_ID,
      androidClientId: GOOGLE_ANDROID_CLIENT_ID,
      iosClientId: GOOGLE_IOS_CLIENT_ID,
    },
  },
};

export default config;
