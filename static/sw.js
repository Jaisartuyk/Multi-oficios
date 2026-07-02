const CACHE_NAME = 'obraya-v1';
const OFFLINE_URL = '/offline/';

// Assets to pre-cache for offline shell
const PRECACHE_ASSETS = [
    '/',
    '/static/css/styles.css',
    '/static/js/app.js',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap',
];

// Install: cache the app shell
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(PRECACHE_ASSETS).catch(() => {
                // Silently fail for individual assets on first install
            });
        })
    );
    self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// Fetch: network-first for HTML, cache-first for static assets
self.addEventListener('fetch', (event) => {
    const { request } = event;

    // Skip non-GET requests (POST forms, etc.)
    if (request.method !== 'GET') return;

    // For navigation requests (HTML pages): network first, fallback to cache
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                    return response;
                })
                .catch(() => caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL)))
        );
        return;
    }

    // For static assets: cache first, fallback to network
    if (request.url.includes('/static/') || request.url.includes('fonts.googleapis.com') || request.url.includes('fonts.gstatic.com')) {
        event.respondWith(
            caches.match(request).then(
                (cached) =>
                    cached ||
                    fetch(request).then((response) => {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                        return response;
                    })
            )
        );
        return;
    }
});

// Push notification handler
self.addEventListener('push', (event) => {
    let data = { title: 'ObraYa', body: 'Tienes una nueva notificación.' };

    try {
        if (event.data) {
            data = event.data.json();
        }
    } catch {
        if (event.data) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body || 'Tienes una nueva notificación.',
        icon: '/static/img/icon-192.png',
        badge: '/static/img/icon-192.png',
        vibrate: [200, 100, 200],
        tag: data.tag || 'obraya-notification',
        data: {
            url: data.url || '/',
        },
        actions: data.actions || [],
    };

    event.waitUntil(self.registration.showNotification(data.title || 'ObraYa', options));
});

// Notification click: open the app at the right URL
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const targetUrl = event.notification.data?.url || '/';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
            // Focus existing window if available
            for (const client of clients) {
                if (client.url.includes(targetUrl) && 'focus' in client) {
                    return client.focus();
                }
            }
            // Otherwise open a new window
            return self.clients.openWindow(targetUrl);
        })
    );
});
