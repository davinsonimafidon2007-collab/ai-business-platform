import type { CapacitorConfig } from '@capacitor/cli';
import {
  GOOGLE_ANDROID_CLIENT_ID,
  GOOGLE_IOS_CLIENT_ID,
  GOOGLE_WEB_CLIENT_ID,
} from './src/app/config/google-clients';

// SEGURIDAD: En producción, CAPACITOR_ANDROID_SCHEME debe ser 'https'.
// 'http' solo está permitido explícitamente para builds de debug local.
const androidScheme = process.env.CAPACITOR_ANDROID_SCHEME || 'https';

const config: CapacitorConfig = {
  appId: 'com.aibusiness.platform',
  appName: 'AI Business Platform',
  webDir: 'out',
  server: {
    androidScheme,
    // MOB-P1-009: hosts de App Links aceptados (deep links http/https).
    allowNavigation: ['aibusiness.app', 'app.aibusiness.com', 'aibusiness.platform', 'localhost'],
  },
  plugins: {
    Camera: {
      permissions: true,
    },
    GoogleAuth: {
      clientId: GOOGLE_WEB_CLIENT_ID,
      androidClientId: GOOGLE_ANDROID_CLIENT_ID,
      iosClientId: GOOGLE_IOS_CLIENT_ID,
      scopes: ['profile', 'email'],
      forceCodeForRefreshToken: true,
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      androidScaleType: 'CENTER_CROP',
    },
    Preferences: {
      storage: 'local',
    },
  },
};

export default config;
