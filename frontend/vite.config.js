import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

// Vercel builds the isolated frontend service and need not include sibling
// ops/ files. Those ports are used by the local dev proxy ONLY. Local runs
// still read the single authoritative checked-in ops/dev_ports.json.
const ports = process.env.VERCEL === '1'
  ? { frontend: 5173, backend: 8000 }
  : JSON.parse(readFileSync(new URL('../ops/dev_ports.json', import.meta.url), 'utf8'));

// Separate, fixed loopback ports for local development. Never auto-fallback.
const frontendPort = ports.frontend;
const backendPort = ports.backend;
const validPort = p => Number.isInteger(p) && p >= 1024 && p <= 65535;
if (!validPort(frontendPort) || !validPort(backendPort) || frontendPort === backendPort) {
  throw new Error('KATS dev ports must be distinct valid integers');
}
const backend = `http://127.0.0.1:${backendPort}`;

// A unique release marker for *each built artifact*. Deployment SHA wins when
// supplied by CI; local standalone builds receive a distinct build timestamp.
// Never cache this release metadata or put secrets into it.
const releaseId = process.env.KATS_RELEASE_SHA ||
  process.env.VERCEL_GIT_COMMIT_SHA ||
  process.env.RAILWAY_GIT_COMMIT_SHA ||
  process.env.RENDER_GIT_COMMIT ||
  process.env.GITHUB_SHA ||
  'local-' + Date.now().toString(36);
const versionAsset = {
  name: 'kats-release-discovery',
  generateBundle() {
    const readPublic = file => readFileSync(new URL('./public/' + file, import.meta.url));
    const worker = readPublic('sw.js').toString();
    const hash = createHash('sha256').update(worker)
      .update(readPublic('offline.html')).update(readPublic('offline-reconnect.js')).digest('hex');
    this.emitFile({type: 'asset', fileName: 'sw.js', source: worker.replace('__SHELL_HASH__', hash)});
    this.emitFile({
      type: 'asset', fileName: 'app-version.json',
      source: JSON.stringify({version:releaseId})
    });
  }
};

export default defineConfig({
  define: { __KATS_BUILD_ID__: JSON.stringify(releaseId) },
  plugins: [react(), versionAsset],
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
