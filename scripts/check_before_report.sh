#!/bin/bash
# 監督へ提示する前・commit する前に必ず通す自動チェック（門）。
#
# 使い方:
#   bash scripts/check_before_report.sh
#   ALLOW_SKILLS_EDIT=1 bash scripts/check_before_report.sh   # 技データを監督の明示指示で直したとき
#
# 終了コード: 0 = 通過（.claude/.last_check_ok を更新）/ 1 = 違反あり / 2 = 実行不能

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

TARGET="index.html"
MARKER=".claude/.last_check_ok"
LIB="scripts/lib"
PROBLEMS=0

[ -f "$TARGET" ] || { echo "❌ $TARGET が見つかりません"; exit 2; }

echo "=== 提示前チェック: $TARGET ==="

# ---------------------------------------------------------------- 1
echo
echo "[1/5] Phase 1 重要修正 12 項目"
PHASE1_LOG="$(mktemp)"
if bash scripts/check_critical_fixes.sh "$ROOT/$TARGET" >"$PHASE1_LOG" 2>&1; then
  echo "  ✅ 全項目あり"
else
  echo "  ❌ 失われた修正があります:"
  sed 's/^/    /' "$PHASE1_LOG"
  PROBLEMS=$((PROBLEMS + 1))
fi
rm -f "$PHASE1_LOG"

# ---------------------------------------------------------------- 2
echo
echo "[2/5] インライン JavaScript の構文"
JSDIR="$(mktemp -d)"
JS_COUNT="$(python3 "$LIB/extract_inline_js.py" "$TARGET" "$JSDIR")"
JS_ERR=0
for f in "$JSDIR"/*; do
  [ -e "$f" ] || continue
  if ! ERR="$(node --check "$f" 2>&1)"; then
    echo "  ❌ 構文エラー（$(basename "$f")）:"
    echo "$ERR" | head -5 | sed 's/^/    /'
    JS_ERR=$((JS_ERR + 1))
  fi
done
rm -rf "$JSDIR"
if [ "$JS_ERR" -eq 0 ]; then
  echo "  ✅ ${JS_COUNT} ブロックすべて構文 OK"
else
  PROBLEMS=$((PROBLEMS + JS_ERR))
fi

# ---------------------------------------------------------------- 3
echo
echo "[3/5] 現場用語ルール（著者指定）"
python3 "$LIB/check_wording.py" "$TARGET" || PROBLEMS=$((PROBLEMS + 1))

# ---------------------------------------------------------------- 4
echo
echo "[4/5] 技データ（監督の専門領域）の無断改変"
CUR_H="$(python3 "$LIB/skills_region_hash.py" <"$TARGET")"
HEAD_H="$(git show "HEAD:$TARGET" 2>/dev/null | python3 "$LIB/skills_region_hash.py")"
if [ "$CUR_H" = "NOTFOUND" ]; then
  echo "  ❌ EDITABLE_DATA マーカーが見つかりません（技データ領域が壊れている可能性）"
  PROBLEMS=$((PROBLEMS + 1))
elif [ "$HEAD_H" = "NOTFOUND" ] || [ -z "$HEAD_H" ]; then
  echo "  ⚠️  HEAD 版と比較できませんでした。スキップ"
elif [ "$CUR_H" = "$HEAD_H" ]; then
  echo "  ✅ 変更なし"
elif [ "${ALLOW_SKILLS_EDIT:-0}" = "1" ]; then
  echo "  ⚠️  変更あり — ALLOW_SKILLS_EDIT=1 で明示許可済み"
else
  echo "  ❌ 技データ（const skills）が変更されています。"
  echo "     ここは監督の専門領域。Claude 判断での書き換えは禁止。"
  echo "     監督の明示指示がある場合のみ ALLOW_SKILLS_EDIT=1 を付けて再実行。"
  echo "     差分: git diff HEAD -- $TARGET"
  PROBLEMS=$((PROBLEMS + 1))
fi

# ---------------------------------------------------------------- 5
echo
echo "[5/5] 公開先リポジトリ"
REMOTE="$(git remote get-url origin 2>/dev/null || echo '')"
case "$REMOTE" in
  *cheer-tumbling-roadmap*) echo "  ✅ $REMOTE" ;;
  '') echo "  ⚠️  origin が設定されていません" ;;
  *)  echo "  ❌ 想定外の remote: $REMOTE（cta-licence-lp 等には触れない）"
      PROBLEMS=$((PROBLEMS + 1)) ;;
esac

# ---------------------------------------------------------------- 判定
echo
if [ "$PROBLEMS" -eq 0 ]; then
  mkdir -p .claude
  shasum -a 256 "$TARGET" | awk '{print $1}' >"$MARKER"
  echo "✅ 全チェック通過。提示・commit して差し支えありません。"
  exit 0
else
  rm -f "$MARKER"
  echo "❌ $PROBLEMS 件の違反。直すまで監督への提示・commit は禁止。"
  exit 1
fi
