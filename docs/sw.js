// Offline: shell in cache; index.html rete-prima (aggiornamenti), db.json cache-prima con aggiornamento in background.
const C = 'ygoscan-v1', SHELL = ['./', 'index.html', 'manifest.json', 'icon.png', 'db.json'];
self.addEventListener('install', e => e.waitUntil(caches.open(C).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url); if (u.origin !== location.origin || e.request.method !== 'GET') return;
  const refresh = () => fetch(e.request).then(r => { if (r.ok) caches.open(C).then(c => c.put(e.request, r.clone())); return r; });
  if (u.pathname.endsWith('db.json')) e.respondWith(caches.match(e.request).then(hit => { const p = refresh().catch(() => hit); return hit || p; }));
  else if (u.pathname.endsWith('/') || u.pathname.endsWith('index.html')) e.respondWith(refresh().catch(() => caches.match(e.request)));
  else e.respondWith(caches.match(e.request).then(hit => hit || refresh()));
});
