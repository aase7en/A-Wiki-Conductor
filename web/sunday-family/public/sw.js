/* Only build-listed public shell assets enter this cache. Never cache monitor data. */
importScripts('./precache.js');
const CACHE_PREFIX = 'sunday-family-shell-';
const CACHE_NAME = CACHE_PREFIX + self.SUNDAY_PRECACHE.version;
const MAX_ENTRIES = 64;
const ASSETS = self.SUNDAY_PRECACHE.assets;

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    if (ASSETS.length > MAX_ENTRIES) throw new Error('Shell exceeds precache limit');
    const cache = await caches.open(CACHE_NAME);
    // Do not skipWaiting: keep old pages and their hashed assets on one version.
    await cache.addAll(ASSETS.map(path => new Request(new URL(path, self.location.origin), {
      credentials: 'omit', cache: 'reload',
    })));
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (request.method !== 'GET') return;
  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request, { cache: 'no-store' }));
    return;
  }
  if (request.headers.has('authorization')) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(async () => {
      const cache = await caches.open(CACHE_NAME);
      return await cache.match('/index.html') || Response.error();
    }));
  } else if (!url.search && ASSETS.includes(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      return await cache.match(request) || fetch(request);
    })());
  }
});
