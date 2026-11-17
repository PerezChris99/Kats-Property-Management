import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = file => readFileSync(new URL('../'+file,import.meta.url),'utf8');

test('release discovery is generated from the exact build artifact, not from optimistic GitHub pushes', () => {
  const vite = read('vite.config.js');
  const update = read('src/AppUpdateNotice.jsx');
  assert.ok(vite.includes('const releaseId ='));
  assert.ok(vite.includes('GITHUB_SHA'));
  assert.ok(vite.includes("fileName: 'app-version.json'"));
  assert.ok(vite.includes('__KATS_BUILD_ID__'));
  assert.ok(update.includes('CURRENT_RELEASE'));
  assert.ok(update.includes('body.version !== CURRENT_RELEASE'));
  assert.ok(update.includes("fetch('/app-version.json'"));
  assert.ok(update.includes("cache: 'no-store'"));
  assert.ok(update.includes("response.headers.get('content-type')"));
  assert.ok(update.includes('navigator.serviceWorker.getRegistration()'));
  assert.ok(update.includes('registration?.update()'));
  assert.ok(update.includes('window.location.reload()'), 'user explicitly applies update');
  assert.ok(update.includes('setReady(newer)'));
});

test('browser and installed PWA check after reconnect, focus and on a two-minute cadence', () => {
  const source = read('src/AppUpdateNotice.jsx');
  const app = read('src/App.jsx');
  assert.ok(source.includes("window.addEventListener('online', wake)"));
  assert.ok(source.includes("window.addEventListener('focus', wake)"));
  assert.ok(source.includes("document.addEventListener('visibilitychange', wake)"));
  assert.ok(source.includes('const REFRESH_MS = 120000'));
  assert.ok(source.includes("window.addEventListener('kats:check-update', manually)"));
  assert.ok(source.includes('Get new update'));
  assert.ok(app.includes('<AppUpdateNotice/>'));
  assert.ok(app.includes('<CheckAppUpdatesButton/>'));
  assert.ok(read('src/site/PublicMegaNavigation.jsx').includes('kats:check-update'));
});

test('release metadata and SW are private-data-safe and never cached as immutable', () => {
  const sw = read('public/sw.js');
  const nginx = read('nginx.conf');
  const vercel = JSON.parse(read('vercel.json'));
  const vercelRoot = JSON.parse(read('../vercel.json'));
  assert.ok(sw.includes("url.pathname === '/app-version.json'"));
  assert.ok(sw.includes("url.pathname.startsWith('/api/')"));
  assert.ok(sw.includes("request.mode === 'navigate'"));
  assert.ok(nginx.includes('location = /app-version.json'));
  assert.ok(nginx.includes('add_header Cache-Control "no-store, max-age=0" always;'));
  assert.ok([vercel,vercelRoot].every(v =>
    v.headers.some(h=>h.source==='/app-version.json' &&
      h.headers.some(p=>p.key==='Cache-Control'&&p.value.includes('no-store')))));
  assert.ok(read('src/main.jsx').includes("navigator.serviceWorker.register('/sw.js')"));
  assert.ok(read('public/manifest.webmanifest').includes('"display": "standalone"'));
});
