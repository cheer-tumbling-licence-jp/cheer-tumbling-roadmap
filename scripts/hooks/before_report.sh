#!/bin/bash
# Stop フック: 「未検証のまま完了報告する」のを防ぐ最後の門。
# index.html が最後にチェックを通った状態から変わっていたら、応答を止めて検証させる。
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TARGET="$ROOT/index.html"
MARKER="$ROOT/.claude/.last_check_ok"

PAYLOAD="$(cat)"

# 同じフックで既に止めている場合は無限ループを避けて通す
ACTIVE="$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    print("1" if json.load(sys.stdin).get("stop_hook_active") else "0")
except Exception:
    print("0")
' 2>/dev/null || echo 0)"
[ "$ACTIVE" = "1" ] && exit 0

[ -f "$TARGET" ] || exit 0

# このセッションで index.html を触っていなければ検証不要
if git -C "$ROOT" diff --quiet HEAD -- index.html 2>/dev/null; then
  exit 0
fi

CUR="$(shasum -a 256 "$TARGET" | awk '{print $1}')"
OK="$(cat "$MARKER" 2>/dev/null || echo '')"

[ "$CUR" = "$OK" ] && exit 0

{
  echo "【未検証です】index.html に未検証の変更があります。完了報告はできません。"
  echo
  echo "次を実行し、結果を確認してから報告してください:"
  echo "  bash scripts/check_before_report.sh"
  echo
  echo "さらに、ブラウザでの動作確認（プレビュー起動 → 画面とコンソールの確認）も"
  echo "済んでいない場合は実施してください。「たぶん動く」での報告は禁止です。"
} >&2
exit 2
