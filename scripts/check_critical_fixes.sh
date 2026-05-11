#!/bin/bash
# Phase 1 で導入した重要修正がローカル版に残っているかチェックする。
# 失われた修正があればリスト表示し、終了コード 1 で警告。

set -uo pipefail

LOCAL_HTML="${1:-$HOME/cheer_tumbling_app/index.html}"

if [ ! -f "$LOCAL_HTML" ]; then
  echo "❌ ファイルが見つかりません: $LOCAL_HTML"
  exit 2
fi

# 検出パターン｜説明  の 2列。grep -F（固定文字列）で検出
declare -a FIXES=(
  'closingScriptRe|エクスポートHTML データ破壊防止'
  '_saveEditsTimer|saveEdits の 400ms デバウンス化'
  "currentSkillFilter !== 'all' && currentSkillFilter !== String(lv)|ツリー表示でレベルフィルタ"
  "addItem.classList.contains('show')|モーダル Esc 多重対応"
  '複製するメニューの名前を入力|複製時の名前入力プロンプト'
  '@media (max-width: 600px)|モバイル対応 @media'
  'role="tablist"|タブの aria-tablist'
  'aria-pressed|chip の aria-pressed'
  ':focus-visible|キーボードフォーカススタイル'
  'colors[lv] || ['"'"'#b8b3d6|colors[lv] フォールバック'
  'role="button"|スキルカード/Chip の role=button'
  'flushSaveEdits|beforeunload で保存フラッシュ'
)

PROBLEMS=0
MISSING_LIST=""
for fix in "${FIXES[@]}"; do
  pattern="${fix%%|*}"
  desc="${fix##*|}"
  # grep -c は 0件マッチで exit 1 を返すため、|| true でエラーを抑制
  if grep -qF "$pattern" "$LOCAL_HTML" 2>/dev/null; then
    : # 検出できた
  else
    MISSING_LIST+="  ❌ $desc"$'\n'
    PROBLEMS=$((PROBLEMS + 1))
  fi
done

if [ "$PROBLEMS" -gt 0 ]; then
  cat <<EOF

❌ CRITICAL_FIXES_MISSING：${PROBLEMS} 件の重要修正が消失しています：

${MISSING_LIST}
  → Claude に「Phase 1 修正を再適用」と依頼してください。
  → 詳細は CLAUDE.md の「Phase 1 重要修正一覧」を参照。

EOF
  exit 1
fi

echo "✅ Phase 1 重要修正は全て保持されています（${#FIXES[@]} 項目すべてOK）"
exit 0
