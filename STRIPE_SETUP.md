# Stripe サブスク有効化 セットアップ手順書

**対象**: Cheer Tumbling Roadmap アプリで Stripe サブスクリプション機能を稼働させるまでの一連の手順。
**所要時間**: 全ステップで約 30〜45 分（Stripe 審査完了後）。
**前提**: Stripe アカウント作成済み・Firebase Blaze プラン契約済み（両方このセッションで完了確認済）。

---

## 全体像

このアプリの Stripe 決済は以下の3層構造：

1. **クライアント側** (`stripe-checkout.js`)
   - 「◯◯プランに申込む」ボタン → Cloud Function を呼出 → Stripe Checkout へリダイレクト
2. **Cloud Functions** (`functions/index.js`) — 東京リージョン
   - `createCheckoutSession`: Stripe Checkout Session を作成
   - `createPortalLink`: 顧客ポータル（解約・プラン変更）
   - `stripeWebhook`: Stripe イベント受信 → Firestore の `users/{uid}.plan` 更新
3. **Firestore** (`users/{uid}` + `config/stripe_prices`)
   - ユーザーのプラン情報を保持
   - `config/stripe_prices` に「planKey → Stripe Price ID」のマッピング

---

## 前提の作業ディレクトリ

すべての `bash` コマンドは以下ディレクトリで実行：
```bash
cd /Users/don/cheer_tumbling_app
```

---

## ステップ 1: テストモードで動作確認（審査中の今すぐ着手可）

Stripe 審査完了を待たずに、**テスト環境で全機能を動作確認**できます。実際のお金は動かないので安全。

### 1-1. Stripe テスト用シークレットキーを取得

Stripe Dashboard → 開発者 → API キー（テストモード）
→ 「シークレットキー」の `sk_test_...` をコピー

### 1-2. Firebase にシークレットとして登録（初回のみ）

```bash
firebase functions:secrets:set STRIPE_SECRET_KEY
```
→ プロンプトが出るので、コピーした `sk_test_...` を貼り付けて Enter。

**この値は Claude には見えません。**

### 1-3. Cloud Functions を初回デプロイ

```bash
firebase deploy --only functions
```

デプロイ完了後、コンソールに以下のような URL が表示されます：
```
Function URL (stripeWebhook(asia-northeast1)):
https://stripewebhook-xxxxxxxxxx-an.a.run.app
```

**この URL をメモしてください（次のステップで Stripe に登録します）。**

### 1-4. Stripe Dashboard で Webhook エンドポイント登録

1. https://dashboard.stripe.com/test/webhooks を開く
2. 「エンドポイントを追加」ボタンをクリック
3. **エンドポイント URL**: 1-3 で控えた URL を貼り付け
4. **リッスンするイベント**: 以下 5 件を選択
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
5. 追加完了後、そのエンドポイントの詳細ページで **「署名シークレットを表示」**
   → `whsec_...` で始まる文字列をコピー

### 1-5. Webhook シークレットを Firebase に登録

```bash
firebase functions:secrets:set STRIPE_WEBHOOK_SECRET
```
→ プロンプトで `whsec_...` を貼り付けて Enter

### 1-6. Cloud Functions を再デプロイ

```bash
firebase deploy --only functions
```

### 1-7. Stripe 商品・価格を一括作成

```bash
STRIPE_SECRET_KEY=sk_test_XXXXX node functions/scripts/setup-stripe-products.js
```
（`sk_test_XXXXX` の部分は 1-1 で控えたキーに置き換え）

このスクリプトが自動で：
- 5 つの商品（個人 / コーチ / コーチプラス / トレーニング指導 / 完全1on1）を Stripe に作成
- 各商品の月額価格を作成
- 各価格の `firebasePlan` メタデータを設定
- Firestore `config/stripe_prices` に priceID を書き込み

冪等（何度実行しても同じ結果）なので、再実行OK。

### 1-8. Firestore ルールをデプロイ

```bash
firebase deploy --only firestore:rules
```

### 1-9. フロントエンドをデプロイ（GitHub Pages）

```bash
git add -A
git commit -m "Stripe サブスク機能を追加（Cloud Functions + フロントエンド統合）"
git push
```
GitHub Pages が自動的にデプロイ（1〜2 分）。

### 1-10. テスト決済で動作確認

1. https://roadmap.cheer-tumbling.jp/ でログイン
2. ハンバーガーメニュー → 「🎁 プランを見る・変更する」 → LP へ
3. 好きなプランの「◯◯に申込む」をクリック
4. Stripe Checkout 画面で以下を入力：
   - メールアドレス: 任意（テスト用）
   - **カード番号: `4242 4242 4242 4242`** ← Stripe公式テストカード
   - 有効期限: 任意の未来日（例: 12/34）
   - CVC: 任意の 3 桁（例: 123）
5. 「登録」→ 成功画面が出て `/?checkout=success` に戻る
6. トーストで「サブスク開始しました」表示
7. ハンバーガーメニューで現在のプランが変わっていることを確認
8. **Stripe Dashboard** → 顧客 で該当ユーザーのサブスクを確認
9. **Firestore** users/{uid} で `plan: 'individual'` などになっていることを確認

### 1-11. 解約フローの確認

1. ハンバーガーメニュー → 「💳 サブスクを管理・解約」 をクリック
2. Stripe 顧客ポータルへ遷移
3. 「プランをキャンセル」→ 確認
4. アプリに戻り、`users/{uid}.plan` が最終的に `free` に戻ることを確認

---

## ステップ 2: 本番モードへの切替（Stripe 審査完了後）

Stripe 審査完了メールが届いたら実施：

### 2-1. Stripe 本番用シークレットキーを取得

Stripe Dashboard 右上のトグルを **「テスト環境」→「本番環境」** に切り替え
→ 開発者 → API キー → シークレットキーの `sk_live_...` をコピー

⚠️ **本番用シークレットキー（`sk_live_...`）は誰にも共有しないでください（Claude にも）。**

### 2-2. Firebase シークレットを本番用に更新

```bash
firebase functions:secrets:set STRIPE_SECRET_KEY
```
→ `sk_live_...` を貼り付け

### 2-3. 本番用 Webhook を Stripe に登録

1. https://dashboard.stripe.com/webhooks （本番モード）
2. ステップ 1-4 と同じ手順、同じ URL を登録
3. `whsec_...`（本番用の新しいもの）をコピー

### 2-4. Webhook シークレットを更新

```bash
firebase functions:secrets:set STRIPE_WEBHOOK_SECRET
```
→ 本番用の `whsec_...` を貼り付け

### 2-5. Cloud Functions を再デプロイ

```bash
firebase deploy --only functions
```

### 2-6. 本番用商品を作成

```bash
STRIPE_SECRET_KEY=sk_live_XXXXX node functions/scripts/setup-stripe-products.js
```
Firestore の `config/stripe_prices` は本番用 priceID で上書きされる（クライアントは自動で最新を使う）。

### 2-7. 実カードで少額テスト決済

自分のカードで一番安いプラン（¥480）を試し、うまく行ったら即解約。

---

## トラブルシューティング

### Q. Webhook が届かない
- Stripe Dashboard → Webhook → 該当エンドポイント → 「試行」タブで送信履歴を確認
- ステータス 200 になっているか
- ステータス 400 なら署名シークレット不一致 → 1-5 と 1-6 を再実行
- ステータス 500 なら Cloud Function エラー → Firebase Console → Functions → ログを確認

### Q. 「priceId が空」エラー
- Firestore `config/stripe_prices` に priceID が入っていない
- ステップ 1-7 を再実行

### Q. Firestore ルールでプランが更新できない
- Cloud Function が Admin SDK を使っているので、通常はブロックされません
- クライアントから直接 plan を書き換えようとしていないか確認

### Q. Cloud Function デプロイ時に「permission denied」エラー
- `firebase login` で認証済みか確認：`firebase login:list`
- 現在のログイン: `cheernicpro@gmail.com` （確認済）

---

## 参考：システム構成図

```
┌──────────────────┐     ①申込ボタンクリック
│  ユーザー       │───────────────────────────┐
│  (ブラウザ)     │                          │
└──────────────────┘                          ▼
        ▲                          ┌────────────────────┐
        │ ⑧ プラン反映            │ Cloud Function     │
        │                          │ createCheckoutSession │
        │                          └────────┬───────────┘
        │                                   │ ② Session作成
        │                                   ▼
        │                          ┌────────────────────┐
        │ ③ Checkout URL          │  Stripe            │
        └──────────────────────────│  Checkout          │
        ④カード入力→登録          └────────┬───────────┘
                                            │ ⑤ subscription.created
                                            ▼
                                   ┌────────────────────┐
                                   │ Cloud Function     │
                                   │ stripeWebhook      │
                                   └────────┬───────────┘
                                            │ ⑥ users/{uid}.plan 更新
                                            ▼
                                   ┌────────────────────┐
                                   │  Firestore         │
                                   │  users/{uid}       │
                                   └────────┬───────────┘
                                            │ ⑦ realtime sync
                                            │
                                    (⑧へ戻る)
```

---

## 次回セッション引継ぎ

このセッションで作成/更新したファイル:

- `functions/index.js` — Cloud Functions 3関数
- `functions/package.json` — 依存パッケージ
- `functions/scripts/setup-stripe-products.js` — 商品セットアップスクリプト
- `firebase.json` — functions セクション追加
- `firestore.rules` — stripe管理フィールドの書込防止・config読取許可
- `stripe-checkout.js` — クライアント側 Checkout/Portal ヘルパー
- `index.html` — Firebase Functions SDK + stripe-checkout.js 追加、auth-menuに管理ボタン
- `landing.html` — 5つのプランCTAボタンを「申込む」に変更、`#pricing` アンカー追加

**まだ実行していないこと**（このドキュメントの手順で監督が実行）:
- Firebase Secrets 登録
- Cloud Functions デプロイ
- Stripe Webhook 登録
- Stripe 商品作成スクリプト実行
- Firestore rules デプロイ
- git push（フロントエンドデプロイ）
- テスト決済
