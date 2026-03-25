import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// FILE 8: vite.config.js — proxies /api to the FastAPI backend
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/admit': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/queue': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/alerts': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/simulate': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/load-demo': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/whatif': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
