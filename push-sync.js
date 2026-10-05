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
 * 購読が1つも無いコーチには案内バナーを出す。提出するのは選手で、
 * 気づく必要があるのはコーチなので、選手には出さない。
 * （コーチかどうかは users/{uid}.role で判定する。
 *   coach.html は必ずコーチが開く画面なので window.CTA_PUSH_BANNER で先に確定させる）
 */
(function () {
  'use strict';

  var hasPush = 'serviceWorker' in navigator && 'PushManager' in window;
  var BANNER_ID = 'pushOffBanner';

  // メールが生きているかどうかで文面を変える。
  // メールで届いているのに「気づけません」と出すと、本当に危ない状態と
  // 区別が付かなくなり、やがて誰もバナーを読まなくなるため。
  function buildInner(mailOn) {
    var ttl = mailOn ? '🔔 アイコンに数字を出せます' : '⚠️ 提出に気づけません';
    var col = mailOn ? '#06d6f8' : '#ff2d55';
    var dsc = mailOn
      ? '今はメールでお知らせしています。設定すると、アプリのアイコンにも件数が出ます。'
      : 'メールもアイコンの数字も止まっています。このままでは提出に気づけません。';
    return '' +
      '<div style="flex:1;min-width:200px;">' +
        '<div style="font-weight:800;color:' + col + ';margin-bottom:2px;">' + ttl + '</div>' +
        '<div style="color:var(--text-dim,#a9a5c0);">' + dsc + '</div>' +
      '</div>' +
      '<a href="/register-push.html" ' +
         'style="background:linear-gradient(135deg,#ff4d8f,#a855f7);color:#fff;' +
         'text-decoration:none;font-weight:800;font-size:13px;padding:10px 16px;' +
         'border-radius:10px;white-space:nowrap;">設定する</a>';
  }

  function showBanner(mailOn) {
    if (document.getElementById(BANNER_ID)) return;
    var main = document.querySelector('main.container');
    var el = document.createElement('div');
    el.id = BANNER_ID;

    if (main) {
      // コーチ画面：本文の一番上に挟む
      el.style.cssText =
        'background:rgba(255,138,61,.12);border:1px solid rgba(255,138,61,.45);' +
        'border-radius:14px;padding:14px 16px;margin:0 0 16px;display:flex;' +
        'align-items:center;gap:12px;flex-wrap:wrap;font-size:13px;line-height:1.7;';
      el.innerHTML = buildInner(mailOn);
      main.insertBefore(el, main.firstChild);
      return;
    }

    // アプリ本体：画面下に固定表示（上部は更新バナーが使うので重ねない）
    el.style.cssText =
      'position:fixed;left:12px;right:12px;bottom:84px;z-index:9997;' +
      'background:rgba(40,20,10,.96);border:1px solid rgba(255,138,61,.5);' +
      'border-radius:14px;padding:12px 14px;display:flex;align-items:center;' +
      'gap:10px;flex-wrap:wrap;font-size:13px;line-height:1.6;max-width:640px;' +
      'margin:0 auto;box-shadow:0 8px 24px rgba(0,0,0,.45);' +
      '-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);';
    el.innerHTML = buildInner(mailOn) +
      '<button type="button" id="pushOffBannerClose" aria-label="閉じる" ' +
      'style="background:transparent;border:none;color:#fff;opacity:.6;' +
      'font-size:18px;cursor:pointer;padding:0 2px;line-height:1;">×</button>';
    document.body.appendChild(el);
    var close = document.getElementById('pushOffBannerClose');
    if (close) close.onclick = function () { el.remove(); };
  }

  function hideBanner() {
    var el = document.getElementById(BANNER_ID);
    if (el) el.remove();
  }

  // バナーを出す相手か（コーチだけ）と、メール通知が生きているかを一度に読む
  async function readCoachState(user) {
    var forced = window.CTA_PUSH_BANNER === true;
    try {
      if (!firebase.firestore) return { isCoach: forced, mailOn: true };
      var snap = await firebase.firestore().collection('users').doc(user.uid).get();
      var d = snap.exists ? snap.data() : {};
      return {
        isCoach: forced || d.role === 'coach',
        // emailNotify が明示的に false のときだけオフ扱い（未設定はオン）
        mailOn: d.emailNotify !== false && !!d.email
      };
    } catch (e) { return { isCoach: forced, mailOn: true }; }
  }

  async function sync(user) {
    if (!hasPush || !user) return;
    try {
      var reg = await navigator.serviceWorker.getRegistration();
      var sub = reg ? await reg.pushManager.getSubscription() : null;

      if (!sub || (window.Notification && Notification.permission !== 'granted')) {
        var st = await readCoachState(user);
        if (st.isCoach) showBanner(st.mailOn);
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
