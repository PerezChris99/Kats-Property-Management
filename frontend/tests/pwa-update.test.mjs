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
  assert.ok(sw.includes("'/offline-reconnect.js'"), 'offline recovery script is in the static-only cache');
  assert.ok(read('public/offline.html').includes('defer src="/offline-reconnect.js"'));
  assert.ok(read('public/offline-reconnect.js').includes("window.addEventListener('online', reconnect)"));
  assert.ok(nginx.includes('location = /app-version.json'));
  assert.ok(nginx.includes('add_header Cache-Control "no-store, max-age=0" always;'));
  assert.ok([vercel,vercelRoot].every(v =>
    v.headers.some(h=>h.source==='/app-version.json' &&
      h.headers.some(p=>p.key==='Cache-Control'&&p.value.includes('no-store')))));
  assert.ok(read('src/main.jsx').includes("navigator.serviceWorker.register('/sw.js', {updateViaCache: 'none'})"));
  assert.ok(read('public/manifest.webmanifest').includes('"display": "standalone"'));
});


test('manifest includes real 192 and 512 pixel raster icons, install scope and secure offline worker', () => {
  const manifest = JSON.parse(read('public/manifest.webmanifest'));
  assert.equal(manifest.display, 'standalone');
  assert.equal(manifest.scope, '/');
  assert.ok(manifest.start_url.startsWith('/'));
  assert.ok(manifest.icons.some(i => i.src === '/icon-192.png'
    && i.type === 'image/png' && i.sizes === '192x192' && i.purpose === 'any'));
  assert.ok(manifest.icons.some(i => i.src === '/icon-512-maskable.png'
    && i.type === 'image/png' && i.sizes === '512x512' && i.purpose === 'maskable'));
  const png = (file, size) => {
    const bytes = readFileSync(new URL('../public/' + file, import.meta.url));
    assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    assert.equal(bytes.readUInt32BE(16), size);
    assert.equal(bytes.readUInt32BE(20), size);
    assert.ok(bytes.length > 2000);
  };
  png('icon-192.png', 192);
  png('icon-512-maskable.png', 512);
  const sw=read('public/sw.js');
  assert.ok(manifest.icons.some(i => i.sizes === '512x512' && i.purpose === 'any'));
  assert.ok(read('index.html').includes('rel="apple-touch-icon"'));
  assert.ok(sw.includes("cache.match('/offline.html')"));
  assert.ok(read('index.html').includes('rel="manifest" href="/manifest.webmanifest"'));
  assert.ok(read('src/main.jsx').includes("import.meta.env.PROD"));
});
