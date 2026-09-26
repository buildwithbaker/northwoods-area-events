// Northwoods Area Events service worker.
// The page is NETWORK-FIRST: the weekly scan rewrites index.html, so a cached page is only
// ever the offline fallback, never served ahead of the network. Keep it that way (see CLAUDE.md).
// Google Fonts: cache-first. Everything else is not intercepted.
const VERSION = "nwe-v1";
const PAGE = VERSION + "-page";
const FONTS = VERSION + "-fonts";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION + "-")).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  if (req.mode === "navigate") {
    // One stored copy of the page, keyed by the scope URL, whatever query string the view has.
    const key = self.registration.scope;
    event.respondWith(
      fetch(req.url, { cache: "no-cache", credentials: "same-origin" })
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            event.waitUntil(caches.open(PAGE).then((c) => c.put(key, copy)));
          }
          return res;
        })
        .catch(() => caches.open(PAGE).then((c) => c.match(key)).then((hit) => hit || Response.error()))
    );
    return;
  }

  const host = new URL(req.url).hostname;
  if (host === "fonts.googleapis.com" || host === "fonts.gstatic.com") {
    event.respondWith(
      caches.open(FONTS).then((c) =>
        c.match(req).then((hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok || res.type === "opaque") c.put(req, res.clone());
            return res;
          })
        )
      )
    );
  }
});
