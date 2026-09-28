/*
 * 【廃止】Push 専用 Service Worker
 *
 * SW のレジストレーションは (オリジン, スコープ) で一意なので、
 * このファイルと service-worker.js を同じスコープ '/' で登録すると
 * 後から register した方が前の方を置き換えてしまう。
 *   ・このファイルが勝つ  → fetch ハンドラが無くなりオフラインキャッシュが死ぬ
 *   ・service-worker.js が勝つ → push ハンドラが無くなり通知が出ない
 *                            → iOS が購読を強制解除する
 * そのため push 処理は service-worker.js に統合し、SW は1本だけにした。
 *
 * 既にこのファイルを登録済みの端末があるので、ファイル自体は残しつつ
 * 自分を登録解除して service-worker.js に戻す。
 * （ファイルを消すと 404 になり、古い SW が残り続けてしまう）
 */

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try { await self.registration.unregister(); } catch (e) {}
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(c => c.navigate(c.url).catch(() => {}));
  })());
});
