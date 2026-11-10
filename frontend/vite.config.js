import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// All browser calls use same-origin paths. Proxy API and readiness to the real
// local Flask process; otherwise Vite's SPA fallback returns HTML with HTTP 200.
const backend = 'http://127.0.0.1:8000';
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/readyz': { target: backend, changeOrigin: true },
      '/healthz': { target: backend, changeOrigin: true }
    }
  }
});
