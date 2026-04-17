// CalorIA – Service Worker
// Versión del caché: cambiá este número para forzar actualización
const CACHE_NAME = 'caloria-v3';

const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap',
];

// ── INSTALL: guardar archivos en caché ──
self.addEventListener('install', event => {
  console.log('[SW] Instalando CalorIA v3...');
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Cachear assets locales (los de Google Fonts pueden fallar sin internet, no pasa nada)
      const local = ASSETS_TO_CACHE.filter(u => !u.startsWith('http'));
      return cache.addAll(local).catch(err => console.warn('[SW] Cache parcial:', err));
    }).then(() => self.skipWaiting())
  );
});

// ── ACTIVATE: limpiar cachés viejos ──
self.addEventListener('activate', event => {
  console.log('[SW] Activando...');
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ── FETCH: estrategia Cache-First con fallback a red ──
self.addEventListener('fetch', event => {
  // Solo interceptar GET
  if (event.request.method !== 'GET') return;

  // Ignorar extensiones de Chrome y peticiones no-http
  if (!event.request.url.startsWith('http')) return;

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;

      return fetch(event.request).then(resp => {
        // Guardar en caché respuestas válidas de nuestro dominio
        if (resp && resp.status === 200 && resp.type !== 'opaque') {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return resp;
      }).catch(() => {
        // Offline fallback: devolver index.html para navegación
        if (event.request.mode === 'navigate') {
          return caches.match('/index.html');
        }
      });
    })
  );
});

// ── BACKGROUND SYNC (preparado para futuro Firebase) ──
self.addEventListener('sync', event => {
  if (event.tag === 'sync-data') {
    console.log('[SW] Background sync disparado');
    // Acá iría la lógica de sincronización con Firebase
  }
});
