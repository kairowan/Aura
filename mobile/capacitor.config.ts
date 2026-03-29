import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.aura.mobile',
  appName: 'Aura Mobile',
  webDir: 'www',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'https',
    iosScheme: 'https',
    allowNavigation: ['*'],
  },
};

export default config;
