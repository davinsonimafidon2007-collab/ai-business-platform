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
      clientId: '983773208764-oevega4uglktmrisjrh41teq5mjb270n.apps.googleusercontent.com',
      androidClientId: '983773208764-7i0hfifq4ni324qnugvj0a79bu09fh4t.apps.googleusercontent.com',
      iosClientId: '983773208764-oevega4uglktmrisjrh41teq5mjb270n.apps.googleusercontent.com',
    },
  },
};

export default config;
