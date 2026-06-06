#!/bin/bash
# 配布物HTMLからPDFを再生成する
# 使い方: bash scripts/regen_pdfs.sh
#
# マーケティング/{flyer_a4,poster_a3,parent_letter,business_card}.html を
# headless Chrome で PDF に変換して マーケティング/pdf/ に保存。

set -e
cd "$(dirname "$0")/.."

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -x "$CHROME" ]; then
    echo "❌ Google Chrome が見つかりません: $CHROME"
    exit 1
fi

mkdir -p マーケティング/pdf
PWD_ESCAPED="$(pwd)"

for src in flyer_a4 poster_a3 parent_letter business_card; do
    in_path="マーケティング/${src}.html"
    out_path="マーケティング/pdf/${src}.pdf"

    if [ ! -f "$in_path" ]; then
        echo "⚠️  $in_path が見つかりません、スキップ"
        continue
    fi

    "$CHROME" --headless --disable-gpu --no-margins \
        --print-to-pdf-no-header \
        --print-to-pdf="$out_path" \
        "file://$PWD_ESCAPED/$in_path" 2>/dev/null

    if [ -f "$out_path" ]; then
        sz=$(stat -f%z "$out_path" 2>/dev/null || stat -c%s "$out_path")
        echo "✅ $out_path ($(echo $sz | awk '{printf "%.1f KB", $1/1024}'))"
    else
        echo "❌ $out_path 生成失敗"
    fi
done

echo ""
echo "完了 ✨ PDFは マーケティング/pdf/ にあります"
echo "AirDrop / LINE で送る場合：Finder で開いて共有してください"
