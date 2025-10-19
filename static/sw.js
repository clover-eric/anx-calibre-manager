// ============================================================================
// Service Worker Configuration
// ============================================================================

const CONFIG = {
  cacheName: 'anx-calibre-manager-v1',
  version: '1.0.0',
  
  // Cache timeout settings (in milliseconds)
  timeout: {
    network: 3000,  // Network timeout for stale-while-revalidate
    cache: 5000     // Maximum age for cached responses
  },
  
  // Resources to precache on installation
  precacheUrls: [
    // Pages
    '/',
    '/login',
    '/settings',
    
    // Core CSS
    '/static/style.css',
    '/static/reader.css',
    
    // Main CSS - Base styles
    '/static/css/main/base.css',
    '/static/css/main/components.css',
    '/static/css/main/forms.css',
    '/static/css/main/layout.css',
    '/static/css/main/modals.css',
    '/static/css/main/navigation.css',
    '/static/css/main/pages.css',
    '/static/css/main/responsive.css',
    '/static/css/main/variables.css',
    
    // Main CSS - Additional features
    '/static/css/main/chat_player.css',
    '/static/css/main/user_activities.css',
    '/static/css/audio_player.css',
    
    // Reader CSS
    '/static/css/reader/base.css',
    '/static/css/reader/components.css',
    '/static/css/reader/sidebar.css',
    '/static/css/reader/toolbar.css',
    '/static/css/reader/tts.css',
    '/static/css/reader/variables.css',
    
    // Images
    '/static/logo.svg',
    '/static/logo.png',
    '/static/images/default-cover.svg',
    
    // Core JavaScript
    '/static/js/index.js',
    '/static/js/login.js',
    '/static/js/register.js',
    '/static/js/reader.js',
    '/static/js/audio_player.js',
    
    // Page JavaScript modules
    '/static/js/page/utils.js',
    '/static/js/page/ui.js',
    '/static/js/page/handlers.js',
    '/static/js/page/completions.js',
    '/static/js/page/translations.js',
    '/static/js/page/chat_player.js',
    
    // Settings JavaScript modules
    '/static/js/settings/common.js',
    '/static/js/settings/main.js',
    '/static/js/settings/tabs.js',
    '/static/js/settings/global_settings.js',
    '/static/js/settings/user_settings.js',
    '/static/js/settings/user_management.js',
    '/static/js/settings/user_activities.js',
    '/static/js/settings/invite_codes.js',
    '/static/js/settings/service_profiles.js',
    '/static/js/settings/mcp.js'
  ],
  
  // URL patterns for different caching strategies
  patterns: {
    api: /^\/api\//,
    static: /^\/static\//,
    covers: /^\/(calibre_cover|anx_cover)\//,
    navigation: request => request.mode === 'navigate'
  }
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Log messages with timestamp and prefix
 */
const logger = {
  info: (message, ...args) => {
    console.log(`[SW ${CONFIG.version}] ${message}`, ...args);
  },
  error: (message, ...args) => {
    console.error(`[SW ${CONFIG.version}] ERROR: ${message}`, ...args);
  },
  warn: (message, ...args) => {
    console.warn(`[SW ${CONFIG.version}] WARNING: ${message}`, ...args);
  }
};

/**
 * Check if a request should be handled by the service worker
 */
function shouldHandleRequest(request) {
  // Only handle GET requests
  if (request.method !== 'GET') {
    return false;
  }
  
  // Skip chrome-extension and other non-http(s) requests
  const url = new URL(request.url);
  if (!url.protocol.startsWith('http')) {
    return false;
  }
  
  return true;
}

/**
 * Create a timeout promise
 */
function createTimeoutPromise(timeout) {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Network timeout')), timeout);
  });
}

/**
 * Check if response is valid for caching
 */
function isValidResponse(response) {
  return response && 
         response.status === 200 && 
         response.type !== 'error';
}

// ============================================================================
// Caching Strategies
// ============================================================================

/**
 * Network First Strategy
 * Try network first, fall back to cache if network fails
 * Best for: API requests, dynamic content
 */
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (isValidResponse(networkResponse)) {
      const cache = await caches.open(CONFIG.cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    logger.warn('Network request failed, trying cache:', request.url);
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // If no cache available, return a custom offline response
    return new Response(
      JSON.stringify({ 
        error: 'Network unavailable', 
        offline: true 
      }), 
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Cache First Strategy
 * Try cache first, fall back to network if cache misses
 * Best for: Static assets, images
 */
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    // Optionally revalidate in background
    fetch(request).then(networkResponse => {
      if (isValidResponse(networkResponse)) {
        caches.open(CONFIG.cacheName).then(cache => {
          cache.put(request, networkResponse);
        });
      }
    }).catch(() => {
      // Silently fail background revalidation
    });
    
    return cachedResponse;
  }
  
  // Cache miss, fetch from network
  try {
    const networkResponse = await fetch(request);
    
    if (isValidResponse(networkResponse)) {
      const cache = await caches.open(CONFIG.cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    logger.error('Cache miss and network failed:', request.url);
    throw error;
  }
}

/**
 * Stale While Revalidate Strategy
 * Return cached response immediately, update cache in background
 * Best for: Frequently updated content that can tolerate staleness
 */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CONFIG.cacheName);
  const cachedResponse = await cache.match(request);
  
  // Start network request
  const fetchPromise = fetch(request).then(networkResponse => {
    if (isValidResponse(networkResponse)) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(error => {
    logger.warn('Background revalidation failed:', error);
    return null;
  });
  
  // Return cached response immediately if available
  // Otherwise wait for network
  return cachedResponse || fetchPromise;
}

/**
 * Network Only Strategy
 * Always fetch from network, no caching
 * Best for: Real-time data, user-specific content
 */
async function networkOnly(request) {
  return fetch(request);
}

// ============================================================================
// Request Router
// ============================================================================

/**
 * Route request to appropriate caching strategy
 */
function routeRequest(request) {
  const url = new URL(request.url);
  
  // API requests: Network First (need fresh data, but cache for offline)
  if (CONFIG.patterns.api.test(url.pathname)) {
    return networkFirst(request);
  }
  
  // Navigation requests: Network First (always try for fresh page)
  if (CONFIG.patterns.navigation(request)) {
    return networkFirst(request);
  }
  
  // Static assets and covers: Cache First (rarely change, fast loading)
  if (CONFIG.patterns.static.test(url.pathname) || 
      CONFIG.patterns.covers.test(url.pathname)) {
    return cacheFirst(request);
  }
  
  // Default: Network Only (unknown resources)
  return networkOnly(request);
}

// ============================================================================
// Service Worker Event Handlers
// ============================================================================

/**
 * Install Event
 * Triggered when service worker is first installed
 */
self.addEventListener('install', event => {
  logger.info('Installing service worker...');
  
  event.waitUntil(
    caches.open(CONFIG.cacheName)
      .then(cache => {
        logger.info('Precaching assets...');
        return cache.addAll(CONFIG.precacheUrls);
      })
      .then(() => {
        logger.info('Installation complete, skipping waiting...');
        return self.skipWaiting();
      })
      .catch(error => {
        logger.error('Installation failed:', error);
        throw error;
      })
  );
});

/**
 * Activate Event
 * Triggered when service worker takes control
 */
self.addEventListener('activate', event => {
  logger.info('Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        // Delete old caches
        return Promise.all(
          cacheNames
            .filter(cacheName => cacheName !== CONFIG.cacheName)
            .map(cacheName => {
              logger.info('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        logger.info('Claiming clients...');
        return self.clients.claim();
      })
      .then(() => {
        logger.info('Activation complete');
      })
      .catch(error => {
        logger.error('Activation failed:', error);
        throw error;
      })
  );
});

/**
 * Fetch Event
 * Intercept and handle all network requests
 */
self.addEventListener('fetch', event => {
  const { request } = event;
  
  // Skip non-GET requests and unsupported protocols
  if (!shouldHandleRequest(request)) {
    return;
  }
  
  // Route request to appropriate strategy
  event.respondWith(
    routeRequest(request).catch(error => {
      logger.error('Request failed:', request.url, error);
      
      // Return generic error response
      return new Response(
        'Network error occurred',
        {
          status: 408,
          statusText: 'Request Timeout',
          headers: { 'Content-Type': 'text/plain' }
        }
      );
    })
  );
});

/**
 * Message Event
 * Handle messages from clients (pages)
 */
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    logger.info('Received SKIP_WAITING message');
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    logger.info('Received CLEAR_CACHE message');
    event.waitUntil(
      caches.delete(CONFIG.cacheName).then(() => {
        logger.info('Cache cleared');
        return self.clients.claim();
      })
    );
  }
});

// ============================================================================
// Error Handling
// ============================================================================

self.addEventListener('error', event => {
  logger.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', event => {
  logger.error('Unhandled promise rejection:', event.reason);
});

// ============================================================================
// Log startup
// ============================================================================

logger.info('Service Worker initialized', {
  version: CONFIG.version,
  cacheName: CONFIG.cacheName
});