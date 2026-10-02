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
  // Secret Manager に改行や空白が混ざることがあるので必ず trim する。
  // 混ざっていると HTTP ヘッダに不正文字が入り
  // "Invalid character in header content [Authorization]" で通信自体が失敗する。
  // eslint-disable-next-line global-require
  return require('stripe')((secretKey || '').trim());
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
        (STRIPE_WEBHOOK_SECRET.value() || "").trim()
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
    let pushSent = 0;
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
        pushSent = result.sent;
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
        console.log(`前回のメール通知から ${Math.round(mins)} 分のためメール送信を見送りました`
                    + (pushSent > 0 ? '（Push は送信済み）'
                                    : '（Push も送れていません。コーチが通知未設定です）'));
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

  // iOS 18.4+ の「宣言的プッシュ」形式で送る。
  // web_push:8030 を含めると iOS は Service Worker を介さず OS 側で
  // 通知とアイコンバッジを直接描画するため、SW 起動失敗・setAppBadge の
  // silent fail といった経路をすべて回避できる。
  // app_badge の置き場所は iOS のバージョンで異なる：
  //   iOS 18.4〜18.x … notification オブジェクトの中
  //   iOS 26+        … トップレベル
  // 後方互換フォールバックが無いため両方に入れる（未知キーは無視される）。
  const badge = Number(payload.badgeCount) || 0;
  const declarative = {
    web_push: 8030,
    notification: {
      title: payload.title,
      body: payload.body,
      navigate: DEFAULT_ORIGIN + (payload.clickUrl || '/'),
      lang: 'ja',
      silent: false,
      app_badge: badge
    },
    app_badge: badge,
    // 従来形式（Chrome/Firefox・古い iOS の SW フォールバック）とも互換にする
    title: payload.title,
    body: payload.body,
    clickUrl: payload.clickUrl || '/',
    badgeCount: String(badge)
  };
  const body = JSON.stringify(declarative);
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









// ═════════════════════════════════════════════
// 自己診断（healthCheck）
//
// 「関数が存在するか」ではなく「実際に動くか」を確認する。
// 決済のように金銭が絡む処理は、画面が開くところまでではなく
// プラン反映・解約まで通しで検証しないと意味がないため。
//
// 管理者のみ実行可。壊れている項目があれば ok:false を返す。
// ═════════════════════════════════════════════
// 動作チェック・決済チェックを実行できるのはマスター1名のみ。
// cheernicpro@ は規約・LP に公開している問い合わせ用アドレスのため外した。
// index.html 側の ADMINS と必ず同じ内容にすること。
const ADMIN_EMAILS_FOR_HEALTH = ['don.stillalone.119@gmail.com'];

exports.healthCheck = onCall(
  // NOTIFY_EMAIL_* を宣言しないと .value() が undefined になり、
  // 設定済みでも「未設定」と誤表示される。必ずここに並べること。
  { secrets: [STRIPE_SECRET_KEY, VAPID_PRIVATE_KEY, NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS] },
  async (request) => {
    if (!request.auth) throw new HttpsError('unauthenticated', 'ログインが必要です');
    const email = request.auth.token.email || '';
    if (!ADMIN_EMAILS_FOR_HEALTH.includes(email)) {
      throw new HttpsError('permission-denied', '管理者のみ実行できます');
    }

    const checks = [];
    const add = (name, ok, detail) => checks.push({ name, ok, detail });

    // ── 1. Stripe に実際に接続できるか ──
    //    秘密鍵に改行が混ざると "Invalid character in header" で全決済が落ちる。
    //    実際に API を叩いて初めて分かるので、必ず通信まで行う。
    let stripe = null;
    try {
      stripe = getStripe(STRIPE_SECRET_KEY.value());
      const acct = await stripe.accounts.retrieve();
      add('Stripe接続', true, acct.id);
    } catch (e) {
      add('Stripe接続', false, e.message);
    }

    // ── 2. 5プランの価格が有効か ──
    const PRICES = {
      individual:     'price_1U8hkmCD8zFCJuDi77vbC13y',
      coach:          'price_1U8hknCD8zFCJuDidUrDFNE4',
      coach_plus:     'price_1U8hkoCD8zFCJuDi7O2GHzNU',
      training_light: 'price_1U8hkpCD8zFCJuDiwAbqWWYK',
      training_1on1:  'price_1U8hkqCD8zFCJuDizIhJh8sx'
    };
    if (stripe) {
      for (const [plan, pid] of Object.entries(PRICES)) {
        try {
          const pr = await stripe.prices.retrieve(pid, { expand: ['product'] });
          const resolved = await resolvePlanName(pid, stripe);
          const ok = pr.active && resolved === plan;
          add('価格:' + plan, ok,
              `${pr.unit_amount}円 active=${pr.active} → plan=${resolved}` +
              (resolved !== plan ? `（期待:${plan}）` : ''));
        } catch (e) {
          add('価格:' + plan, false, e.message);
        }
      }
    }

    // ── 3. 決済セッションを実際に作れるか ──
    //    ここが通らないとユーザーは購入画面にすら行けない。
    if (stripe) {
      try {
        const s = await stripe.checkout.sessions.create({
          mode: 'subscription',
          line_items: [{ price: PRICES.individual, quantity: 1 }],
          success_url: DEFAULT_ORIGIN + '/?checkout=success',
          cancel_url: DEFAULT_ORIGIN + '/?checkout=cancel',
          customer_email: 'healthcheck@example.test'
        });
        add('決済セッション作成', !!s.url, s.url ? 'URL発行OK' : 'URLなし');
        await stripe.checkout.sessions.expire(s.id).catch(() => {});
      } catch (e) {
        add('決済セッション作成', false, e.message);
      }
    }

    // ── 4. Webhook が登録され有効か ──
    if (stripe) {
      try {
        const hooks = await stripe.webhookEndpoints.list({ limit: 10 });
        const mine = hooks.data.find(h => h.url.includes('stripewebhook'));
        const need = ['checkout.session.completed','customer.subscription.created',
                      'customer.subscription.updated','customer.subscription.deleted',
                      'invoice.payment_succeeded','invoice.payment_failed'];
        const missing = mine ? need.filter(e => !mine.enabled_events.includes(e)) : need;
        add('Webhook設定', !!mine && mine.status === 'enabled' && missing.length === 0,
            mine ? `status=${mine.status}` + (missing.length ? ` 不足:${missing.join(',')}` : '') : '未登録');
      } catch (e) {
        add('Webhook設定', false, e.message);
      }
    }

    // ── 5. 購入→解約でプランが正しく動くか（擬似サブスクで通す）──
    if (stripe) {
      const QA = 'zz_healthcheck_tmp';
      try {
        await db.collection('users').doc(QA).set(
          { email: 'healthcheck@example.test', plan: 'free', stripeCustomerId: 'cus_HEALTHCHECK' },
          { merge: true });
        const fake = {
          id: 'sub_healthcheck', customer: 'cus_HEALTHCHECK', status: 'active',
          metadata: { firebaseUid: QA },
          items: { data: [{ price: { id: PRICES.individual } }] },
          cancel_at_period_end: false,
          current_period_end: Math.floor(Date.now() / 1000) + 2592000
        };
        await syncSubscriptionToFirestore(fake, stripe);
        const a = (await db.collection('users').doc(QA).get()).data() || {};
        add('購入時のプラン反映', a.plan === 'individual', 'plan=' + a.plan);

        fake.status = 'canceled';
        await syncSubscriptionToFirestore(fake, stripe);
        const b = (await db.collection('users').doc(QA).get()).data() || {};
        add('解約時のプラン戻し', b.plan === 'free', 'plan=' + b.plan);
      } catch (e) {
        add('購入→解約の流れ', false, e.message);
      } finally {
        await db.collection('users').doc(QA).delete().catch(() => {});
      }
    }

    // ── 6. VAPID 鍵が正しいか（Push 通知が送れる状態か）──
    try {
      const webpush = initWebPush();
      webpush.getVapidHeaders('https://web.push.apple.com', VAPID_SUBJECT,
                              VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY.value().trim(), 'aes128gcm');
      const subs = await db.collection('pushSubscriptions').get();
      add('Push通知の準備', true, `購読 ${subs.size} 件`);
    } catch (e) {
      add('Push通知の準備', false, e.message);
    }

    // ── 7. 通知メールが実際に送れるか ──
    //    設定値の有無だけ見ても、アプリパスワードの失効や
    //    Gmail 側のブロックは検出できない。実際に1通送って確かめる。
    const mailUser = (NOTIFY_EMAIL_USER.value() || '').trim();
    const mailPass = (NOTIFY_EMAIL_PASS.value() || '').trim();
    if (!mailUser.includes('@') || !mailPass) {
      add('通知メール', false, '未設定（障害が起きてもメールで気づけません）');
    } else {
      const r = await sendMail({
        to: ADMIN_NOTIFY_TO,
        subject: '【動作チェック】通知メールは正常です',
        text: [
          'アプリの動作チェックから送信したテストメールです。',
          'このメールが届いていれば、決済障害の通知や申込通知は',
          '確実に届く状態になっています。',
          '',
          '送信アカウント: ' + mailUser
        ].join('\n')
      });
      add('通知メール', r.ok, r.ok ? ADMIN_NOTIFY_TO + ' へ送信成功' : r.error);
    }

    const failed = checks.filter(c => !c.ok);
    return {
      ok: failed.length === 0,
      総数: checks.length,
      失敗: failed.length,
      結果: checks.map(c => `${c.ok ? '✅' : '❌'} ${c.name}: ${c.detail}`),
      要対応: failed.map(c => `${c.name}: ${c.detail}`)
    };
  }
);

// ═════════════════════════════════════════════
// 決済の常時監視（30分ごと）
//
// 決済が壊れても誰も気づけない状態を避けるため、定期的に
// 「実際に決済セッションを作れるか」を確認する。
// 壊れていたら Firestore に障害フラグを立て、アプリ上部に
// お知らせを自動表示する。復旧したら自動で消える。
//
// 実際に Stripe API を叩くのが要点。設定値の照合だけでは
// 秘密鍵の不正などランタイムの障害を検出できない。
// ═════════════════════════════════════════════
const { onSchedule } = require('firebase-functions/v2/scheduler');

async function runPaymentHealthProbe() {
  const statusRef = db.collection('config').doc('service_status');
  let ok = false;
  let detail = '';
  try {
    const stripe = getStripe(STRIPE_SECRET_KEY.value());
    // 実際に決済セッションを作って、作れたらすぐ破棄する
    const s = await stripe.checkout.sessions.create({
      mode: 'subscription',
      line_items: [{ price: 'price_1U8hkmCD8zFCJuDi77vbC13y', quantity: 1 }],
      success_url: DEFAULT_ORIGIN + '/?checkout=success',
      cancel_url: DEFAULT_ORIGIN + '/?checkout=cancel',
      customer_email: 'monitor@example.test'
    });
    ok = !!s.url;
    detail = ok ? 'OK' : 'セッションURLが返らない';
    await stripe.checkout.sessions.expire(s.id).catch(() => {});
  } catch (e) {
    ok = false;
    detail = (e.type || e.name || 'Error') + ': ' + (e.message || '').slice(0, 200);
  }

  const prev = await statusRef.get();
  const wasOk = prev.exists ? prev.data().paymentOk !== false : true;

  await statusRef.set({
    paymentOk: ok,
    paymentDetail: detail,
    paymentCheckedAt: FieldValue.serverTimestamp(),
    // 壊れ始めた時刻を保持（復旧時にクリア）
    paymentBrokenSince: ok ? null : (prev.exists && prev.data().paymentBrokenSince
                                     ? prev.data().paymentBrokenSince
                                     : FieldValue.serverTimestamp())
  }, { merge: true });

  if (wasOk && !ok) {
    console.error('[監視] 決済が停止しました:', detail);
    await sendMail({
      to: ADMIN_NOTIFY_TO,
      subject: '【緊急】アプリの決済が停止しています',
      text: [
        'アプリの決済機能が利用できない状態を検知しました。',
        '',
        '内容: ' + detail,
        '',
        'ユーザーはプランを購入できません。',
        'アプリ内には「決済に不具合が発生しています」という',
        'お知らせが自動表示されています。',
        '',
        'アプリのメニュー →「🩺 動作チェック（管理者）」で詳細を確認できます。'
      ].join('\n')
    }).catch(() => {});
  } else if (!wasOk && ok) {
    console.log('[監視] 決済が復旧しました');
    await sendMail({
      to: ADMIN_NOTIFY_TO,
      subject: '【復旧】アプリの決済が正常に戻りました',
      text: 'アプリの決済機能が正常に戻りました。お知らせの表示も自動で消えます。'
    }).catch(() => {});
  }
  return { ok, detail };
}

// 30分ごとに自動実行
exports.monitorPayment = onSchedule(
  { schedule: 'every 30 minutes', timeZone: 'Asia/Tokyo',
    secrets: [STRIPE_SECRET_KEY, NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS] },
  async () => { await runPaymentHealthProbe(); }
);

// 手動実行用（管理者が今すぐ確認したいとき）
exports.checkPaymentNow = onCall(
  { secrets: [STRIPE_SECRET_KEY, NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS] },
  async (request) => {
    if (!request.auth) throw new HttpsError('unauthenticated', 'ログインが必要です');
    const email = request.auth.token.email || '';
    if (!ADMIN_EMAILS_FOR_HEALTH.includes(email)) {
      throw new HttpsError('permission-denied', '管理者のみ実行できます');
    }
    return await runPaymentHealthProbe();
  }
);

// ═════════════════════════════════════════════
// 毎朝の運用レポート（マスター宛）
//
// なぜ必要か：
//   これまでの不具合は「設定が間違っていた」よりも
//   「壊れていることが誰にも伝わらなかった」ことで長引いた。
//   メール送信は 3週間ほど毎回失敗し続けていたが、
//   console.error に出るだけで誰も見ていなかった。
//   通知も、自分の端末で1件試して正常と判断していたが、
//   実際にはコーチ16人中15人が未設定だった。
//
//   そこで「実際の利用者がどういう状態か」を毎朝メールで出す。
//   このメール自体が、メール送信の生存確認も兼ねる。
// ═════════════════════════════════════════════
async function buildOpsReport() {
  const lines = [];
  let needsAction = false;

  // ── 通知を受け取れるコーチが何人いるか ──
  const [coachSnap, subSnap] = await Promise.all([
    db.collection('users').where('role', '==', 'coach').get(),
    db.collection('pushSubscriptions').get()
  ]);
  const subscribedUids = new Set();
  subSnap.forEach(d => { const u = d.data().uid; if (u) subscribedUids.add(u); });

  const coaches = coachSnap.docs.map(d => ({
    uid: d.id,
    name: d.data().displayName || d.data().name || '（名前未設定）',
    email: d.data().email || '（メール未登録）',
    hasPush: subscribedUids.has(d.id)
  }));
  const ok = coaches.filter(c => c.hasPush);
  const ng = coaches.filter(c => !c.hasPush);

  lines.push('■ 通知（アイコンの数字）');
  lines.push(`　受け取れるコーチ … ${ok.length}人 / ${coaches.length}人`);
  if (ng.length) {
    needsAction = true;
    lines.push('　受け取れない人（提出があっても気づけません）:');
    ng.forEach(c => lines.push(`　　・${c.name}　${c.email}`));
  }
  lines.push('');

  // ── 過去24時間の提出と、そのとき通知が届いたか ──
  try {
    const since = new Date(Date.now() - 86400000);
    const ssnap = await db.collection('submissions')
      .where('submittedAt', '>=', since).get();
    let notified = 0;
    let missed = 0;
    ssnap.forEach(d => {
      const cid = d.data().coachId;
      if (cid && subscribedUids.has(cid)) notified++; else missed++;
    });
    lines.push('■ 過去24時間の提出');
    lines.push(`　提出 ${ssnap.size}件（通知が届いた ${notified}件 / 届かなかった ${missed}件）`);
    if (missed > 0) needsAction = true;
  } catch (e) {
    lines.push('■ 過去24時間の提出');
    lines.push('　集計できませんでした: ' + e.message);
  }
  lines.push('');

  // ── 決済が実際に使えるか ──
  const pay = await runPaymentHealthProbe();
  lines.push('■ 決済');
  lines.push(pay.ok ? '　正常（実際に決済画面を作れました）'
                    : `　⚠️ 停止中: ${pay.detail}`);
  if (!pay.ok) needsAction = true;
  lines.push('');

  lines.push('■ メール');
  lines.push('　このメールが届いていれば正常です。');
  lines.push('');
  lines.push('──────────');
  lines.push('通知がオフのコーチには、コーチ画面を開いたときに');
  lines.push('案内バナーが出ます。急ぐ場合はアプリのメニューから');
  lines.push('「📣 通知オフのコーチに案内を送る」で個別にお知らせできます。');

  return { needsAction, text: lines.join('\n'), coachesWithoutPush: ng };
}

exports.dailyOpsReport = onSchedule(
  { schedule: '0 8 * * *', timeZone: 'Asia/Tokyo',
    secrets: [STRIPE_SECRET_KEY, NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS] },
  async () => {
    const r = await buildOpsReport();
    // ログにも必ず残す。メールが止まっているときの最後の手がかりになる。
    console.log('[運用レポート]\n' + r.text);
    await sendMail({
      to: ADMIN_NOTIFY_TO,
      subject: (r.needsAction ? '【要対応】' : '【正常】') + 'アプリ運用レポート',
      text: r.text
    });
  }
);

// 手動実行用（マスターが今すぐ見たいとき）
exports.opsReportNow = onCall(
  { secrets: [STRIPE_SECRET_KEY, NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS] },
  async (request) => {
    if (!request.auth) throw new HttpsError('unauthenticated', 'ログインが必要です');
    if (!ADMIN_EMAILS_FOR_HEALTH.includes(request.auth.token.email || '')) {
      throw new HttpsError('permission-denied', 'マスターのみ実行できます');
    }
    const r = await buildOpsReport();
    await sendMail({
      to: ADMIN_NOTIFY_TO,
      subject: (r.needsAction ? '【要対応】' : '【正常】') + 'アプリ運用レポート（手動）',
      text: r.text
    });
    return { ok: true, 要対応: r.needsAction, 本文: r.text };
  }
);

// ─────────────────────────────────────────────
// 通知がオフのコーチに、設定をお願いするメールを送る
//   マスターが明示的に実行したときだけ送る（自動送信はしない）。
//   dryRun: true なら送らずに宛先一覧だけ返す。
// ─────────────────────────────────────────────
exports.notifyCoachesPushOff = onCall(
  { secrets: [NOTIFY_EMAIL_USER, NOTIFY_EMAIL_PASS] },
  async (request) => {
    if (!request.auth) throw new HttpsError('unauthenticated', 'ログインが必要です');
    if (!ADMIN_EMAILS_FOR_HEALTH.includes(request.auth.token.email || '')) {
      throw new HttpsError('permission-denied', 'マスターのみ実行できます');
    }
    const dryRun = !(request.data && request.data.send === true);

    const [coachSnap, subSnap] = await Promise.all([
      db.collection('users').where('role', '==', 'coach').get(),
      db.collection('pushSubscriptions').get()
    ]);
    const subscribed = new Set();
    subSnap.forEach(d => { const u = d.data().uid; if (u) subscribed.add(u); });

    const targets = coachSnap.docs
      .filter(d => !subscribed.has(d.id))
      .map(d => ({ email: d.data().email, name: d.data().displayName || d.data().name || '' }))
      .filter(t => t.email && t.email.includes('@'));

    if (dryRun) {
      return { ok: true, 送信せず確認のみ: true, 宛先数: targets.length,
               宛先: targets.map(t => `${t.name} <${t.email}>`) };
    }

    const body = (name) => [
      `${name || 'コーチ'} 様`,
      '',
      'チアタンブリング ロードマップの通知設定のお願いです。',
      '',
      '現在、選手が課題を提出してもお知らせが届かない状態になっています。',
      'お手数ですが、下記の手順で通知をオンにしてください（1分で終わります）。',
      '',
      '【iPhone / iPad】',
      '① Safari で https://roadmap.cheer-tumbling.jp/ を開く',
      '② 画面下の共有ボタン（□に↑）→「ホーム画面に追加」',
      '③ ホーム画面にできたアイコンからアプリを開く',
      '④ メニュー →「🔔 通知の設定・テスト」→「通知をオンにする」',
      '',
      '【Android / パソコン】',
      '① https://roadmap.cheer-tumbling.jp/register-push.html を開く',
      '②「通知をオンにする」を押す',
      '',
      '設定が終わると、提出があったときにアイコンに件数が表示されます。',
      '',
      '一般社団法人チアタンブリング協会'
    ].join('\n');

    let sent = 0;
    const failed = [];
    for (const t of targets) {
      const r = await sendMail({
        to: t.email,
        subject: '【お願い】提出のお知らせが届かない状態です（通知設定）',
        text: body(t.name)
      });
      if (r.ok) sent++; else failed.push(`${t.email}: ${r.error}`);
    }
    return { ok: failed.length === 0, 送信数: sent, 失敗: failed };
  }
);
