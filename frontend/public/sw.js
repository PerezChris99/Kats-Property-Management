// The build gives each offline shell a content-derived cache name.
const CACHE = 'kats-static-__SHELL_HASH__';
const SHELL = ['/offline.html', '/offline-reconnect.js'];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const entries = await Promise.all(SHELL.map(async path => {
      const response = await fetch(path, {cache: 'reload', credentials: 'omit', redirect: 'error'});
      const type = response.headers.get('content-type') || '';
      const validType = path.endsWith('.js') ? /javascript/i.test(type) : /^text\/html/i.test(type);
      if (!response.ok || !validType) throw new Error('Offline shell unavailable');
      return [path, response];
    }));
    await Promise.all(entries.map(([path, response]) => cache.put(path, response)));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith('kats-static-') && key !== CACHE)
      .map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin ||
      url.pathname.startsWith('/api/') || url.pathname === '/api' ||
      url.pathname === '/app-version.json' || url.pathname === '/sw.js' ||
      url.pathname === '/readyz' || url.pathname === '/healthz') return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(async () => {
      const cache = await caches.open(CACHE);
      return await cache.match('/offline.html') || Response.error();
    }));
  } else if (!url.search && SHELL.includes(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      return await cache.match(url.pathname) || fetch(request);
    })());
  }
});
