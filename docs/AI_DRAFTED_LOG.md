# AI ドラフト記録

このファイルは、Claude（AI）がドラフトしたコンテンツの一覧です。
監督が後から確認・修正できるよう、AIが新規作成した項目を記録します。

データ側にも `aiDrafted: true` フラグを付与しているので、JSコンソールや検索で簡単に絞り込めます。

---

## 2026-06-02 — Word修正コメント適用に伴うトレーニング追加

監督指示：「Q2 → A：私が他のトレーニングに準じた標準的な内容でドラフトして、後で監督が修正」

| id | 名前 | カテゴリ | 場所 | ドラフト内容 | 監督確認 |
|---|---|---|---|---|---|
| `approach-jump` | アプローチジャンプ | jump | `index.html` の `trainings` 配列 | description/points/targetをAIで生成 | ⬜ 未確認 |
| `wrist-stretch` | 手首ストレッチ | flexibility | `index.html` の `trainings` 配列 | description/points/targetをAIで生成 | ⬜ 未確認 |
| `neck-stretch` | 首ストレッチ | flexibility | `index.html` の `trainings` 配列 | description/points/targetをAIで生成 | ⬜ 未確認 |

### 確認方法
1. 各トレーニングは `aiDrafted: true` フィールドを持つ
2. ブラウザのDevToolsで以下を実行：
   ```js
   trainings.filter(t => t.aiDrafted).forEach(t => console.log(t.name, t));
   ```
3. 監督が読んで OK なら、データ側の `aiDrafted: true` を削除＋このログの「監督確認」欄を ✅ に変更

---
