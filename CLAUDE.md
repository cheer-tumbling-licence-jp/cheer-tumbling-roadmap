# Cheer Tumbling Roadmap アプリ

チアリーディング指導者向けタンブリング練習ロードマップアプリ。
**公開中**：https://cheer-tumbling-licence-jp.github.io/cheer-tumbling-roadmap/

---

## 🛠 役割分担（A案・厳守）

- **Cowork 側** ＝ 新機能の試作・追加（速度優先）
- **このチーム（Claude Code）** ＝ バグ修正・品質保証・公開作業

監督が「Cowork で作業した」と仰った場合、または最終更新がローカル版より新しい場合は、**必ず以下の手順**を踏むこと。

---

## 📋 セッション開始時の必須手順

1. `bash project_boot.sh` を実行
   - `sync_from_cowork.sh` が Cowork の新版を検出
   - `check_critical_fixes.sh` が Phase 1 重要修正の保持を検証
2. 警告が出ていたら **作業に入る前に必ずマージを実行**
3. マージ後、`scripts/check_critical_fixes.sh` を再実行して全項目 OK を確認

### マージ手順（COWORK_NEWER_DETECTED が出た場合）

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
curl -I https://cheer-tumbling-licence-jp.github.io/cheer-tumbling-roadmap/
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
