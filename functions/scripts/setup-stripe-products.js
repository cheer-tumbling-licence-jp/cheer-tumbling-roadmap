#!/usr/bin/env node
/**
 * Stripe商品・価格の一括作成 + Firestore config/stripe_prices への反映
 *
 * 使い方（テスト環境の商品作成）:
 *   STRIPE_SECRET_KEY=sk_test_XXX node scripts/setup-stripe-products.js
 *
 * 本番環境で使う場合（Stripe 審査完了後）:
 *   STRIPE_SECRET_KEY=sk_live_XXX node scripts/setup-stripe-products.js
 *
 * 実行内容:
 *   1. 5つのProduct + Priceを Stripe に作成
 *      （既存の同名Productは再利用 = 冪等）
 *   2. 各Priceに metadata.firebasePlan を付与
 *      → Cloud Function stripeWebhook がこれを見てユーザーの plan を決定
 *   3. Firestore の config/stripe_prices ドキュメントに priceID を書き込み
 *      → クライアント stripe-checkout.js が これを読んで Checkout に priceId を渡す
 *
 * 前提:
 *   - functions/ ディレクトリで `npm install` 済み
 *   - Firebase Admin SDK が gcloud認証 or GOOGLE_APPLICATION_CREDENTIALS で認証済み
 *     （firebase-tools がログイン済みなら通常OK）
 */

const Stripe = require('stripe');
const admin = require('firebase-admin');

const PLANS = [
  {
    planKey: 'individual',
    name: '個人プレミアムプラン',
    description: '応用動画解放、練習メニュー無制限、進捗記録永続保存、クラウド同期',
    amount: 480,
    lookupKey: 'individual_monthly'
  },
  {
    planKey: 'coach',
    name: 'コーチプラン',
    description: 'コーチダッシュボード、課題配布、進捗ヒートマップ、動画添削、選手10名まで',
    amount: 1200,
    lookupKey: 'coach_monthly'
  },
  {
    planKey: 'coach_plus',
    name: 'コーチプラスプラン',
    description: 'コーチプラン機能すべて + 選手無制限 + マスタークラス動画 + CSV出力',
    amount: 1980,
    lookupKey: 'coach_plus_monthly'
  },
  {
    planKey: 'training_light',
    name: 'トレーニング指導プラン',
    description: '個別メニュー作成、動画添削 月20本、スタンプ・コメント返信、プレミアム動画見放題',
    amount: 4500,
    lookupKey: 'training_light_monthly'
  },
  {
    planKey: 'training_1on1',
    name: '完全1on1プラン',
    description: '動画添削無制限、専用LINE 24h以内返信、月1ビデオ通話30分、月1動画解析レポート、優先サポート',
    amount: 7500,
    lookupKey: 'training_1on1_monthly'
  }
];

async function main() {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    console.error('❌ STRIPE_SECRET_KEY 環境変数が未設定です');
    console.error('   例: STRIPE_SECRET_KEY=sk_test_... node scripts/setup-stripe-products.js');
    process.exit(1);
  }
  const isLive = secretKey.startsWith('sk_live_');
  const modeLabel = isLive ? '🔴 本番環境' : '🟢 テスト環境';
  console.log(`[Stripe商品セットアップ] ${modeLabel} で実行します`);

  const stripe = new Stripe(secretKey);

  // Firebase Admin 初期化（gcloud認証 or ADC でOK）
  if (!admin.apps.length) {
    admin.initializeApp({
      projectId: 'cheer-tumbling-roadmap'
    });
  }
  const db = admin.firestore();

  const priceMap = {};

  for (const plan of PLANS) {
    console.log(`\n── ${plan.name} (${plan.planKey}) ¥${plan.amount}/月 ──`);

    // 1. 既存のProductを検索（同じ metadata.firebasePlan を持つもの）
    let product = null;
    const existingProducts = await stripe.products.search({
      query: `metadata['firebasePlan']:'${plan.planKey}' AND active:'true'`,
      limit: 1
    });
    if (existingProducts.data.length > 0) {
      product = existingProducts.data[0];
      console.log(`  ✓ 既存Product再利用: ${product.id}`);
    } else {
      product = await stripe.products.create({
        name: plan.name,
        description: plan.description,
        metadata: { firebasePlan: plan.planKey },
        tax_code: 'txcd_10103001' // Software as a service (デジタルサービス)
      });
      console.log(`  ✓ Product作成: ${product.id}`);
    }

    // 2. 既存のPriceを検索（同じ lookup_key）
    let price = null;
    const existingPrices = await stripe.prices.list({
      lookup_keys: [plan.lookupKey],
      active: true,
      limit: 1
    });
    if (existingPrices.data.length > 0) {
      price = existingPrices.data[0];
      console.log(`  ✓ 既存Price再利用: ${price.id}`);
    } else {
      price = await stripe.prices.create({
        product: product.id,
        unit_amount: plan.amount,
        currency: 'jpy',
        recurring: { interval: 'month' },
        lookup_key: plan.lookupKey,
        metadata: { firebasePlan: plan.planKey }
      });
      console.log(`  ✓ Price作成: ${price.id}`);
    }

    priceMap[plan.planKey] = price.id;
  }

  // 3. Firestore config/stripe_prices に書き込み
  //    クライアント (stripe-checkout.js) はこの1箇所を読む。
  //    テスト時→テスト用priceID、本番切替時→本番用priceID を再実行で上書き。
  console.log('\n── Firestore config/stripe_prices に反映 ──');
  await db.collection('config').doc('stripe_prices').set(
    {
      ...priceMap,
      updatedAt: admin.firestore.FieldValue.serverTimestamp(),
      mode: isLive ? 'live' : 'test'
    },
    { merge: true }
  );
  console.log('  ✓ Firestore反映完了 (mode:', isLive ? 'live' : 'test', ')');

  // 4. まとめ出力（コピペ用）
  console.log('\n========================================');
  console.log('セットアップ完了！各プランの Price ID:');
  console.log('========================================');
  for (const [k, v] of Object.entries(priceMap)) {
    console.log(`  ${k.padEnd(18)} → ${v}`);
  }
  console.log('\n上記は Firestore config/stripe_prices にも保存済みです。');
  console.log('クライアント側 stripe-checkout.js は自動的に読み込むので、追加作業は不要です。');
  console.log('\n次のステップ: Cloud Functions にシークレットを設定してデプロイ');
  console.log('  firebase functions:secrets:set STRIPE_SECRET_KEY');
  console.log('  firebase functions:secrets:set STRIPE_WEBHOOK_SECRET');
  console.log('  firebase deploy --only functions');
}

main().catch((err) => {
  console.error('\n❌ エラー:', err.message);
  if (err.raw) console.error('  Stripe raw:', err.raw);
  process.exit(1);
});
