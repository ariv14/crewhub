// CrewHub Service Worker — lightweight, cache-first for static assets
const CACHE_NAME = "crewhub-v1";
const STATIC_ASSETS = ["/favicon.png", "/logo.svg", "/og-image.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Only cache GET requests for static assets
  if (event.request.method !== "GET") return;

  // Cache-first for static assets (images, fonts)
  if (
    url.pathname.startsWith("/favicon") ||
    url.pathname === "/logo.svg" ||
    url.pathname === "/og-image.png"
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  // Network-first for everything else (pages, API calls)
  // Don't intercept — let the browser handle normally
});
