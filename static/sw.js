const CACHE_NAME = 'anx-calibre-manager-v1';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/manifest.webmanifest'
  // Note: We don't cache book data or API calls, only the app shell.
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

// Cache and return requests
self.addEventListener('fetch', event => {
    // We only want to cache GET requests.
    if (event.request.method !== 'GET') {
        return;
    }

    // For navigation requests, use a network-first strategy.
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    // For other requests (like CSS, images), use a cache-first strategy.
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request).then(fetchResponse => {
                // Check if we received a valid response to cache
                if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
                    return fetchResponse;
                }

                const responseToCache = fetchResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                return fetchResponse;
            });
        })
    );
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