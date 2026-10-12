# Cheer Tumbling Roadmap アプリ

チアリーディング指導者向けタンブリング練習ロードマップアプリ。
**公開中**：https://roadmap.cheer-tumbling.jp/

---

## 🛠 運営方針（Z案：ここで完結・厳守）

**すべての作業をこのセッションで完結させる**。新機能追加・修正・公開・QA、全部ここ。

- 監督の役割：「こうしたい」を伝えるだけ（経営判断のみ）
- CEO（Claude）の役割：部下エージェントを Agent ツールで編成し、結果を集約して経営報告
- Cowork は**原則使わない**（記憶が引き継げず、過去にヒューマンエラー事故が発生）

### 組織（`.claude/agents/` に常設・2026-10-11 設置）

このアプリ専属の担当者。定義ファイルに「過去に何で失敗したか」を書き込んであるので、
セッションが変わっても同じ失敗を繰り返さない。

| 役職 | 呼び方 | 使うとき |
|---|---|---|
| **統括（CEO）** | `ceo` | 方針決定・部下の編成・監督への報告責任。**通常はメインセッションが CEO として動く**ので呼ばなくてよい。別セッションに統括を任せるときだけ呼ぶ |
| **不具合担当** | `bug-hunter` | 「動かない」「エラーが出る」「反映されない」。**推測での修正を禁止**し、実データ（ログ・実行出力・ライブラリ実物）を根拠に出させる |
| **マーケ・戦略担当** | `growth-strategist` | 集客・料金・訴求・継続率・競合。**先に実データの数字を取ってから**提案させる |
| **提示前ゲート** | `roadmap-reviewer` | 監督に見せる前・commit する前（**必須**） |

汎用の部下（必要に応じて追加で編成）：

| 役職 | サブエージェント種別 | 使うとき |
|---|---|---|
| CTO | `Plan` | 設計・アーキテクチャ起案 |
| リードエンジニア | `general-purpose` | 実装・修正・公開作業 |
| コードリサーチャー | `Explore` | 既存コードの調査・関数特定 |
| QA テスター | `general-purpose` + プレビューツール | ブラウザ実機テスト |
| セキュリティ監査 | `general-purpose` + `security-review` スキル | 公開前チェック |

独立した調査は**並列で走らせる**（実例：3 エージェント並列の監査）。
部下の報告は**そのまま信じず**、決定的な主張は CEO が自分で裏を取ってから監督に出す。

---

## ⚠️ 万一 Cowork を使ってしまった場合（保険）

通常は使わない方針だが、誤って Cowork で作業された場合に備え、以下の安全網は残してある：

---

## 📋 セッション開始時の必須手順

1. `bash project_boot.sh` を実行
   - `sync_from_cowork.sh`：Cowork に作業漏れがないか確認（通常は「同期不要」が出るはず）
   - `check_critical_fixes.sh`：Phase 1 重要修正 12 項目の保持を検証
2. 警告が出ていたら **作業に入る前に必ず対処**
3. 対処後、`scripts/check_critical_fixes.sh` を再実行して全項目 OK を確認

### 万一マージが必要になった場合（COWORK_NEWER_DETECTED）

1. `.cowork_pending/cowork_latest.html` の内容を確認
2. `cp .cowork_pending/cowork_latest.html index.html` でローカル版を Cowork 版に置換
3. **Phase 1 重要修正を再適用**（下記の一覧に沿って）
4. ブラウザで動作検証（http://localhost:5191/）
5. `git commit && git push`
6. GitHub Pages 反映を確認

---

## 🛡 Phase 1 重要修正一覧（**絶対に消さない**）

以下の 12 項目は Cowork からマージしたあとに失われていないか必ず確認。`scripts/check_critical_fixes.sh` で自動検証可能。

| # | 修正内容 | 検出パターン |
|---|---|---|
| 1 | エクスポートHTML データ破壊防止 | `closingScriptRe` |
| 2 | saveEdits 400ms デバウンス化 | `_saveEditsTimer` |
| 3 | beforeunload で保存フラッシュ | `flushSaveEdits` |
| 4 | ツリー表示でレベルフィルタ | `currentSkillFilter !== 'all' && currentSkillFilter !== String(lv)` |
| 5 | モーダル Esc 多重対応 | `addItem.classList.contains('show')` |
| 6 | 複製時の名前入力プロンプト | `複製するメニューの名前を入力` |
| 7 | モバイル対応 @media | `@media (max-width: 600px)` |
| 8 | タブ aria-tablist | `role="tablist"` |
| 9 | chip aria-pressed | `aria-pressed` |
| 10 | キーボードフォーカス | `:focus-visible` |
| 11 | colors[lv] フォールバック | `colors[lv] \|\| ['#b8b3d6` |
| 12 | カード/Chip role=button | `role="button"` |

各修正の詳細実装は `git log --grep="Phase 1"` で参照。

---

---

## 🤖 自動チェック体制（2026-10-07 導入）

監督に提示する前・commit する前の**ミス検出を自動化**している。CEO が忘れても門が閉まる。

### 1. 機械チェック（自動発火）

```bash
bash scripts/check_before_report.sh
```

| # | 検査内容 | 失敗時 |
|---|---|---|
| 1 | Phase 1 重要修正 12 項目の保持 | ブロック |
| 2 | インライン JavaScript の構文 | ブロック |
| 3 | 現場用語ルール（弾く／伸び上がる／一瞬ためて／下手／タック／椅子に座るように） | ブロック（戒める文脈なら警告のみ） |
| 4 | 技データ `EDITABLE_DATA` の無断改変 | ブロック |
| 5 | 公開先 remote の確認 | ブロック |

**発火タイミング（`.claude/settings.json`）**

- `PostToolUse` … index.html を編集した直後に自動実行。違反があれば編集が差し戻される
- `Stop` … 未検証のまま完了報告しようとすると止まる

技データ（`const skills`）を**監督の明示指示で**変更するときだけ:

```bash
touch .claude/.allow_skills_edit   # 作業が終わったら削除する
```

### 2. 判断チェック（サブエージェント）

機械では測れない逸脱は `roadmap-reviewer` サブエージェントが見る。
**監督に提示する前に必ず Agent ツールで呼ぶこと。**

- 依頼範囲を超えた変更
- 監督の専門領域（技データの文言・前段階・レベル）への踏み込み
- 後方宙返りの腕振り等、技術的な誤り
- 未検証での完了報告
- 公開 URL・起動トリガーの記載漏れ

### 3. ルールを増やすとき

- 文字列で判定できるもの → `scripts/lib/check_wording.py` の `RULES` に追加
- 文脈判断が要るもの → `.claude/agents/roadmap-reviewer.md` に追記

誤検知が出たら必ずルールを精密化する。狼少年になると門が無視される。

## 🚧 触ってはいけない領域

- **技データ本体**（`const skills = [...]`）の中身は **監督の専門領域**。文言・前段階・レベルなどを Claude 判断で書き換えてはならない。表示方法（UI）の改善は OK。
- **公開先リポジトリ** `cheer-tumbling-licence-jp/cta-licence-lp`（既存LP）には絶対に触れない。

---

## 📂 プロジェクト構成

```
/Users/don/cheer_tumbling_app/
├── CLAUDE.md                    # このファイル
├── README.md
├── index.html                   # 本体（自己完結型 HTML）
├── project_boot.sh              # セッション開始スクリプト
├── scripts/
│   ├── sync_from_cowork.sh      # Cowork 新版検出
│   └── check_critical_fixes.sh  # Phase 1 修正の保持確認
├── qr/                          # QR コード（印刷/SNS/アイコン用）
└── .cowork_pending/             # Cowork 新版が検出されたら退避される
```

---

## 🌐 デプロイフロー

**⚠️ 2026-10-12 に公開先が変わった。`git push` だけでは本番は更新されない。**

本番 `roadmap.cheer-tumbling.jp` は **Firebase Hosting** が配信している。
（iOS のホーム画面アプリで Google ログインを通すには authDomain をアプリと
同一オリジンにする必要があり、それには `/__/auth/` を配信できる
Firebase Hosting でなければならないため。GitHub Pages では不可）

```bash
# 編集後、これ1本で GitHub と本番の両方へ
bash scripts/deploy.sh "コミットメッセージ"
```

中でやっていること:
1. `git push origin main`（履歴と旧URL用。GitHub Pages も残してある）
2. `scripts/prepare_hosting.sh` … **git 追跡下のファイルだけ**を `_hosting/` に集める
   Firebase Hosting は `.gitignore` を見ないため、直下をそのまま公開すると
   `backups/`（全利用者のメールを含む）まで出てしまう。必ずこの手順を通す
3. `firebase deploy --only hosting`
4. 本番URLの応答確認

**DNS**: `roadmap` CNAME → `cheer-tumbling-roadmap.web.app`（ムームードメイン）
元に戻す場合は `cheer-tumbling-licence-jp.github.io`

## 🔧 開発サーバー

`.claude/launch.json` 経由で `cheer-tumbling-app` プレビューサーバが起動可能（port 5191）。

```bash
# プレビュー起動
preview_start name="cheer-tumbling-app"
# → http://localhost:5191/
```

---

## 📞 起動トリガー

監督が「**チアタンブリングアプリの続き**」「**ロードマップアプリ**」「**cheer tumbling アプリ**」等と仰ったら、

1. `bash /Users/don/cheer_tumbling_app/project_boot.sh` を実行
2. 警告が出ていればマージから着手
3. 異常なしなら次の作業内容を監督にヒアリング
