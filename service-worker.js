/*
 * Cheer Tumbling Roadmap - Service Worker
 * 戦略：network-first（最新版を優先、オフラインのみキャッシュにフォールバック）
 * 設計理由：このアプリは毎日新動画やコード修正が入るため、必ず最新を取りに行く。
 *           オフライン時は最後にキャッシュした版を返す。
 */
const CACHE_VERSION = 'v15';
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

  // HTML（navigate / .html）は絶対にキャッシュから返さない。
  // GitHub Pages が HTML に max-age=600 を付けるため、SW にもキャッシュされると
  // 監督の端末で古い HTML が返り続けて新しい inline SW版チェックが起動しない
  // （2026-07-14 監督指摘対応）。オフライン時のみ最小限のキャッシュを使う。
  const isHTML = req.mode === 'navigate' ||
                 (req.destination === 'document') ||
                 url.pathname.endsWith('.html') || url.pathname === '/' ||
                 (req.headers.get('Accept') || '').includes('text/html');

  if (isHTML) {
    // HTML は必ず network 優先。キャッシュには入れない。オフライン時のみ fallback。
    event.respondWith(
      fetch(req, { cache: 'no-store' })
        .catch(() => caches.match(req).then(c => c || caches.match(SCOPE + 'index.html')))
    );
    return;
  }

  // それ以外（JS/CSS/画像/JSON）は network-first でキャッシュにも保存
  event.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE_NAME).then((cache) => {
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
