const CACHE_NAME = "eduvia-static-v1";
const STATIC_ASSETS = [
    "/static/css/style.css",
    "/static/manifest.json",
    "/static/icons/icon.svg"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys
                .filter((key) => key !== CACHE_NAME)
                .map((key) => caches.delete(key))
        ))
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const requestUrl = new URL(event.request.url);
    if (requestUrl.origin !== self.location.origin || event.request.method !== "GET") {
        return;
    }

    if (requestUrl.pathname.startsWith("/static/")) {
        event.respondWith(
            caches.match(event.request).then((cached) => cached || fetch(event.request))
        );
    }
});
