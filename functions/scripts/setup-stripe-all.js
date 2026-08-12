#!/usr/bin/env node
/**
 * Stripe一括セットアップ（Webhook + 商品 + Firestore反映）
 *
 * 使い方:
 *   STRIPE_SECRET_KEY=sk_test_XXX WEBHOOK_URL=https://... node scripts/setup-stripe-all.js
 *
 * 動作:
 *   1. WEBHOOK_URL を Stripe に登録（既存があれば再利用、URLが違えば更新）
 *   2. 5プランのProduct + Priceを作成/再利用
 *   3. Firestore config/stripe_prices に priceID マッピング反映
 *   4. Webhook Signing Secret を標準出力
 */

const Stripe = require('stripe');
const admin = require('firebase-admin');

const PLANS = [
  { planKey: 'individual', name: '個人プレミアムプラン',
    description: '応用動画解放、練習メニュー無制限、進捗記録永続保存、クラウド同期',
    amount: 480, lookupKey: 'individual_monthly' },
  { planKey: 'coach', name: 'コーチプラン',
    description: 'コーチダッシュボード、課題配布、進捗ヒートマップ、動画添削、選手10名まで',
    amount: 1200, lookupKey: 'coach_monthly' },
  { planKey: 'coach_plus', name: 'コーチプラスプラン',
    description: 'コーチプラン機能すべて + 選手無制限 + マスタークラス動画 + CSV出力',
    amount: 1980, lookupKey: 'coach_plus_monthly' },
  { planKey: 'training_light', name: 'トレーニング指導プラン',
    description: '個別メニュー作成、動画添削 月20本、スタンプ・コメント返信、プレミアム動画見放題',
    amount: 4500, lookupKey: 'training_light_monthly' },
  { planKey: 'training_1on1', name: '完全1on1プラン',
    description: '動画添削無制限、専用LINE 24h以内返信、月1ビデオ通話30分、月1動画解析レポート、優先サポート',
    amount: 7500, lookupKey: 'training_1on1_monthly' }
];

const WEBHOOK_EVENTS = [
  'checkout.session.completed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'invoice.payment_succeeded',
  'invoice.payment_failed'
];

async function main() {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const webhookUrl = process.env.WEBHOOK_URL;
  if (!secretKey) { console.error('❌ STRIPE_SECRET_KEY 未設定'); process.exit(1); }
  if (!webhookUrl) { console.error('❌ WEBHOOK_URL 未設定'); process.exit(1); }

  const isLive = secretKey.startsWith('sk_live_');
  console.log(`[Stripeセットアップ] ${isLive ? '🔴 本番' : '🟢 テスト'} モード`);
  console.log(`   Webhook URL: ${webhookUrl}\n`);

  const stripe = new Stripe(secretKey);

  if (!admin.apps.length) {
    admin.initializeApp({ projectId: 'cheer-tumbling-roadmap' });
  }
  const db = admin.firestore();

  // ─── 1. Webhookエンドポイント設定 ───
  console.log('── 1. Webhook エンドポイント登録 ──');
  const existingHooks = await stripe.webhookEndpoints.list({ limit: 100 });
  let webhook = existingHooks.data.find(h => h.url === webhookUrl);
  let webhookSecret = null;

  if (webhook) {
    console.log(`  ✓ 既存 Webhook を再利用: ${webhook.id}`);
    // 既存ならイベント更新のみ（secret は既存の値を取り直せないので、新規作成が必要な場合はダッシュボードで再生成）
    if (JSON.stringify(webhook.enabled_events.sort()) !== JSON.stringify([...WEBHOOK_EVENTS].sort())) {
      webhook = await stripe.webhookEndpoints.update(webhook.id, {
        enabled_events: WEBHOOK_EVENTS
      });
      console.log('  ✓ イベント一覧を更新');
    }
    webhookSecret = webhook.secret; // 既存の場合、secretは通常返ってこない（作成時のみ）
    if (!webhookSecret) {
      console.log('  ℹ 既存Webhookの署名secretは Stripe API では再取得不可');
      console.log('    → 新規作成に切替（古いWebhookは削除）');
      await stripe.webhookEndpoints.del(webhook.id);
      webhook = null;
    }
  }

  if (!webhook) {
    webhook = await stripe.webhookEndpoints.create({
      url: webhookUrl,
      enabled_events: WEBHOOK_EVENTS,
      description: 'Cheer Tumbling Roadmap Cloud Functions webhook'
    });
    webhookSecret = webhook.secret;
    console.log(`  ✓ 新規 Webhook 作成: ${webhook.id}`);
  }

  if (!webhookSecret) {
    console.error('❌ Webhook secret を取得できませんでした');
    process.exit(1);
  }

  // ─── 2. 商品・価格作成 ───
  console.log('\n── 2. 商品・価格作成 ──');
  const priceMap = {};

  for (const plan of PLANS) {
    let product = null;
    const existingProducts = await stripe.products.search({
      query: `metadata['firebasePlan']:'${plan.planKey}' AND active:'true'`,
      limit: 1
    });
    if (existingProducts.data.length > 0) {
      product = existingProducts.data[0];
      console.log(`  ✓ [${plan.planKey}] Product再利用: ${product.id}`);
    } else {
      product = await stripe.products.create({
        name: plan.name,
        description: plan.description,
        metadata: { firebasePlan: plan.planKey }
      });
      console.log(`  ✓ [${plan.planKey}] Product作成: ${product.id}`);
    }

    let price = null;
    const existingPrices = await stripe.prices.list({
      lookup_keys: [plan.lookupKey], active: true, limit: 1
    });
    if (existingPrices.data.length > 0) {
      price = existingPrices.data[0];
      console.log(`             Price再利用: ${price.id}`);
    } else {
      price = await stripe.prices.create({
        product: product.id,
        unit_amount: plan.amount,
        currency: 'jpy',
        recurring: { interval: 'month' },
        lookup_key: plan.lookupKey,
        metadata: { firebasePlan: plan.planKey }
      });
      console.log(`             Price作成: ${price.id}`);
    }
    priceMap[plan.planKey] = price.id;
  }

  // ─── 3. Firestore 反映 ───
  console.log('\n── 3. Firestore config/stripe_prices 更新 ──');
  await db.collection('config').doc('stripe_prices').set(
    { ...priceMap, updatedAt: admin.firestore.FieldValue.serverTimestamp(),
      mode: isLive ? 'live' : 'test' },
    { merge: true }
  );
  console.log('  ✓ 反映完了');

  // ─── 4. 結果 ───
  console.log('\n========================================');
  console.log('セットアップ完了');
  console.log('========================================');
  console.log(`Webhook ID:     ${webhook.id}`);
  console.log(`Webhook Secret: ${webhookSecret}`);
  console.log('\nPrice IDs:');
  for (const [k, v] of Object.entries(priceMap)) {
    console.log(`  ${k.padEnd(18)} → ${v}`);
  }

  // Firebase Secrets 更新用に一時ファイルにwebhookSecretを書き出す
  const fs = require('fs');
  const secretFile = '/tmp/whsec_' + Date.now() + '.txt';
  fs.writeFileSync(secretFile, webhookSecret);
  console.log(`\nWebhook secret を一時ファイルに保存: ${secretFile}`);
  console.log('次のコマンドで Firebase Secret に登録:');
  console.log(`  firebase functions:secrets:set STRIPE_WEBHOOK_SECRET --data-file=${secretFile}`);
  console.log(`  rm ${secretFile}`);
}

main().catch((err) => {
  console.error('\n❌ エラー:', err.message);
  if (err.raw) console.error('  Stripe raw:', err.raw);
  process.exit(1);
});
