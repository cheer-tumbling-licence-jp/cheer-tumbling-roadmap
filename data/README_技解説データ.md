# チアタンブリング技解説データ 引き継ぎ書

## 概要

このJSONファイル(`cheer_tumbling_skills.json`)には、チアタンブリング練習アプリ用の全42技の解説データが含まれています。Claude(チャット側)で作成・統一・検証済みです。

- **総技数**: 42(メイン33技 \+ 応用バリエーション9技)  
- **対象読者**: 練習者(子ども・初心者)、保護者、チームコーチ、学校顧問  
- **言語**: 日本語

## データ構造

{

  "meta": { ... },

  "skills": \[

    {

      "id": "handstand\_forward\_roll",      // 一意のID(英語snake\_case)

      "name": "倒立前転",                    // 日本語表示名

      "name\_en": "Handstand Forward Roll",  // 英語名

      "level": "LEVEL 2 初級",               // レベル分類

      "parent\_id": null,                    // 親技のID(応用バリエーションの場合のみ)

      "description": "...",                 // 概要(80〜115字程度)

      "points": \[                           // ポイント:4項目

        { "title": "...", "detail": "..." }

      \],

      "cautions": \[                         // 注意点:3項目

        { "title": "...", "detail": "..." }

      \],

      "common\_mistakes": \[                  // よくあるミス:4項目

        { "title": "...", "detail": "..." }

      \],

      "progression": \[                      // 段階設定:4項目(易しい→難しい)

        { "title": "...", "detail": "..." }

      \]

    }

  \]

}

## レベル分類

データには以下のレベルが存在します:

- `基礎運動` \- 全ての技の土台となる動き  
- `ウォームアップ` \- 練習前の準備運動  
- `LEVEL 1 基礎` \- タンブリング入門  
- `LEVEL 2 初級` \- 基本回転技  
- `LEVEL 3 中級` \- 連続技・空中技の入門  
- `LEVEL 4 上級` \- 宙返り系  
- `LEVEL 5 上級+` \- ひねり系、最高難度

## 応用バリエーションの扱い

`parent_id` が設定されている技は、親技の応用バリエーションです。

| 親技 | 応用バリエーション |
| :---- | :---- |
| `animal_walks` | `bear_walk`, `one_leg_bear_walk`, `rabbit_hop`, `crab_walk` |
| `shoulder_stand` | `shoulder_stand_front_back_split` |
| `cartwheel` | `one_handed_cartwheel`, `high_cartwheel` |
| `bridge` | `bridge_swing`, `one_leg_bridge` |

アプリ側では「メイン技 → 応用バリエーション」のグループ表示や、親技ページからの遷移が実装できます。

## Code側でやってほしいこと

1. **このJSONファイルを `企画/` または適切な `data/` ディレクトリに配置する**  
2. **アプリ内でこのデータを読み込み、技解説画面に表示する**  
   - 各技ページに `description`、`points`、`cautions`、`common_mistakes`、`progression` を表示  
   - `parent_id` を使って親技から応用バリエーションへのリンクを設置  
   - `level` でフィルタリング・分類できるUIを検討  
3. **データの一貫性を保つため、技の追加・修正は基本的にこのJSONを直接編集する形にする**(コード内にハードコーディングしない)

## 注意事項

- **このJSONの内容は確認済み**: 文字数・項目数・トーンが統一されています。Code側で勝手にリライト・要約・補足を加えないでください。  
- **修正が必要な場合**: 微調整は祐介さん本人が手動で行います。Code側で表現を変更する場合は祐介さんに確認してください。  
- **追加技がある場合**: 同じフォーマット(4-3-4-4項目、50字以内、タイトル:詳細形式)で作成してください。サンプルとして `handstand_forward_roll`(倒立前転)または `back_extension_roll`(後転倒立)を参照してください。

## 品質保証

このデータはClaude(チャット側)で以下のチェック済みです:

- ✅ JSON妥当性  
- ✅ 全42技、メイン33 \+ バリエーション9  
- ✅ 各技に description、points(4)、cautions(3)、common\_mistakes(4)、progression(4)  
- ✅ description文字数:86〜113字  
- ✅ トーン:子ども・初心者にもわかる優しめ  
- ✅ 動作の時系列分解 \+ 成功のメカニズムを含む構造

