#!/usr/bin/env bash
#
# Firebase Hosting へ上げるファイルだけを _hosting/ に組み立てる。
#
# なぜ「コピーしてから配る」のか
# ──────────────────────────────────────────────────────────────
# Firebase Hosting は .gitignore を見ない。リポジトリ直下をそのまま
# public に指定すると、backups/（全利用者のメールアドレスを含む）や
# 企画・マーケティング資料まで世界に公開してしまう。
#
# そこで「git が追跡しているファイル」だけを明示的に集める。
# このリポジトリは公開リポジトリなので、git 追跡下のファイルは
# すでに GitHub 上で誰でも見られる＝公開範囲は今と一切変わらない。
#
# 使い方:
#   bash scripts/prepare_hosting.sh
#   firebase deploy --only hosting
#
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="_hosting"

# 毎回まっさらに作り直す（消し忘れが残ると古い版が公開され続けるため）
rm -rf "$OUT"
mkdir -p "$OUT"

# git 追跡下のファイルだけをコピー。
# -z と --null で、空白や日本語を含むパスも壊さずに扱う。
COUNT=0
while IFS= read -r -d '' f; do
  mkdir -p "$OUT/$(dirname "$f")"
  cp "$f" "$OUT/$f"
  COUNT=$((COUNT + 1))
done < <(git ls-files -z)

# GitHub Pages 専用のファイルは Firebase では不要
rm -f "$OUT/CNAME"

echo "✅ _hosting/ を作成しました（${COUNT} ファイル）"
echo "   公開範囲は git 追跡下のファイルのみ＝現在 GitHub で公開中のものと同一"

# 事故防止：公開してはいけないものが紛れていないか必ず確かめる
NG=0
for forbidden in backups .env mail.env settings.local.json serviceAccount; do
  if find "$OUT" -name "*${forbidden}*" -print -quit | grep -q .; then
    echo "❌ 公開してはいけないものが含まれています: *${forbidden}*"
    find "$OUT" -name "*${forbidden}*"
    NG=1
  fi
done
if [ "$NG" -ne 0 ]; then
  echo "中止しました。_hosting/ を確認してください。"
  exit 1
fi
echo "   危険なファイルの混入なし"
