#!/usr/bin/env bash
#
# 公開（デプロイ）
#
# ⚠️ 2026-10-12 に公開先が変わった。git push だけでは本番は更新されない。
#    本番 roadmap.cheer-tumbling.jp は Firebase Hosting が配信している。
#    （Google ログインのために authDomain をアプリと同一オリジンにする必要があり、
#      それには Firebase Hosting でないと /__/auth/ が配信できないため）
#
#    GitHub Pages も残してあるが、独自ドメインは Firebase を向いている。
#
# 使い方:
#   bash scripts/deploy.sh "コミットメッセージ"
#   bash scripts/deploy.sh            # コミット済みのものを公開するだけ
#
set -euo pipefail
cd "$(dirname "$0")/.."

MSG="${1:-}"

if [ -n "$MSG" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "$MSG"
  else
    echo "（変更なし。コミットは省略）"
  fi
fi

# 1) GitHub へ（履歴・旧URL用）
git push origin main

# 2) 本番へ（Firebase Hosting）
bash scripts/prepare_hosting.sh
firebase deploy --only hosting

echo
echo "── 反映確認 ──"
for i in $(seq 1 20); do
  if curl -s -m 15 -o /dev/null -w "%{http_code}" "https://roadmap.cheer-tumbling.jp/?cb=$(date +%s)" | grep -q 200; then
    echo "✅ https://roadmap.cheer-tumbling.jp/ が応答しています"
    break
  fi
  sleep 5
done
