/* ЯДРО-2026 programme — service worker.
   data.js and navigations: network-first so conference-day edits show up.
   CSS / JS / fonts / icons: cache-first, refresh in the background.
   HTTPS / localhost only; the page never registers this file on plain HTTP. */
'use strict';

const CACHE = 'nucleus2026-424827d5';
const PRECACHE = [
  './',
  './index.html',
  './app.css',
  './app.js',
  './data.js',
  './manifest.json',
  './assets/icons/icon.svg',
  './assets/icons/icon-192.png',
  './assets/fonts/onest-cyrillic.woff2',
  './assets/fonts/onest-latin.woff2',
  './assets/sponsors/gammatech.png',
  './assets/sponsors/digitizer.svg',
  './assets/sponsors/spegroup.svg',
  './assets/maps/pier-ru.png',
  './assets/maps/pier-en.png',
  './assets/maps/intourist-ru.png',
  './assets/maps/intourist-en.png',
];

function isProgrammeData(url) {
  const path = url.pathname;
  return path.endsWith('data.js') || path.endsWith('app.js') || path.endsWith('app.css');
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    for (const url of PRECACHE) {
      try { await cache.add(url); } catch { /* optional / first-deploy race */ }
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cacheable = url.protocol === 'http:' || url.protocol === 'https:';
    const put = (fresh) => {
      if (cacheable && fresh && fresh.ok) cache.put(req, fresh.clone()).catch(() => {});
    };

    const networkFirst = req.mode === 'navigate' || isProgrammeData(url);
    if (networkFirst) {
      try {
        const fresh = await fetch(req);
        put(fresh);
        return fresh;
      } catch {
        const cached = await cache.match(req);
        if (cached) return cached;
        if (req.mode === 'navigate') {
          return (await cache.match('./index.html')) || (await cache.match('./')) || Response.error();
        }
        return Response.error();
      }
    }

    const cached = await cache.match(req);
    const refresh = fetch(req).then((fresh) => { put(fresh); return fresh; }).catch(() => null);
    if (cached) return cached;
    return (await refresh) || Response.error();
  })());
});
