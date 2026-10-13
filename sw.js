/* MatchdayZA service worker: lets the site be added to a home screen. It caches nothing,
   so scores are always fetched fresh. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
