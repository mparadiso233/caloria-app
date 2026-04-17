// CalorIA – Service Worker
// ⚠️ Cambiá CACHE_VERSION para forzar actualización en todos los dispositivos
const CACHE_VERSION = 'v5';
const CACHE_NAME = `caloria-${CACHE_VERSION}`;

const LOCAL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// ── INSTALL ──────────────────────────────────────────
self.addEventListener('install', event => {
  console.log(`[SW] Instalando ${CACHE_NAME}...`);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(LOCAL_ASSETS).catch(err => console.warn('[SW] Cache parcial:', err)))
      // NO llamamos skipWaiting() aquí — esperamos que el usuario confirme la actualización
  );
});

// ── ACTIVATE: limpiar cachés viejos ─────────────────
self.addEventListener('activate', event => {
  console.log(`[SW] Activando ${CACHE_NAME}...`);
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => {
        console.log('[SW] Borrando caché viejo:', k);
        return caches.delete(k);
      })))
      .then(() => self.clients.claim()) // tomar control de todas las pestañas
  );
});

// ── FETCH: Network-First para index.html, Cache-First para el resto ──
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith('http')) return;

  const url = new URL(event.request.url);
  const isNavigation = event.request.mode === 'navigate';
  const isIndexHtml  = url.pathname === '/' || url.pathname.endsWith('index.html');

  if (isNavigation || isIndexHtml) {
    // Network-First para la página principal → siempre intenta traer la versión más nueva
    event.respondWith(
      fetch(event.request)
        .then(resp => {
          if (resp && resp.status === 200) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return resp;
        })
        .catch(() => {
          // Offline → servir desde caché
          return caches.match(event.request).then(cached => cached || caches.match('/index.html'));
        })
    );
    return;
  }

  // Cache-First para íconos, fonts, etc.
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(resp => {
        if (resp && resp.status === 200 && resp.type !== 'opaque') {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return resp;
      }).catch(() => null);
    })
  );
});

// ── MENSAJE: SKIP_WAITING (enviado desde el banner de actualización) ──
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[SW] Aplicando actualización por pedido del usuario...');
    self.skipWaiting();
  }
});
