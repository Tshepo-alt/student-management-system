const CACHE_NAME = 'gips-portal-v1.0.0';
const urlsToCache = [
    '/',
    '/index.html',
    '/pages/student-dashboard.html',
    '/pages/login.html',
    '/pages/register.html',
    '/pages/chatbot.html',
    '/images/gipslogo.jpg',
    '/favicon/favicon.ico',
    '/favicon/favicon-16x16.png',
    '/favicon/favicon-32x32.png',
    '/favicon/apple-touch-icon.png',
    '/favicon/site.webmanifest',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
            .catch(() => caches.match('/index.html'))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
        ))
    );
    self.clients.claim();
});