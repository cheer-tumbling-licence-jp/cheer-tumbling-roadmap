/*
 * Cheer Tumbling Roadmap - Service Worker
 * 戦略：network-first（最新版を優先、オフラインのみキャッシュにフォールバック）
 * 設計理由：このアプリは毎日新動画やコード修正が入るため、必ず最新を取りに行く。
 *           オフライン時は最後にキャッシュした版を返す。
 */
const CACHE_VERSION = 'v21';
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

// ═════════════════════════════════════════════
// Web Push（VAPID）— ここに統合した理由
//
// SW のレジストレーションは (オリジン, スコープ) で一意。
// push 用に別ファイルを同じスコープ '/' で register すると
// このファイルと奪い合いになり、後から register した方が勝つ。
// その結果
//   ・push-sw.js が勝つ → fetch ハンドラが消えてオフラインキャッシュが死ぬ
//   ・service-worker.js が勝つ → push ハンドラが無く通知が出ない
//     → iOS Safari は「通知を出さない push」を検出して購読を強制解除する
// という壊れ方をする。よって SW は必ずこの1本だけにする。
// ═════════════════════════════════════════════

self.addEventListener('push', (event) => {
  // iOS の購読解除を避けるため、どの経路でも必ず1通は通知を出す
  event.waitUntil((async () => {
    let title = '🎀 チアタンブリング';
    let body = '新しいお知らせがあります';
    let clickUrl = SCOPE;
    let badge = 0;

    try {
      if (event.data) {
        const p = event.data.json();
        // 宣言的プッシュ形式（web_push:8030）とも互換にしておく
        const n = p.notification || {};
        title = n.title || p.title || title;
        body = n.body || p.body || body;
        clickUrl = n.navigate || p.clickUrl || clickUrl;
        badge = Number(p.app_badge != null ? p.app_badge
                     : (n.app_badge != null ? n.app_badge : p.badgeCount)) || 0;
      }
    } catch (err) {
      try { body = event.data ? event.data.text() : body; } catch (e2) {}
    }

    // ① 通知を先に出す
    //    iOS は「通知を出さない push」を検出すると購読を強制解除するため、
    //    バッジ処理より必ず先に実行する（バッジ側で詰まっても通知は出る）。
    await self.registration.showNotification(title, {
      body,
      icon: SCOPE + 'icons/icon-192.png',
      badge: SCOPE + 'icons/icon-192.png',
      tag: 'cta-push',
      renotify: true,
      data: { clickUrl }
    });

    // ② そのあとでアイコンバッジを更新（iOS 16.4+ / ホーム画面追加時のみ）
    //    0 のときは clearAppBadge を呼ぶ。これを省くとバッジが永久に消えない。
    try {
      if (self.navigator && self.navigator.setAppBadge) {
        if (badge > 0) await self.navigator.setAppBadge(badge);
        else if (self.navigator.clearAppBadge) await self.navigator.clearAppBadge();
      }
    } catch (e) { /* 通知は出ているので握りつぶす */ }
  })().catch(async () => {
    // 最後の保険：上で落ちても通知だけは必ず出す
    await self.registration.showNotification('🎀 チアタンブリング', {
      body: '新しいお知らせがあります',
      icon: SCOPE + 'icons/icon-192.png',
      data: { clickUrl: SCOPE }
    });
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.clickUrl) || SCOPE;
  event.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of list) {
      if (c.url.includes(url) && 'focus' in c) return c.focus();
    }
    if (self.clients.openWindow) return self.clients.openWindow(url);
  })());
});

// 購読が期限切れ・失効したら自動で取り直してサーバーに再登録する
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil((async () => {
    try {
      const oldSub = event.oldSubscription;
      const key = oldSub && oldSub.options && oldSub.options.applicationServerKey;
      if (!key) return;
      const newSub = await self.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: key
      });
      // SW からは ID トークンを付けられないので専用エンドポイントを使う。
      // 旧 endpoint を渡すと、サーバーがその購読の持ち主(uid)を引き継いでくれる。
      await fetch('https://asia-northeast1-cheer-tumbling-roadmap.cloudfunctions.net/renewPushSubscription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subscription: newSub.toJSON(),
          oldEndpoint: oldSub.endpoint
        })
      });
    } catch (e) {}
  })());
});
