import type { CapacitorConfig } from '@capacitor/cli';

// Google OAuth client IDs reales del proyecto (mismos que google-auth.ts).
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
      clientId:
        process.env.GOOGLE_WEB_CLIENT_ID ||
        '983773208764-oevega4uglktmrisjrh41teq5mjb270n.apps.googleusercontent.com',
      androidClientId:
        process.env.GOOGLE_ANDROID_CLIENT_ID ||
        '983773208764-7i0hfifq4ni324qnugvj0a79bu09fh4t.apps.googleusercontent.com',
      iosClientId:
        process.env.GOOGLE_IOS_CLIENT_ID ||
        '983773208764-oevega4uglktmrisjrh41teq5mjb270n.apps.googleusercontent.com',
    },
  },
};

export default config;
