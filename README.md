# Cheer Tumbling Roadmap

一般社団法人チアタンブリング協会 公式アプリ「チアタンブリングロードマップ」の GitHub Pages リポジトリ。

- 🌐 公開URL：https://roadmap.cheer-tumbling.jp/
- 📦 GitHub：https://github.com/cheer-tumbling-licence-jp/cheer-tumbling-roadmap

---

## 📁 ディレクトリ・ファイル構造（見取り図）

### ✅ ルート直下（動かさない）

これらは **GitHub Pages / Firebase / npm / PWA の仕様で「ルート直下必須」** のため移動できません。

#### 🌐 稼働中HTML（アプリ本体・公開URL固定）

| ファイル | 用途 |
|--|--|
| `index.html` | メイン（技・トレ・練習メニュー・成長記録） |
| `coach.html` | コーチダッシュボード |
| `me.html` | 選手のマイページ |
| `dashboard.html` | 管理者向け |
| `landing.html` | LP（ランディング） |
| `help.html` | ヘルプ |
| `student-link.html` | 選手招待リンク受け取り |
| `privacy.html` / `terms.html` / `specified-commercial.html` | 法定ページ |

#### 📜 稼働中JS

| ファイル | 用途 |
|--|--|
| `service-worker.js` | PWA キャッシュ・オフライン対応（scope=/ 必須） |
| `app-update.js` | 全ページ共通の更新チェック FAB |
| `stripe-checkout.js` | Stripe 決済ハンドラ（index.html から参照） |

#### ⚙️ 設定ファイル

| ファイル | 何のため |
|--|--|
| `firebase.json` / `.firebaserc` | Firebase CLI 設定 |
| `firestore.rules` / `firestore.indexes.json` | Firestore セキュリティ・インデックス |
| `storage.rules` / `storage-lifecycle.json` | Firebase Storage ルール・ライフサイクル |
| `manifest.json` | PWA マニフェスト |
| `CNAME` | GitHub Pages カスタムドメイン |
| `package.json` / `package-lock.json` | npm 依存関係（node_modules 用） |

#### 🚀 起動・監督向けドキュメント

| ファイル | 用途 |
|--|--|
| `project_boot.sh` | セッション開始時に走る診断スクリプト |
| `CLAUDE.md` | Claude 起動時に自動読み込みされる指示書（動かさない） |
| `README.md` | このファイル |

---

### 📂 ディレクトリ（すべて用途別に整理済み）

| ディレクトリ | 内容 |
|--|--|
| **`data/`** | JSON データ（coach_items / cheer_tumbling_skills / announcements など） |
| **`assets/`** | 画像・LPスクリーンショット |
| **`icons/`** | PWA アイコン各サイズ |
| **`scripts/`** | 開発用スクリプト（診断・スクショ撮影・販促物生成など） |
| **`functions/`** | Firebase Functions（サーバ関数） |
| **`youtube/`** | YouTube アップロード自動化（動画管理） |
| **`coach/`** | コーチ機能の追加ファイル |
| **`shared/`** | 複数HTMLで共有する部品 |
| **`qr/`** | QRコード画像 |
| **`node_modules/`** | npm 依存関係（自動生成、触らない） |
| **`マーケティング/`** | 販促物 PDF/画像・三つ折りチラシ |
| **`リサーチ/`** | 事業・市場リサーチ資料 |
| **`企画/`** | 企画書・提案資料 |

---

### 📦 整理用ディレクトリ（今回追加）

| ディレクトリ | 内容 |
|--|--|
| **`_archive/`** | 過去のバックアップ **18 個**（`backup-YYYY-MM-DD-pre-*/` 形式） |
| **`docs/`** | ドキュメント（AI_DRAFTED_LOG / OPERATIONS / STRIPE_SETUP / HANDOFF / 事業企画書） |
| **`prototypes/`** | プロトタイプ HTML（本番前の試作、公開されていない） |

---

## 🔧 主要スクリプト

`scripts/` 内の重要なもの：

| スクリプト | 用途 |
|--|--|
| `diagnose_video_pipeline.sh` | 動画パイプライン診断（Drive/manifest/OAuth/アプリ反映） |
| `sync_coach_items.js` | index.html の trainings/skills を coach_items.json に自動同期 |
| `take_lp_screenshots.js` | LP用アプリスクリーンショット自動撮影（Playwright） |
| `make_promo_trifold_a4.py` | A4三つ折り総合版チラシ 生成 |
| `make_promo_general_flyer.py` | 単ページ総合チラシ 生成 |
| `handoff_operations.sh` | 運用相談モード切替 |

---

## ビルド・デプロイ

- **ローカル確認**：`python3 -m http.server 5191` → http://localhost:5191/
- **デプロイ**：`main` ブランチに push すると GitHub Pages が自動デプロイ

## 制作

一般社団法人 チアタンブリング協会
