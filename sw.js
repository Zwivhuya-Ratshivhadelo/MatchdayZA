/* No longer used: removes itself from browsers that registered it earlier. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.registration.unregister());
