# Cheer Tumbling Roadmap アプリ

チアリーディング指導者向けタンブリング練習ロードマップアプリ。
**公開中**：https://roadmap.cheer-tumbling.jp/

---

## 🛠 運営方針（Z案：ここで完結・厳守）

**すべての作業をこのセッションで完結させる**。新機能追加・修正・公開・QA、全部ここ。

- 監督の役割：「こうしたい」を伝えるだけ（経営判断のみ）
- CEO（Claude）の役割：部下エージェントを Agent ツールで編成し、結果を集約して経営報告
- Cowork は**原則使わない**（記憶が引き継げず、過去にヒューマンエラー事故が発生）

### 部下エージェントの編成例

| 役職 | サブエージェント種別 | 使うとき |
|---|---|---|
| CTO | `Plan` | 設計・アーキテクチャ起案 |
| リードエンジニア | `general-purpose` | 実装・修正・公開作業 |
| コードリサーチャー | `Explore` | 既存コードの調査・関数特定 |
| QA テスター | `general-purpose` + プレビューツール | ブラウザ実機テスト |
| セキュリティ監査 | `general-purpose` + `security-review` スキル | 公開前チェック |

複数並列で動かして時間短縮可能（実例：3 エージェント並列の監査）。

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

`git push` するだけで GitHub Pages に自動反映（1〜2分）。

```bash
cd /Users/don/cheer_tumbling_app
# 編集後
git add . && git commit -m "..." && git push
# 反映確認
curl -I https://roadmap.cheer-tumbling.jp/
```

---

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
