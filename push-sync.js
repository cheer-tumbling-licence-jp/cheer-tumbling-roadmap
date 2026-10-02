/*
 * push-sync.js — 通知の宛先を「今ログインしているアカウント」に合わせる
 *
 * なぜ必要か（2026-10-02 に実際に起きた不具合）
 * ──────────────────────────────────────────────
 * Push の購読は「端末＋ブラウザ」ごとに1つしか作れない。ホーム画面の
 * アイコンも端末に1つしかない。そのため同じ端末で別アカウントに
 * ログインし直すと、
 *   ・購読は残っている（＝アプリは「通知オン」に見える）
 *   ・しかし通知は前のアカウント宛てに飛ぶ
 * という状態になり、バッジが一切付かなくなる。
 *
 * savePushSubscription は endpoint をキーに上書き保存するので、
 * ページを開くたびに呼び直せば宛先が自動で揃う。
 *
 * 購読が1つも無いときは、コーチ画面だけ案内バナーを出す
 * （window.CTA_PUSH_BANNER = true を事前に設定したページ）。
 * 選手画面では出さない。提出するのは選手、気づく必要があるのはコーチのため。
 */
(function () {
  'use strict';

  var hasPush = 'serviceWorker' in navigator && 'PushManager' in window;

  function showBanner() {
    if (document.getElementById('pushOffBanner')) return;
    var main = document.querySelector('main.container') || document.body;
    var el = document.createElement('div');
    el.id = 'pushOffBanner';
    el.style.cssText =
      'background:rgba(255,138,61,.12);border:1px solid rgba(255,138,61,.45);' +
      'border-radius:14px;padding:14px 16px;margin:0 0 16px;display:flex;' +
      'align-items:center;gap:12px;flex-wrap:wrap;font-size:13px;line-height:1.7;';
    el.innerHTML =
      '<div style="flex:1;min-width:220px;">' +
        '<div style="font-weight:800;color:#ff8a3d;margin-bottom:2px;">🔕 通知がオフです</div>' +
        '<div style="color:var(--text-dim,#a9a5c0);">' +
          '提出があってもアイコンに数字が付きません。' +
        '</div>' +
      '</div>' +
      '<a href="/register-push.html" ' +
         'style="background:linear-gradient(135deg,#ff4d8f,#a855f7);color:#fff;' +
         'text-decoration:none;font-weight:800;font-size:13px;padding:10px 16px;' +
         'border-radius:10px;white-space:nowrap;">通知をオンにする</a>';
    main.insertBefore(el, main.firstChild);
  }

  function hideBanner() {
    var el = document.getElementById('pushOffBanner');
    if (el) el.remove();
  }

  async function sync(user) {
    if (!hasPush || !user) return;
    try {
      var reg = await navigator.serviceWorker.getRegistration();
      var sub = reg ? await reg.pushManager.getSubscription() : null;

      if (!sub || (window.Notification && Notification.permission !== 'granted')) {
        if (window.CTA_PUSH_BANNER) showBanner();
        return;
      }
      hideBanner();

      // 購読はあるので、宛先を今のアカウントに揃え直す。
      // 同じ内容でも毎回呼ぶ（uid が変わったかはクライアントでは判定できないため）。
      var fn = firebase.app().functions('asia-northeast1').httpsCallable('savePushSubscription');
      await fn({
        subscription: sub.toJSON(),
        ua: navigator.userAgent,
        isPWA: window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true
      });

      // 購読が失効して SW が取り直すときに、誰の購読かを渡せるよう控える
      try {
        var cache = await caches.open('cta-push-owner');
        await cache.put('owner', new Response(JSON.stringify({
          uid: user.uid, email: user.email || null
        })));
      } catch (e) {}
    } catch (e) {
      console.warn('[push-sync] 宛先の同期に失敗:', e && e.message);
    }
  }

  // firebase.initializeApp は各ページのインラインスクリプトの中で呼ばれており、
  // 読み込み順に依存しないよう、初期化が終わるまで少し待ってから購読する。
  function start(tries) {
    tries = tries || 0;
    var ready = window.firebase && firebase.apps && firebase.apps.length > 0;
    if (!ready) {
      if (tries < 40) setTimeout(function () { start(tries + 1); }, 250);
      return;
    }
    firebase.auth().onAuthStateChanged(function (user) {
      if (user) sync(user);
      else hideBanner();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
