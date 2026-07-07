/*
 * Cheer Tumbling Roadmap - Service Worker
 * 戦略：network-first（最新版を優先、オフラインのみキャッシュにフォールバック）
 * 設計理由：このアプリは毎日新動画やコード修正が入るため、必ず最新を取りに行く。
 *           オフライン時は最後にキャッシュした版を返す。
 */
const CACHE_VERSION = 'v12';
const CACHE_NAME = `cheer-tumbling-${CACHE_VERSION}`;
const SCOPE = '/';

// インストール時にキャッシュする最低限の資産
const PRECACHE_URLS = [
  SCOPE,
  SCOPE + 'index.html',
  SCOPE + 'manifest.json',
  SCOPE + 'icons/icon-192.png',
  SCOPE + 'icons/icon-512.png',
  SCOPE + 'icons/apple-touch-icon.png',
  SCOPE + 'data/cheer_tumbling_skills.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn('precache addAll 部分失敗:', err);
      })
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// クライアントから「更新ボタン押された」通知を受けたら即座に新版に切り替える
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  // GET 以外、別オリジン、Firebase Auth/Firestore、YouTube などは触らない（素通し）
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // navigate（HTML）と同オリジンの GET だけ network-first
  event.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE_NAME).then((cache) => {
        // 成功した同オリジン GET だけキャッシュ
        if (res.ok) cache.put(req, copy).catch(() => {});
      });
      return res;
    }).catch(() =>
      caches.match(req).then((cached) =>
        cached || caches.match(SCOPE + 'index.html')
      )
    )
  );
});
