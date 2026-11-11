/* Static-only offline support. No API, auth, HTML, tenant, financial or
 * signed-document responses are cached or served from previous sessions. */
const CACHE = 'kats-static-v2';
const STATIC = ['/offline.html', '/icon.svg', '/brand-mark.svg'];
const MAX_ASSETS = 70;

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(key => key.startsWith('kats-static-') && key !== CACHE)
      .map(key => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  // Cross-origin photos/fonts may have unclear consent/licensing semantics.
  // All private API responses explicitly bypass the service worker.
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/offline.html')));
    return;
  }
  const staticAsset = url.pathname.startsWith('/assets/') ||
    STATIC.includes(url.pathname);
  if (!staticAsset) return;
  event.respondWith((async () => {
    const store = await caches.open(CACHE);
    const cached = await store.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok && response.type === 'basic') {
      await store.put(request, response.clone());
      const keys = await store.keys();
      await Promise.all(keys.slice(0, Math.max(0, keys.length - MAX_ASSETS))
        .map(key => store.delete(key)));
    }
    return response;
  })());
});
