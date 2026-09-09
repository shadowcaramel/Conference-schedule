/* ЯДРО-2026 programme — service worker.
   Network-first so conference-day updates are not hidden behind yesterday's cache.
   HTTPS / localhost only; the page never registers this file on plain HTTP. */
'use strict';

const CACHE = 'nucleus2026-v1';
const PRECACHE = [
  './',
  './index.html',
  './app.css',
  './app.js',
  './data.js',
  './manifest.json',
  './assets/icons/icon.svg',
  './assets/icons/icon-192.png',
  './assets/icons/icon-512.png',
  './assets/icons/apple-touch-icon.png',
  './assets/fonts/onest-cyrillic.woff2',
  './assets/fonts/onest-cyrillic-ext.woff2',
  './assets/fonts/onest-latin.woff2',
  './assets/fonts/onest-latin-ext.woff2',
  './assets/fonts/onest-math.woff2',
];

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
    try {
      const fresh = await fetch(req);
      if (fresh && fresh.ok && (url.protocol === 'http:' || url.protocol === 'https:')) {
        cache.put(req, fresh.clone()).catch(() => {});
      }
      return fresh;
    } catch {
      const cached = await cache.match(req);
      if (cached) return cached;
      if (req.mode === 'navigate') {
        return (await cache.match('./index.html')) || (await cache.match('./')) || Response.error();
      }
      return Response.error();
    }
  })());
});
