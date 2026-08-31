/**
 * Cloud Functions for Cheer Tumbling Roadmap
 * Stripe subscription integration
 *
 * Functions:
 *   - createCheckoutSession : クライアントからサブスク開始（Stripe Checkoutへ遷移）
 *   - createPortalLink      : 顧客ポータル（プラン変更・解約・支払方法変更）を発行
 *   - stripeWebhook         : Stripeイベント受信 → Firestore users/{uid}.plan を同期
 *
 * Environment secrets (set via `firebase functions:secrets:set`):
 *   - STRIPE_SECRET_KEY     : Stripe シークレットキー（sk_test_... or sk_live_...）
 *   - STRIPE_WEBHOOK_SECRET : Stripe Webhook 署名検証用シークレット（whsec_...）
 *
 * Plan名の対応（Stripe商品metadataの `firebasePlan` で指定）:
 *   individual        : ¥480 個人プラン
 *   coach             : ¥1,200 コーチプラン
 *   coach_plus        : ¥1,980 コーチプラスプラン
 *   training_light    : ¥4,500 トレーニング指導プラン
 *   training_1on1     : ¥19,800 完全1on1プラン（2026-08-31 改定。旧価格 ¥7,500 の既存契約者はそのまま継続）
 */

const { onCall, onRequest, HttpsError } = require('firebase-functions/v2/https');
const { setGlobalOptions } = require('firebase-functions/v2');
const { defineSecret } = require('firebase-functions/params');
const { initializeApp } = require('firebase-admin/app');
const { getFirestore, FieldValue, Timestamp } = require('firebase-admin/firestore');

// ─────────────────────────────────────────────
// 初期化
// ─────────────────────────────────────────────
initializeApp();
const db = getFirestore();

// 日本ユーザー向け：東京リージョン固定
setGlobalOptions({ region: 'asia-northeast1', maxInstances: 10 });

const STRIPE_SECRET_KEY = defineSecret('STRIPE_SECRET_KEY');
const STRIPE_WEBHOOK_SECRET = defineSecret('STRIPE_WEBHOOK_SECRET');

// 運営あて申込通知メールの送信元（Gmail アプリパスワードを使う）
// 未設定のまま deploy するとエラーになるため、空文字でもよいので必ず set すること：
//   firebase functions:secrets:set NOTIFY_EMAIL_USER
//   firebase functions:secrets:set NOTIFY_EMAIL_PASS
// 空文字を入れた場合、メール送信はスキップされ Firestore への記録のみ行われる。
const NOTIFY_EMAIL_USER = defineSecret('NOTIFY_EMAIL_USER');
const NOTIFY_EMAIL_PASS = defineSecret('NOTIFY_EMAIL_PASS');

// リダイレクト先の既定URL（本番ドメイン）
const DEFAULT_ORIGIN = 'https://roadmap.cheer-tumbling.jp';

// 申込があったら運営に通知するプラン
// ここに planKey を足せば他プランも通知対象になる
const NOTIFY_ON_NEW_SUBSCRIPTION_PLANS = ['training_1on1'];

// 通知メールの宛先（運営窓口）
const ADMIN_NOTIFY_TO = 'cheer.tumbling.association@gmail.com';

// プラン表示名（通知メール用）
const PLAN_LABELS = {
  individual: '個人プレミアム',
  coach: 'コーチプラン',
  coach_plus: 'コーチプラス',
  training_light: 'トレーニング指導',
  training_1on1: '完全1on1'
};

// ─────────────────────────────────────────────
// ヘルパー
// ─────────────────────────────────────────────
function getStripe(secretKey) {
  // eslint-disable-next-line global-require
  return require('stripe')(secretKey);
}

/**
 * Firebase UID から Stripe Customer を取得。無ければ作成して users/{uid} に保存
 */
async function getOrCreateStripeCustomer(uid, email, displayName, stripe) {
  const userRef = db.collection('users').doc(uid);
  const snap = await userRef.get();
  const data = snap.exists ? snap.data() : {};

  if (data.stripeCustomerId) {
    return data.stripeCustomerId;
  }

  const customer = await stripe.customers.create({
    email: email || undefined,
    name: displayName || undefined,
    metadata: { firebaseUid: uid }
  });

  await userRef.set(
    {
      stripeCustomerId: customer.id,
      stripeUpdatedAt: FieldValue.serverTimestamp()
    },
    { merge: true }
  );

  return customer.id;
}

/**
 * Stripe Customer ID から Firebase UID を逆引き
 * まずメタデータヒント（webhook payload の firebaseUid）を試し、次に Firestore クエリ
 */
async function findUidByStripeCustomerId(customerId, hintUid) {
  if (hintUid) {
    const doc = await db.collection('users').doc(hintUid).get();
    if (doc.exists && doc.data().stripeCustomerId === customerId) {
      return hintUid;
    }
  }
  const snap = await db
    .collection('users')
    .where('stripeCustomerId', '==', customerId)
    .limit(1)
    .get();
  return snap.empty ? null : snap.docs[0].id;
}

/**
 * Stripe Price から 内部プラン名を導出
 * 優先順：product.metadata.firebasePlan → price.metadata.firebasePlan → 'premium'（フォールバック）
 */
async function resolvePlanName(priceId, stripe) {
  const price = await stripe.prices.retrieve(priceId, { expand: ['product'] });
  const fromProduct = price.product?.metadata?.firebasePlan;
  const fromPrice = price.metadata?.firebasePlan;
  return fromProduct || fromPrice || 'premium';
}

// ─────────────────────────────────────────────
// createCheckoutSession
// クライアントが「このプランに申込」ボタンを押した時に呼ぶ
// 返り値の url へリダイレクトすると Stripe Checkout が開く
// ─────────────────────────────────────────────
exports.createCheckoutSession = onCall(
  { secrets: [STRIPE_SECRET_KEY] },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError('unauthenticated', 'サインインが必要です');
    }
    const { priceId, successUrl, cancelUrl } = request.data || {};
    if (!priceId || typeof priceId !== 'string') {
      throw new HttpsError('invalid-argument', 'priceId が必要です');
    }

    const stripe = getStripe(STRIPE_SECRET_KEY.value());
    const uid = request.auth.uid;
    const email = request.auth.token.email;
    const displayName = request.auth.token.name;

    const customerId = await getOrCreateStripeCustomer(uid, email, displayName, stripe);

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url:
        successUrl ||
        `${DEFAULT_ORIGIN}/?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl || `${DEFAULT_ORIGIN}/?checkout=cancel`,
      allow_promotion_codes: true,
      billing_address_collection: 'auto',
      client_reference_id: uid,
      subscription_data: {
        metadata: { firebaseUid: uid }
      },
      metadata: { firebaseUid: uid },
      locale: 'ja'
    });

    return { url: session.url, sessionId: session.id };
  }
);

// ─────────────────────────────────────────────
// createPortalLink
// マイページ「サブスクを管理」ボタンで呼ぶ
// 返り値の url へ遷移すると Stripe Customer Portal（プラン変更・解約・領収書等）が開く
// ─────────────────────────────────────────────
exports.createPortalLink = onCall(
  { secrets: [STRIPE_SECRET_KEY] },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError('unauthenticated', 'サインインが必要です');
    }
    const { returnUrl } = request.data || {};

    const stripe = getStripe(STRIPE_SECRET_KEY.value());
    const uid = request.auth.uid;

    const userSnap = await db.collection('users').doc(uid).get();
    const customerId = userSnap.data()?.stripeCustomerId;

    if (!customerId) {
      throw new HttpsError(
        'failed-precondition',
        'Stripeカスタマー未作成です。まずプランに申込してください'
      );
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: returnUrl || `${DEFAULT_ORIGIN}/me.html`,
      locale: 'ja'
    });

    return { url: session.url };
  }
);

// ─────────────────────────────────────────────
// stripeWebhook
// Stripe → Firebase への通知受信口
// concurrency=1 で同時実行を制限（同ユーザーの同時イベント競合を避けるため）
// ─────────────────────────────────────────────
exports.stripeWebhook = onRequest(
  {
    secrets: [
      STRIPE_SECRET_KEY,
      STRIPE_WEBHOOK_SECRET,
      NOTIFY_EMAIL_USER,
      NOTIFY_EMAIL_PASS
    ],
    concurrency: 1,
    maxInstances: 3
  },
  async (req, res) => {
    if (req.method !== 'POST') {
      res.status(405).send({ error: 'Method not allowed' });
      return;
    }

    const stripe = getStripe(STRIPE_SECRET_KEY.value());
    const sig = req.headers['stripe-signature'];

    let event;
    try {
      event = stripe.webhooks.constructEvent(
        req.rawBody,
        sig,
        STRIPE_WEBHOOK_SECRET.value()
      );
    } catch (err) {
      console.error('Webhook signature verification failed:', err.message);
      res.status(400).send(`Webhook Error: ${err.message}`);
      return;
    }

    try {
      await handleStripeEvent(event, stripe);
      res.status(200).send({ received: true, type: event.type });
    } catch (err) {
      console.error('Event handler error:', event.type, err);
      // 500 を返すと Stripe がリトライする（Stripeの標準動作）
      res.status(500).send({ error: err.message });
    }
  }
);

// ─────────────────────────────────────────────
// Stripe イベントハンドラ
// ─────────────────────────────────────────────
async function handleStripeEvent(event, stripe) {
  console.log('Stripe event:', event.type, event.id);

  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated':
      await syncSubscriptionToFirestore(event.data.object, stripe);
      break;

    case 'customer.subscription.deleted':
      await handleSubscriptionDeleted(event.data.object);
      break;

    case 'invoice.payment_succeeded':
      // サブスクの状態は subscription イベントで管理するので、ここではログのみ
      console.log('Payment succeeded for invoice:', event.data.object.id);
      break;

    case 'invoice.payment_failed':
      await handlePaymentFailed(event.data.object);
      break;

    case 'checkout.session.completed':
      // Checkout 完了時のロギング用（実際の状態遷移は subscription.created で行う）
      console.log('Checkout completed:', event.data.object.id);
      break;

    default:
      console.log('Unhandled event type:', event.type);
  }
}

/**
 * Subscription の状態を Firestore users/{uid} に反映
 */
async function syncSubscriptionToFirestore(subscription, stripe) {
  const customerId = subscription.customer;
  const hintUid = subscription.metadata?.firebaseUid;
  const uid = await findUidByStripeCustomerId(customerId, hintUid);

  if (!uid) {
    console.warn('No Firebase user found for customer:', customerId);
    return;
  }

  const priceId = subscription.items?.data?.[0]?.price?.id;
  if (!priceId) {
    console.warn('No priceId on subscription:', subscription.id);
    return;
  }

  const planName = await resolvePlanName(priceId, stripe);
  const status = subscription.status; // active, trialing, past_due, canceled, unpaid, incomplete, incomplete_expired
  const isActive = ['active', 'trialing'].includes(status);
  const isTerminal = ['canceled', 'unpaid', 'incomplete_expired'].includes(status);

  const update = {
    stripeSubscriptionId: subscription.id,
    stripeSubscriptionStatus: status,
    stripePriceId: priceId,
    stripeCancelAtPeriodEnd: subscription.cancel_at_period_end || false,
    stripeUpdatedAt: FieldValue.serverTimestamp()
  };

  if (subscription.current_period_end) {
    update.stripeCurrentPeriodEnd = Timestamp.fromMillis(
      subscription.current_period_end * 1000
    );
  }

  if (isActive) {
    update.plan = planName;
  } else if (isTerminal) {
    update.plan = 'free';
  }
  // past_due や incomplete の場合はプランを変えず、ステータスだけ更新

  await db.collection('users').doc(uid).set(update, { merge: true });
  console.log(
    `Synced subscription ${subscription.id} (${status}) to user ${uid} → plan: ${update.plan || 'unchanged'}`
  );

  // 有効化されたタイミングで運営に申込通知を出す。
  // created ではなく「初めて active/trialing になったとき」を条件にしているのは、
  // subscription.created が status=incomplete（決済確定前）で飛ぶことがあり、
  // 決済が失敗した申込まで通知してしまうため。
  if (isActive) {
    await notifyAdminNewSubscription({ uid, planName, subscription });
  }
}

/**
 * 個別指導プランの申込を運営に通知する
 *
 * - Firestore admin_notifications/{subscriptionId} に記録（申込台帳）
 * - 運営あてにメール送信（NOTIFY_EMAIL_USER/PASS が設定されている場合のみ）
 *
 * ドキュメントIDに subscriptionId を使い create() で作るため、
 * subscription.updated が何度飛んでも通知は1回だけになる。
 */
async function notifyAdminNewSubscription({ uid, planName, subscription }) {
  if (!NOTIFY_ON_NEW_SUBSCRIPTION_PLANS.includes(planName)) return;

  const notifRef = db.collection('admin_notifications').doc(subscription.id);

  // 申込者情報（メール本文に載せる）
  let userInfo = {};
  try {
    const snap = await db.collection('users').doc(uid).get();
    const d = snap.data() || {};
    userInfo = {
      email: d.email || null,
      displayName: d.displayName || null,
      role: d.role || null,
      teamName: d.teamName || null
    };
  } catch (err) {
    console.warn('Failed to load user info for notification:', err.message);
  }

  const planLabel = PLAN_LABELS[planName] || planName;

  try {
    await notifRef.create({
      type: 'new_subscription',
      plan: planName,
      planLabel,
      uid,
      ...userInfo,
      stripeSubscriptionId: subscription.id,
      stripeCustomerId: subscription.customer,
      status: subscription.status,
      createdAt: FieldValue.serverTimestamp(),
      handled: false,
      emailSent: false
    });
  } catch (err) {
    // code 6 = ALREADY_EXISTS（同じサブスクで既に通知済み）
    if (err.code === 6) {
      console.log('Admin notification already sent for', subscription.id);
      return;
    }
    throw err;
  }

  // ログにも必ず残す（メール設定がなくても Cloud Functions のログから追える）
  console.log(
    `[ADMIN_NOTIFY] 新規申込 ${planLabel} / uid=${uid} / email=${userInfo.email || '不明'} / sub=${subscription.id}`
  );

  const sent = await sendAdminNotifyMail({ planLabel, uid, userInfo, subscription });
  await notifRef.set(
    { emailSent: sent.ok, emailError: sent.error || null },
    { merge: true }
  );
}

/**
 * 運営あて通知メールを送る。失敗しても例外は投げない。
 *
 * webhook の中から呼ぶため、ここで throw すると Stripe に 500 を返してしまい
 * 「メールが送れないだけ」でリトライが延々と続く。そのため必ず握りつぶし、
 * 成否は admin_notifications ドキュメントの emailSent に記録する。
 */
async function sendAdminNotifyMail({ planLabel, uid, userInfo, subscription }) {
  const user = (NOTIFY_EMAIL_USER.value() || '').trim();
  const pass = (NOTIFY_EMAIL_PASS.value() || '').trim();

  // メール通知を使わない場合は NOTIFY_EMAIL_USER に "-" 等を入れておけばよい。
  // （Secret Manager は空文字を受け付けないことがあるため、@ の有無で判定する）
  if (!user.includes('@') || !pass) {
    console.log('NOTIFY_EMAIL_USER/PASS 未設定のためメール送信はスキップしました');
    return { ok: false, error: 'mail_not_configured' };
  }

  try {
    // eslint-disable-next-line global-require
    const nodemailer = require('nodemailer');
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: { user, pass }
    });

    const lines = [
      `${planLabel} プランの新規申込が入りました。`,
      '',
      `申込者　： ${userInfo.displayName || '（名前未設定）'}`,
      `メール　： ${userInfo.email || '（未取得）'}`,
      `チーム　： ${userInfo.teamName || '（未設定）'}`,
      `区分　　： ${userInfo.role || '（未設定）'}`,
      '',
      `Firebase UID　　： ${uid}`,
      `Stripe Subscription： ${subscription.id}`,
      `Stripe Customer　 ： ${subscription.customer}`,
      `ステータス　　　　： ${subscription.status}`,
      '',
      '── 対応が必要なこと ──',
      '① 専用LINEを用意して申込者に案内する',
      '② 初回ビデオ通話（30分）の日程を調整する',
      '③ 個別メニューを作成する',
      '',
      `Stripe管理画面： https://dashboard.stripe.com/subscriptions/${subscription.id}`,
      `Firebase　　　： https://console.firebase.google.com/project/cheer-tumbling-roadmap/firestore/data/~2Fusers~2F${uid}`
    ];

    await transporter.sendMail({
      from: `チアタンブリング ロードマップ <${user}>`,
      to: ADMIN_NOTIFY_TO,
      subject: `【申込】${planLabel} — ${userInfo.displayName || userInfo.email || uid}`,
      text: lines.join('\n')
    });

    console.log('Admin notification mail sent for', subscription.id);
    return { ok: true };
  } catch (err) {
    console.error('Admin notification mail failed:', err.message);
    return { ok: false, error: err.message };
  }
}

/**
 * サブスク完全削除時（Customer Portal から即時解約 or 期限切れ）
 */
async function handleSubscriptionDeleted(subscription) {
  const customerId = subscription.customer;
  const hintUid = subscription.metadata?.firebaseUid;
  const uid = await findUidByStripeCustomerId(customerId, hintUid);
  if (!uid) return;

  await db.collection('users').doc(uid).set(
    {
      plan: 'free',
      stripeSubscriptionId: null,
      stripeSubscriptionStatus: 'canceled',
      stripeCancelledAt: FieldValue.serverTimestamp(),
      stripeUpdatedAt: FieldValue.serverTimestamp()
    },
    { merge: true }
  );
  console.log(`Subscription deleted for user ${uid}`);
}

/**
 * 支払失敗時（カード期限切れ等）
 * Stripeが自動リトライ（3〜4回）するのでプランはまだ落とさない
 */
async function handlePaymentFailed(invoice) {
  const customerId = invoice.customer;
  const uid = await findUidByStripeCustomerId(customerId);
  if (!uid) return;

  await db.collection('users').doc(uid).set(
    {
      stripePaymentFailedAt: FieldValue.serverTimestamp(),
      stripePaymentFailedCount: FieldValue.increment(1),
      stripeUpdatedAt: FieldValue.serverTimestamp()
    },
    { merge: true }
  );
  console.log(`Payment failed for user ${uid}, invoice ${invoice.id}`);
}
