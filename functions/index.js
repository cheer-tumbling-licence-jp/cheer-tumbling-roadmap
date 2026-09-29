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
const { onDocumentCreated } = require('firebase-functions/v2/firestore');
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

// 標準 Web Push（VAPID）の秘密鍵。FCM ではなく web-push ライブラリで使う。
const VAPID_PRIVATE_KEY = defineSecret('VAPID_PRIVATE_KEY');

// リダイレクト先の既定URL（本番ドメイン）
const DEFAULT_ORIGIN = 'https://roadmap.cheer-tumbling.jp';

// 申込があったら運営に通知するプラン
// ここに planKey を足せば他プランも通知対象になる
const NOTIFY_ON_NEW_SUBSCRIPTION_PLANS = ['training_1on1'];

// 通知メールの宛先（運営窓口）
const ADMIN_NOTIFY_TO = 'cheer.tumbling.association@gmail.com';

// コーチへの提出通知メールの最短間隔（分）
// 選手が続けて提出するとメールが連発するため、この間隔で1通にまとめる
const COACH_NOTIFY_INTERVAL_MIN = 30;

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
 * メールを1通送る。失敗しても例外は投げない（呼び出し元の処理を止めないため）。
 * NOTIFY_EMAIL_USER / NOTIFY_EMAIL_PASS が未設定なら送信をスキップする。
 */
async function sendMail({ to, subject, text }) {
  const user = (NOTIFY_EMAIL_USER.value() || '').trim();
  const pass = (NOTIFY_EMAIL_PASS.value() || '').trim();

  if (!user || !pass) {
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
    await transporter.sendMail({
      from: `チアタンブリング ロードマップ <${user}>`,
      to,
      subject,
      text
    });
    console.log('メール送信:', subject, '→', to);
    return { ok: true };
  } catch (err) {
    console.error('メール送信に失敗:', err.message);
    return { ok: false, error: err.message };
  }
}

// ─────────────────────────────────────────────
// 選手が課題を提出したらコーチにメールで知らせる
//   submissions/{id} が新規作成されたときだけ動く。
//   （毎日の課題は日付入りIDなので、日ごとに1回発火する）
//   users/{coachId}.emailNotify === false のコーチには送らない。
//   30分に1通までにまとめ、連続提出でメールが溢れないようにする。
// ─────────────────────────────────────────────
exports.notifyCoachOnSubmission = onDocumentCreated(
  {
    document: 'submissions/{submissionId}',
    secrets: [NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS, VAPID_PRIVATE_KEY]
  },
  async (event) => {
    const sub = event.data && event.data.data();
    if (!sub) return;

    const coachId = sub.coachId;
    if (!coachId) {
      console.log('submission に coachId が無いため通知しません:', event.params.submissionId);
      return;
    }

    const coachRef = db.collection('users').doc(coachId);
    const coachSnap = await coachRef.get();
    if (!coachSnap.exists) {
      console.log('コーチが見つかりません:', coachId);
      return;
    }
    const coach = coachSnap.data();

    const student = sub.studentName || '選手';
    const item = sub.itemName || '課題';

    // ============ Web Push 通知（アプリが閉じていてもアイコンにバッジ更新） ============
    // メールとは独立して即時送信する（30分制限なし）
    try {
      const subs = await loadSubscriptions(coachId);
      if (subs.length > 0) {
        // 過去 30 日以内の提出数をバッジに出す
        const monthAgoIso = new Date(Date.now() - 30 * 86400000).toISOString();
        const asnapAll = await db.collection('assignments').where('coachId', '==', coachId).get();
        const aids = asnapAll.docs.map(d => d.id);
        let unreadCount = 0;
        for (let i = 0; i < aids.length; i += 10) {
          const batch = aids.slice(i, i + 10);
          if (batch.length === 0) continue;
          const ssnap = await db.collection('submissions').where('assignmentId', 'in', batch).get();
          ssnap.forEach(d => {
            const dat = d.data();
            let iso = dat.submittedAt || dat.createdAt;
            if (iso && typeof iso.toDate === 'function') iso = iso.toDate().toISOString();
            if (iso && iso > monthAgoIso) unreadCount++;
          });
        }
        const result = await sendWebPush(subs, {
          title: '🎀 新着提出',
          body: `${student} さんが「${item}」を提出しました`,
          clickUrl: '/coach.html',
          badgeCount: String(unreadCount)
        });
        console.log(`[WebPush] 提出通知: 成功 ${result.sent} / 失敗 ${result.failed}`);
        if (result.errors.length) console.log('[WebPush] errors:', result.errors.join(' | '));
      } else {
        console.log('[WebPush] コーチに購読が無いため Push スキップ:', coachId);
      }
    } catch (e) {
      console.error('[WebPush] 提出通知エラー:', e);
    }

    // ============ メール通知（30分ごとにまとめて送信） ============
    if (coach.emailNotify === false) {
      console.log('コーチがメール通知をオフにしています:', coachId);
      return;
    }
    if (!coach.email) {
      console.log('コーチのメールアドレスが未登録です:', coachId);
      return;
    }

    // 30分以内に送っていれば今回は送らない（アプリ内バッジで拾える）
    const last = coach.coachNotifiedAt;
    if (last && typeof last.toMillis === 'function') {
      const mins = (Date.now() - last.toMillis()) / 60000;
      if (mins < COACH_NOTIFY_INTERVAL_MIN) {
        console.log(`前回のメール通知から ${Math.round(mins)} 分のためメール送信を見送りました（Pushは送信済み）`);
        return;
      }
    }

    const lines = [
      `${student} さんが「${item}」を提出しました。`,
      '',
      'アプリで動画とコメントを確認できます。',
      'https://roadmap.cheer-tumbling.jp/coach.html',
      '',
      '──────────',
      `※ このあと ${COACH_NOTIFY_INTERVAL_MIN} 分間に届いた提出は、このメールにまとめています。`,
      '　 アプリを開くと件数が表示されます。',
      '',
      '※ 通知を止めたいときは、アプリのメニューから「提出のメール通知」をオフにしてください。'
    ];

    const sent = await sendMail({
      to: coach.email,
      subject: `【提出】${student} さん — ${item}`,
      text: lines.join('\n')
    });

    if (sent.ok) {
      await coachRef.set(
        { coachNotifiedAt: FieldValue.serverTimestamp() },
        { merge: true }
      );
    }
  }
);

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







// ═════════════════════════════════════════════
// 標準 Web Push（VAPID / web-push ライブラリ）
//
// FCM をやめて標準 Web Push に切り替えた理由：
//   iOS Safari は「通知を表示しない push」を検出すると購読を強制解除する。
//   Firebase の messaging SW はフォアグラウンド時・データのみ送信時に
//   通知を出さない経路があり、iOS で数回のうちに購読が切れる
//   （firebase-js-sdk #8010・2024-02 report / 未修正）。
//   自前の push-sw.js なら必ず showNotification() を呼べるので iOS で安定する。
// ═════════════════════════════════════════════

const VAPID_PUBLIC_KEY = 'BF1KQaAd9sKkdVW2JxiGyHZJsyYlbAr4kxH0jpwYgsZEgeRN0XDCKWljgxx1XL5MMXogS5QLO5EetuxKKAsNZdA';
const VAPID_SUBJECT = 'mailto:cheer.tumbling.association@gmail.com';

function initWebPush() {
  // eslint-disable-next-line global-require
  const webpush = require('web-push');
  // Secret Manager に改行や空白が混ざることがあるので必ず trim する
  // （混ざっていると "Vapid private key must be a URL safe Base 64" で落ちる）
  const priv = (VAPID_PRIVATE_KEY.value() || '').trim();
  webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC_KEY.trim(), priv);
  return webpush;
}

/** endpoint URL から Firestore のドキュメント ID を作る（記号を除去） */
function subDocId(endpoint) {
  return Buffer.from(endpoint).toString('base64').replace(/[^A-Za-z0-9]/g, '').slice(0, 200);
}

/**
 * 指定した購読リストへ通知を送る。失効したものは自動で削除する。
 * @returns {{sent:number, failed:number, errors:string[]}}
 */
async function sendWebPush(subscriptions, payload) {
  if (!subscriptions.length) return { sent: 0, failed: 0, errors: [] };
  const webpush = initWebPush();
  const body = JSON.stringify(payload);
  let sent = 0, failed = 0;
  const errors = [];
  const dead = [];

  await Promise.all(subscriptions.map(async (item) => {
    try {
      await webpush.sendNotification(item.subscription, body, { TTL: 3600, urgency: 'high' });
      sent++;
    } catch (e) {
      failed++;
      errors.push((e.statusCode || '') + ' ' + (e.body || e.message || ''));
      // 404/410 は購読が失効している → 削除
      if (e.statusCode === 404 || e.statusCode === 410) dead.push(item.docId);
    }
  }));

  for (const id of dead) {
    await db.collection('pushSubscriptions').doc(id).delete().catch(() => {});
  }
  if (dead.length) console.log(`[WebPush] 失効した購読を ${dead.length} 件削除`);
  return { sent, failed, errors };
}

/** Firestore から購読を読み出す。uid 指定があればその人のものだけ。 */
async function loadSubscriptions(uid) {
  let q = db.collection('pushSubscriptions');
  if (uid) q = q.where('uid', '==', uid);
  const snap = await q.get();
  const out = [];
  snap.forEach(d => {
    const x = d.data();
    if (x.subscription && x.subscription.endpoint) {
      out.push({ docId: d.id, subscription: x.subscription, uid: x.uid || null, email: x.email || null });
    }
  });
  return out;
}

// ─── 購読を保存（認証必須） ───
// onCall にすることで Firebase が ID トークンを検証してくれる。
// uid をリクエストから受け取ると他人になりすませてしまうため、
// 必ず request.auth.uid（検証済み）を使う。
exports.savePushSubscription = onCall(async (request) => {
  if (!request.auth) throw new HttpsError('unauthenticated', 'ログインが必要です');
  const { subscription, ua, isPWA } = request.data || {};
  if (!subscription || !subscription.endpoint) {
    throw new HttpsError('invalid-argument', 'subscription がありません');
  }
  const uid = request.auth.uid;
  const email = request.auth.token.email || null;
  const id = subDocId(subscription.endpoint);
  await db.collection('pushSubscriptions').doc(id).set({
    subscription,
    uid,
    email,
    ua: ua || null,
    isPWA: !!isPWA,
    updatedAt: FieldValue.serverTimestamp()
  }, { merge: true });
  console.log('[WebPush] 購読を保存:', email || uid);
  return { ok: true, id };
});

// ─── SW からの再購読用（認証なしで呼ばれる）───
// pushsubscriptionchange は SW 内で起きるため ID トークンを付けられない。
// endpoint が既存の購読と一致する場合だけ、その uid を引き継いで更新する。
// 新規作成はしないので、他人の uid で購読を作ることはできない。
exports.renewPushSubscription = onRequest({ cors: true }, async (req, res) => {
  if (req.method === 'OPTIONS') { res.status(204).send(''); return; }
  try {
    const { subscription, oldEndpoint } = req.body || {};
    if (!subscription || !subscription.endpoint) {
      res.status(400).json({ ok: false, error: 'subscription がありません' }); return;
    }
    // 旧 endpoint の購読を探して uid を引き継ぐ
    let uid = null, email = null;
    if (oldEndpoint) {
      const oldDoc = await db.collection('pushSubscriptions').doc(subDocId(oldEndpoint)).get();
      if (oldDoc.exists) {
        uid = oldDoc.data().uid || null;
        email = oldDoc.data().email || null;
        await oldDoc.ref.delete().catch(() => {});
      }
    }
    if (!uid) {
      // 持ち主が分からない購読は保存しない（誰宛てか決められないため）
      res.status(200).json({ ok: false, error: '元の購読が見つかりません' }); return;
    }
    await db.collection('pushSubscriptions').doc(subDocId(subscription.endpoint)).set({
      subscription, uid, email,
      ua: 'pushsubscriptionchange',
      isPWA: true,
      updatedAt: FieldValue.serverTimestamp()
    }, { merge: true });
    console.log('[WebPush] 購読を更新（再購読）:', email || uid);
    res.status(200).json({ ok: true });
  } catch (e) {
    console.error('[WebPush] 再購読エラー:', e);
    res.status(500).json({ ok: false, error: e.message });
  }
});

// ─── テスト送信（自分の端末にだけ送る・認証必須） ───
exports.sendTestPush = onCall({ secrets: [VAPID_PRIVATE_KEY] }, async (request) => {
  if (!request.auth) throw new HttpsError('unauthenticated', 'ログインが必要です');
  // uid はリクエストから受け取らず、必ず認証済みの自分自身にだけ送る
  const uid = request.auth.uid;
  const subs = await loadSubscriptions(uid);
  if (!subs.length) {
    return { sent: 0, failed: 0, error: '購読が登録されていません。先に「通知をオンにする」を押してください' };
  }
  const result = await sendWebPush(subs, {
    title: '🎀 テスト通知',
    body: 'これが見えたら Push は成功です！',
    clickUrl: '/coach.html',
    badgeCount: '3'
  });
  console.log('[WebPush] テスト送信:', JSON.stringify(result));
  return { ...result, targets: subs.length };
});



