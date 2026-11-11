import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import ports from '../ops/dev_ports.json';

// Separate, fixed loopback ports for local development. Never auto-fallback.
const frontendPort = ports.frontend;
const backendPort = ports.backend;
const validPort = p => Number.isInteger(p) && p >= 1024 && p <= 65535;
if (!validPort(frontendPort) || !validPort(backendPort) || frontendPort === backendPort) {
  throw new Error('KATS dev ports must be distinct valid integers');
}
const backend = `http://127.0.0.1:${backendPort}`;

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/readyz': { target: backend, changeOrigin: true },
      '/healthz': { target: backend, changeOrigin: true }
    }
  }
});
