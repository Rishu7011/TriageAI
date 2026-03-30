import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// FILE 8: vite.config.js
// The axios client in src/lib/api.js now uses VITE_API_BASE_URL directly,
// so the proxy is only needed if you want to keep relative-URL calls working
// in dev. It is kept here as a convenience but is no longer the primary routing
// mechanism.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/admit': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/queue': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/alerts': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/simulate': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/load-demo': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/whatif': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
