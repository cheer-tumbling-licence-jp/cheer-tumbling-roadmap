#!/bin/bash
# 印刷物（A4/A3）が1ページに収まっているかチェックするスクリプト
# Chrome headless で各印刷物をピクセル単位で正確なページサイズで撮影し、
# /tmp/print_check/ に PNG として保存する。目視確認用。
#
# 使い方：
#   bash scripts/check_print_layouts.sh
#   open /tmp/print_check/  # Finder で開いて全部確認

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_DIR="/tmp/print_check"

if [ ! -x "$CHROME" ]; then
  echo "❌ Chrome が見つかりません: $CHROME"
  exit 1
fi

mkdir -p "$OUT_DIR"

# A4 = 210×297mm @ 96dpi → 794×1123 px
# A3 = 297×420mm @ 96dpi → 1123×1587 px

shoot() {
  local file="$1"
  local size="$2"
  local label="$3"
  local out="$OUT_DIR/$(basename "${file%.html}").png"
  echo "  📸 $label ..."
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --window-size="$size" \
    --virtual-time-budget=3000 \
    --screenshot="$out" \
    "file://$PROJECT_ROOT/$file" 2>/dev/null
  if [ -f "$out" ]; then
    echo "     ✅ $out"
  else
    echo "     ❌ 撮影失敗"
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  印刷物レイアウトチェック（1ページに収まるか）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

shoot "マーケティング/flyer_a4.html"      "794,1123"  "A4 配布チラシ"
shoot "マーケティング/poster_a3.html"     "1123,1587" "A3 教室掲示ポスター"
shoot "マーケティング/business_card.html" "794,1123"  "名刺カード（10枚/A4）"
shoot "マーケティング/parent_letter.html" "794,1123"  "保護者向け配布レター"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  💡 確認方法："
echo "     open $OUT_DIR/"
echo "     → Finder で開いて、各PNGを順に見る"
echo "     → コンテンツが下端まで収まっていれば OK"
echo "     → 途中で切れていたら該当HTMLの sheet { height: ... }"
echo "        と内部のフォントサイズ・余白を縮小して再実行"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
