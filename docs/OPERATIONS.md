# チアタンブリングロードマップ 運用ハンドブック

**このファイルはアシスタント（Claude）が「アプリ運用相談：〜」と言われたときに読み込む参照資料。監督は基本的に読む必要なし。**

---

## 1. アプリ概要

- **URL**: https://roadmap.cheer-tumbling.jp/
- **GitHub**: https://github.com/cheer-tumbling-licence-jp/cheer-tumbling-roadmap
- **リポジトリ Local**: `/Users/don/cheer_tumbling_app/`
- **運営**: 一般社団法人 チアタンブリング協会（CTA）
- **代表理事**: 中村祐介
- **サポート連絡先**: cheer.tumbling.association@gmail.com

## 2. 収益モデル（Stripe サブスク）

| プラン | 月額 | 対象 | Stripe Price ID (Live) |
|---|---|---|---|
| 個人プレミアム | ¥480 | 個人ユーザー | price_1U8hkmCD8zFCJuDi77vbC13y |
| コーチプラン | ¥1,200 | 教室指導者 | price_1U8hknCD8zFCJuDidUrDFNE4 |
| コーチプラス | ¥1,980 | 大型教室 | price_1U8hkoCD8zFCJuDi7O2GHzNU |
| トレーニング指導 | ¥4,500 | 個別指導希望選手 | price_1U8hkpCD8zFCJuDiwAbqWWYK |
| 完全1on1 | **¥19,800** | プロ伴走選手（月3名限定） | ⚠️ 新Price ID 発行待ち |

**完全1on1 の価格改定（2026-08-31）**
- ¥7,500 → ¥19,800。根拠は `リサーチ/2026-08-31_1on1プラン価格リサーチ.md`（案B）
- 内容変更：動画添削「無制限」→「月30本（超過¥500/本）」、ビデオ通話 月1回 → **月2回**、個別メニュー毎月更新を追加
- **既存契約者は ¥7,500 のまま継続**（グランドファザリング）。旧Price ID `price_1U8hkqCD8zFCJuDizIhJh8sx` は **Stripe 上でアーカイブしない**
- 新Price ID は Firestore `config/stripe_prices.training_1on1` に入れればコード再デプロイなしで切替可能

**トライアル**: 全プラン 7 日間無料
**振込先**: CTA 銀行口座（Stripe が月次自動振込）

## 3. 技術スタック

| 層 | 使用サービス | 役割 |
|---|---|---|
| フロント | GitHub Pages | HTML/JS 配信（roadmap.cheer-tumbling.jp） |
| 認証・DB | Firebase Auth + Firestore | ユーザー・進捗・課題保存 |
| サーバー | Firebase Cloud Functions (asia-northeast1) | Stripe 連携 API |
| 決済 | Stripe（Live モード） | Checkout・Webhook |
| 動画 | YouTube（Cheernic チャンネル） | 動画配信 |
| ドメイン | ムームードメイン | cheer-tumbling.jp |

## 4. Cloud Functions（3 個）

- `createCheckoutSession` — プラン購入画面を Stripe で生成
- `createPortalLink` — サブスク管理ページ生成
- `stripeWebhook` — Stripe → Firestore の状態同期
- **Endpoint**: https://stripewebhook-joba24buzq-an.a.run.app

## 5. Firebase / Stripe 管理画面

- **Firebase Console**: https://console.firebase.google.com/project/cheer-tumbling-roadmap/
- **Stripe Dashboard**: https://dashboard.stripe.com/
  - Stripe ログイン: `cheer.tumbling.association@gmail.com`

## 6. よくある運用対応と手順

### A. ユーザーが解約したい

**方法 1（推奨・ユーザー自身で）**：
アプリ内メニュー → 「💳 サブスクを管理・解約」 → Stripe Portal で解約

**方法 2（監督が代行）**：
1. Stripe Dashboard → 顧客 → 該当ユーザーのメールで検索
2. サブスクリプション → 「キャンセル」
3. Firestore の `users/{uid}.plan` は Webhook で自動的に `free` に

### B. 返金したい

1. Stripe Dashboard → 支払い → 該当決済を検索
2. 「返金」ボタン → 全額 or 部分返金
3. カード会社経由で 5〜10 営業日でユーザーに返金

**返金ポリシー**：トライアル 7 日以内は全額、以降は原則なし（要ケースバイケース）

### C. Apple Pay / Google Pay が使えないと言われた

- **iPhone Safari**: Apple Wallet にカード登録があるか確認してもらう
- **iPhone Chrome**: 同上（Chrome でも Apple Pay 使える）
- **Android Chrome**: Google Pay にカード登録あるか
- **Windows Safari**: Windows 版 Safari は Apple Pay 非対応 → カード決済で

### D. 決済が失敗する

1. Stripe Dashboard → 支払い → 失敗した決済を確認
2. 「decline_code」を確認：
   - `insufficient_funds` → ユーザーに残高不足を案内
   - `card_declined` → カード会社に確認するよう案内
   - `expired_card` → カード有効期限切れ、新カードで再試行

### E. 課題提出通知が来ない（コーチ側）

1. Firebase Console → Firestore → `notifications/{uid}` を確認
2. `submittedAt` フィールドがあるか（過去に `createdAt` のみだったバグあり）
3. 通知バッジのロジック: index.html 内 `data.submittedAt || data.createdAt`

## 7. 過去のトラブル履歴（学習資産）

| 日付 | 症状 | 原因 | 対処 |
|---|---|---|---|
| 2026-07-21 | 通知バッジが表示されない | フィールド名 `createdAt` vs `submittedAt` | フォールバック実装 |
| 2026-08-11 | 練習メニュークラッシュ | trainingCategories.warmup 未定義 | warmup エントリ追加 |
| 2026-08-13 | Stripe Secret 二重貼り付け | 214文字（正常は107文字） | 自動検出して修正 |
| 2026-08-16 | Webhook API バージョン invalid | `api_version: null` パラメータ | パラメータ削除 |

## 8. 監視ポイント

- **Stripe Dashboard トップ**: 未処理の支払いエラー数
- **Firebase Console → Cloud Functions**: エラー率 5% 超えたら要確認
- **不具合報告 FAB**: ユーザーがアプリ右下から送信 → Firestore `bugReports/` コレクション
- **GitHub Actions**: なし（デプロイは私が git push で実行）

## 9. コード更新の流れ

1. ローカル `/Users/don/cheer_tumbling_app/` で編集
2. `git commit + git push` → GitHub Pages が 1〜2 分で反映
3. Cloud Functions 変更時は `firebase deploy --only functions`
4. Service Worker のキャッシュで古いバージョン表示される可能性 → ユーザーに右下 ⟳ 更新ボタンを案内

## 10. 相談時に私が自動収集する情報

「アプリ運用相談：〜」トリガー時、`handoff_operations.sh` が以下を出力：
- 最新デプロイ時刻・コミットハッシュ
- 直近 7 日の git ログ
- 保留中の TODO / 未処理不具合報告数（Firestore 参照可能な場合）
- Stripe に登録された商品数

---

**このドキュメントは変更が発生するたびに私が自動で更新する。監督は基本的に読まなくてよい。**
