import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.aibusiness.platform',
  appName: 'AI Business Platform',
  webDir: 'out',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    Camera: {
      permissions: true,
    },
    GoogleAuth: {
      clientId: process.env.GOOGLE_WEB_CLIENT_ID || 'REPLACE_ME',
      androidClientId: process.env.GOOGLE_ANDROID_CLIENT_ID || 'REPLACE_ME',
      iosClientId: process.env.GOOGLE_IOS_CLIENT_ID || 'REPLACE_ME',
    },
  },
};

export default config;
