/* PetaPhoto service worker.
 * - Precaches the app shell (index.html, u2netp.js, manifest, icons) into CACHE.
 * - Same-origin navigations: network-first (revalidated), refreshing the cached index.html; offline falls back to it.
 * - Other same-origin GETs: cache-first, network fallback (and cached on success).
 * - Google Fonts / jsDelivr (onnxruntime-web): stale-while-revalidate in RT_CACHE.
 * - Hugging Face (RMBG model, stored in IndexedDB by the app) and Supabase are never touched.
 * - A new version waits until the page posts {type:'skipWaiting'} (after its "update available" toast).
 */
'use strict';
const CACHE = 'petaphoto-v35';
const RT_CACHE = 'petaphoto-rt-v35';
const PRECACHE = ['./', 'index.html', 'u2netp.js', 'manifest.webmanifest',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png'];
const RT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.jsdelivr.net'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE.map(u => new Request(u, { cache: 'reload' })))));
});

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('petaphoto-') && k !== CACHE && k !== RT_CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function skipHost(h) {
  return h === 'huggingface.co' || h.endsWith('.huggingface.co') || h === 'hf.co' || h.endsWith('.hf.co') ||
    /^cdn-lfs.*\.huggingface\.co$/.test(h) || h.endsWith('.supabase.co');
}

async function networkFirstNav(req) {
  try {
    const res = await fetch(req, { cache: 'no-cache' });
    // keep the offline copy in step with the page the user last saw online
    if (res && res.ok && res.type === 'basic') { const copy = res.clone(); caches.open(CACHE).then(c => c.put('index.html', copy)).catch(() => {}); }
    return res;
  } catch (err) {
    const c = await caches.open(CACHE);
    const hit = await c.match('index.html') || await c.match('./');
    if (hit) return hit;
    throw err;
  }
}

async function cacheFirst(req) {
  const c = await caches.open(CACHE);
  const hit = await c.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res && res.ok && res.type === 'basic') c.put(req, res.clone()).catch(() => {});
  return res;
}

async function staleWhileRevalidate(e) {
  const req = e.request;
  const c = await caches.open(RT_CACHE);
  const hit = await c.match(req);
  const net = fetch(req).then(res => {
    if (res && (res.ok || res.type === 'opaque')) c.put(req, res.clone()).catch(() => {});
    return res;
  });
  if (hit) {
    e.waitUntil(net.catch(() => {}));
    return hit;
  }
  return net;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (_) { return; }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
  if (skipHost(url.hostname)) return;

  let p = null;
  if (url.origin === self.location.origin) {
    p = req.mode === 'navigate' ? networkFirstNav(req) : cacheFirst(req);
  } else if (RT_HOSTS.includes(url.hostname)) {
    p = staleWhileRevalidate(e);
  } else {
    return;
  }
  e.respondWith(p.catch(() => fetch(req)));
});
