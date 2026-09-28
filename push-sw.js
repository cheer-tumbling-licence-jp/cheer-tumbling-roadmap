/*
 * 標準 Web Push 用 Service Worker（FCM を使わない）
 *
 * 【なぜ FCM をやめたか】
 * iOS Safari は「通知を表示しない push」を検出すると購読を強制解除する。
 * Firebase の messaging SW は
 *   ・フォアグラウンド時 → window に postMessage して return（通知を出さない）
 *   ・データのみ送信時   → notification が無いので何も出さない
 * という経路があり、iOS で数回のうちに購読が切れる（firebase-js-sdk #8010・2024-02 から未修正）。
 *
 * この SW は push を受けたら必ず showNotification() を呼ぶ。
 * 例外が起きても catch してフォールバック通知を出すので、無通知で終わることが無い。
 */

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  // iOS の購読解除を避けるため、必ず 1 通は通知を出す
  event.waitUntil((async () => {
    let title = '🎀 チアタンブリング';
    let body = '新しいお知らせがあります';
    let clickUrl = '/';
    let badgeCount = 0;

    try {
      if (event.data) {
        const p = event.data.json();
        title = p.title || title;
        body = p.body || body;
        clickUrl = p.clickUrl || clickUrl;
        badgeCount = parseInt(p.badgeCount || '0', 10) || 0;
      }
    } catch (err) {
      // JSON でなければテキストとして扱う
      try { body = event.data ? event.data.text() : body; } catch (e2) {}
    }

    // アイコンバッジ（iOS 16.4+ / ホーム画面追加時のみ有効）
    if (badgeCount > 0 && self.navigator && self.navigator.setAppBadge) {
      try { await self.navigator.setAppBadge(badgeCount); } catch (e) {}
    }

    // ここは何があっても必ず実行する
    await self.registration.showNotification(title, {
      body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      tag: 'cta-push',
      renotify: true,
      data: { clickUrl }
    });
  })().catch(async (err) => {
    // 最後の保険：上で落ちても通知だけは出す（無通知だと iOS に購読を切られる）
    await self.registration.showNotification('🎀 チアタンブリング', {
      body: '新しいお知らせがあります',
      icon: '/icons/icon-192.png',
      data: { clickUrl: '/' }
    });
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.clickUrl) || '/';
  event.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of list) {
      if (c.url.includes(url) && 'focus' in c) return c.focus();
    }
    if (self.clients.openWindow) return self.clients.openWindow(url);
  })());
});

// 購読が期限切れ・失効したとき、自動で再購読を試みる
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil((async () => {
    try {
      const oldSub = event.oldSubscription;
      const appServerKey = oldSub && oldSub.options && oldSub.options.applicationServerKey;
      if (!appServerKey) return;
      const newSub = await self.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: appServerKey
      });
      // サーバーに新しい購読を送る
      await fetch('https://asia-northeast1-cheer-tumbling-roadmap.cloudfunctions.net/savePushSubscription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscription: newSub.toJSON(), reason: 'pushsubscriptionchange' })
      });
    } catch (e) {}
  })());
});
