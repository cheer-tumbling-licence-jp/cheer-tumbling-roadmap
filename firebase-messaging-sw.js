/*
 * 【廃止】Firebase Cloud Messaging の Service Worker
 *
 * FCM をやめて標準 Web Push（/push-sw.js）に移行したため、この SW は何もしない。
 * 理由: iOS Safari は「通知を表示しない push」を検出すると購読を強制解除する。
 *       Firebase の messaging SW はフォアグラウンド時とデータのみ送信時に
 *       通知を出さない経路があり、iOS で数回のうちに購読が切れてしまう
 *       （firebase-js-sdk #8010・2024-02 報告 / 未修正）。
 *
 * 既にこの SW を登録済みの端末があるため、ファイル自体は残しつつ
 * 自分自身を登録解除する。削除すると 404 になり古い SW が残り続けるため。
 */

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // 自分自身の登録を解除して、クライアントに新しい SW を使わせる
    try { await self.registration.unregister(); } catch (e) {}
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(c => c.navigate(c.url).catch(() => {}));
  })());
});
