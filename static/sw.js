const CACHE_NAME = 'anx-calibre-manager-v4'; // Bump version to force update
const urlsToCache = [
  '/',
  '/login',
  '/settings',
  '/static/style.css',
  '/static/manifest.webmanifest',
  '/static/logo.svg',
  '/static/logo.png'
];

// Install a service worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Cache and return requests with appropriate strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    if (request.method !== 'GET') {
        return;
    }

    // Strategy 1: Dynamic Content (API & Page Navigations) -> Network First, then Cache
    if (url.pathname.startsWith('/api/') || request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then(networkResponse => {
                    // If successful, update the cache for future offline use
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return networkResponse;
                })
                .catch(() => {
                    // If network fails, serve from cache
                    console.log('Network request failed, serving from cache for:', request.url);
                    return caches.match(request);
                })
        );
        return;
    }

    // Strategy 2: Static Assets (App Shell, Covers) -> Cache First, then Network
    if (
        url.pathname.startsWith('/static/') ||
        url.pathname.startsWith('/calibre_cover/') ||
        url.pathname.startsWith('/anx_cover/')
    ) {
        event.respondWith(
            caches.match(request).then(cachedResponse => {
                return cachedResponse || fetch(request).then(fetchResponse => {
                    if (fetchResponse && fetchResponse.status === 200) {
                        const responseToCache = fetchResponse.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return fetchResponse;
                });
            })
        );
        return;
    }

    // Default: For anything else, just fetch from network without caching
    event.respondWith(fetch(request));
});


// Update a service worker
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});