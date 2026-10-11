#!/bin/bash
# PostToolUse フック: index.html を編集した直後に自動でチェックを走らせる。
# 違反があれば終了コード 2 で Claude に差し戻す（監督の目に触れる前に止める）。
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# フックへの入力 JSON から編集対象ファイルを取り出す
PAYLOAD="$(cat)"
FILE="$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
ti = d.get("tool_input") or {}
print(ti.get("file_path") or ti.get("path") or "")
' 2>/dev/null || echo '')"

case "$FILE" in
  */index.html) ;;
  *) exit 0 ;;   # index.html 以外の編集は対象外
esac

# 監督が技データ変更を明示承認している場合のみ通す
if [ -f "$ROOT/.claude/.allow_skills_edit" ]; then
  export ALLOW_SKILLS_EDIT=1
fi

OUT="$(bash "$ROOT/scripts/check_before_report.sh" 2>&1)"
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  exit 0
fi

{
  echo "【自動チェックで違反を検出しました】index.html の編集は未完了です。"
  echo
  echo "$OUT"
  echo
  echo "対処してから再度編集してください。監督へこのまま提示・commit してはいけません。"
  echo "技データ(const skills)の変更が監督の明示指示によるものなら、"
  echo "  touch .claude/.allow_skills_edit"
  echo "を実行してから作業を続けてください（作業完了後に削除）。"
} >&2
exit 2
