/**
 * Stripe Checkout / Customer Portal 起動ヘルパー
 *
 * 呼び出し例:
 *   startStripeCheckout('training_light')
 *   openStripePortal()
 *
 * 依存:
 *   - Firebase App (compat 版が既に initializeApp 済みであること)
 *   - firebase.auth() が有効
 *   - firebase.functions() が利用可能（<script src="firebase-functions-compat.js"> が読み込み済み）
 *
 * プラン名 → Stripe Price ID のマッピングは Firestore の `config/stripe_prices` ドキュメントから読む。
 * 未設定の場合は window.STRIPE_PRICE_IDS を利用（開発時のフォールバック）。
 */

(function () {
  'use strict';

  // Stripe 本番環境のPrice ID（Live mode・2026-08-26 自動作成）
  // Firestore の config/stripe_prices があればそちらが優先される
  window.STRIPE_PRICE_IDS = window.STRIPE_PRICE_IDS || {
    individual:     'price_1U8hkmCD8zFCJuDi77vbC13y',  // ¥480 個人プレミアム
    coach:          'price_1U8hknCD8zFCJuDidUrDFNE4',  // ¥1,200 コーチプラン
    coach_plus:     'price_1U8hkoCD8zFCJuDi7O2GHzNU',  // ¥1,980 コーチプラス
    training_light: 'price_1U8hkpCD8zFCJuDiwAbqWWYK',  // ¥4,500 トレーニング指導
    training_1on1:  'price_1U8hkqCD8zFCJuDizIhJh8sx'   // ¥7,500 完全1on1
  };

  // Cloud Functions のリージョン（Cloud Functions 側と一致させる）
  const FUNCTIONS_REGION = 'asia-northeast1';

  let _priceMapCache = null;

  async function loadPriceMap() {
    if (_priceMapCache) return _priceMapCache;
    try {
      const db = firebase.firestore();
      const doc = await db.collection('config').doc('stripe_prices').get();
      if (doc.exists) {
        _priceMapCache = { ...window.STRIPE_PRICE_IDS, ...doc.data() };
        return _priceMapCache;
      }
    } catch (e) {
      console.warn('[stripe-checkout] Firestore config/stripe_prices 読込失敗、フォールバック使用:', e);
    }
    _priceMapCache = window.STRIPE_PRICE_IDS;
    return _priceMapCache;
  }

  /**
   * サブスク申込フローを開始
   * @param {string} planKey - 'individual' / 'coach' / 'coach_plus' / 'training_light' / 'training_1on1'
   * @param {object} [opts] - { successUrl, cancelUrl }
   */
  async function startStripeCheckout(planKey, opts) {
    opts = opts || {};

    // 1. ログイン確認
    const user = firebase.auth().currentUser;
    if (!user) {
      const goLogin = confirm('プランに申込むにはログインが必要です。ログイン画面に移動しますか？');
      if (goLogin) {
        // 現在のページを覚えておいて、ログイン後に戻る
        try {
          sessionStorage.setItem('cta_after_login_action', JSON.stringify({
            type: 'startCheckout',
            planKey: planKey
          }));
        } catch (_) {}
        location.href = '/?signin=1';
      }
      return;
    }

    // 2. Price ID 解決
    const priceMap = await loadPriceMap();
    const priceId = priceMap[planKey];
    if (!priceId) {
      alert(
        '申込に必要な設定がまだ完了していません（Stripe 商品未登録）。\n' +
        'しばらくお待ちいただくか、運営までお問い合わせください。'
      );
      console.error('[stripe-checkout] priceId が空:', planKey, priceMap);
      return;
    }

    // 3. Cloud Function 呼出
    const btn = opts.buttonEl;
    if (btn) { btn.disabled = true; btn.dataset._origText = btn.textContent; btn.textContent = '処理中…'; }

    try {
      const functions = firebase.app().functions(FUNCTIONS_REGION);
      const createCheckoutSession = functions.httpsCallable('createCheckoutSession');
      const res = await createCheckoutSession({
        priceId: priceId,
        successUrl: opts.successUrl,
        cancelUrl: opts.cancelUrl
      });
      const url = res.data?.url;
      if (!url) throw new Error('Checkout URL が取得できませんでした');
      // Stripe Checkout へ遷移
      location.href = url;
    } catch (err) {
      console.error('[stripe-checkout] createCheckoutSession エラー:', err);
      alert('申込画面の起動に失敗しました：' + (err.message || err));
      if (btn) { btn.disabled = false; btn.textContent = btn.dataset._origText || '申し込む'; }
    }
  }

  /**
   * Stripe Customer Portal を開く（プラン変更・解約・支払方法変更）
   */
  async function openStripePortal(opts) {
    opts = opts || {};

    const user = firebase.auth().currentUser;
    if (!user) {
      alert('ログインが必要です');
      return;
    }

    const btn = opts.buttonEl;
    if (btn) { btn.disabled = true; btn.dataset._origText = btn.textContent; btn.textContent = '処理中…'; }

    try {
      const functions = firebase.app().functions(FUNCTIONS_REGION);
      const createPortalLink = functions.httpsCallable('createPortalLink');
      const res = await createPortalLink({ returnUrl: opts.returnUrl });
      const url = res.data?.url;
      if (!url) throw new Error('ポータルURLが取得できませんでした');
      location.href = url;
    } catch (err) {
      console.error('[stripe-checkout] createPortalLink エラー:', err);
      const code = err.code || '';
      if (code === 'functions/failed-precondition') {
        alert('まずサブスクプランに申込む必要があります');
      } else {
        alert('ポータル起動に失敗しました：' + (err.message || err));
      }
      if (btn) { btn.disabled = false; btn.textContent = btn.dataset._origText || 'サブスクを管理'; }
    }
  }

  /**
   * URL に ?checkout=success or ?checkout=cancel が付いていた場合の後処理
   */
  function handleCheckoutReturn() {
    const params = new URLSearchParams(location.search);
    const checkout = params.get('checkout');
    if (!checkout) return;

    if (checkout === 'success') {
      // ページ内で成功トースト表示（既存の showToast があれば利用）
      const msg = '🎉 サブスクリプションを開始しました！プラン反映まで数秒お待ちください。';
      if (typeof window.showToast === 'function') {
        window.showToast(msg, 6000);
      } else {
        alert(msg);
      }
    } else if (checkout === 'cancel') {
      const msg = '申込はキャンセルされました。いつでも再開できます。';
      if (typeof window.showToast === 'function') {
        window.showToast(msg, 4000);
      }
    }

    // URL クエリを消す（履歴汚染防止）
    try {
      const url = new URL(location.href);
      url.searchParams.delete('checkout');
      url.searchParams.delete('session_id');
      history.replaceState(null, '', url.toString());
    } catch (_) {}
  }

  /**
   * ログイン後の pending アクションを実行
   * （ログイン画面へ飛ばす前に sessionStorage に保存したアクションを復元）
   */
  async function resumePendingAction() {
    try {
      const raw = sessionStorage.getItem('cta_after_login_action');
      if (!raw) return;
      sessionStorage.removeItem('cta_after_login_action');
      const action = JSON.parse(raw);
      if (action.type === 'startCheckout' && action.planKey) {
        await startStripeCheckout(action.planKey);
      }
    } catch (_) {}
  }

  /**
   * URL に ?subscribe=<planKey> が付いていた場合、Checkoutフローを起動
   * （LP からの導線：<a href="/?subscribe=training_light">申し込む</a>）
   */
  async function handleSubscribeQuery() {
    const params = new URLSearchParams(location.search);
    const planKey = params.get('subscribe');
    if (!planKey) return;

    // URL を消してから起動（履歴汚染防止 & リロード時の二重起動防止）
    try {
      const url = new URL(location.href);
      url.searchParams.delete('subscribe');
      history.replaceState(null, '', url.toString());
    } catch (_) {}

    await startStripeCheckout(planKey);
  }

  // 公開 API
  window.startStripeCheckout = startStripeCheckout;
  window.openStripePortal = openStripePortal;
  window.handleStripeCheckoutReturn = handleCheckoutReturn;
  window.resumeStripePendingAction = resumePendingAction;

  // 自動処理：ログイン状態が確定したら
  //   1. Checkout 戻り（?checkout=success/cancel）を処理
  //   2. 保留アクション（ログイン前に押した申込ボタン）を復元
  //   3. LP からの申込リンク（?subscribe=<plan>）を起動
  let _autoRan = false;
  async function runAutoHandlers(user) {
    if (_autoRan) return;
    _autoRan = true;
    handleCheckoutReturn();
    if (user) await resumePendingAction();
    // subscribe= は未ログインでも実行（startStripeCheckout がログイン誘導する）
    await handleSubscribeQuery();
  }

  if (window.firebase && firebase.auth) {
    firebase.auth().onAuthStateChanged((user) => runAutoHandlers(user));
  } else {
    document.addEventListener('DOMContentLoaded', () => runAutoHandlers(null));
  }
})();
