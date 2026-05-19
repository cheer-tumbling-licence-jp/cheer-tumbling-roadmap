#!/bin/bash
# 毎朝の確認用：YouTube動画の自動アップロード状況と、アプリ（index.html）への
# 反映状況をチェックする。未アップロード・未反映があれば一覧で表示する。
#
# 使い方:
#   bash scripts/check_video_sync.sh          # フル表示（ログ付き）
#   bash scripts/check_video_sync.sh --brief  # 簡易表示（project_boot.sh 用）
#
# 終了コード: 未反映の動画があれば 1、なければ 0

cd "$(dirname "$0")/.." || exit 1

BRIEF=0
[ "${1:-}" = "--brief" ] && BRIEF=1

if [ "$BRIEF" -eq 0 ]; then
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║  🎬 動画アップロード & アプリ反映チェック                    ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo "  $(date '+%Y-%m-%d %H:%M')"
  echo
fi

python3 - <<'PY'
import json, sys

try:
    manifest = json.load(open('youtube/video_manifest.json'))
    uploaded = json.load(open('youtube/uploaded.json'))
    html = open('index.html', encoding='utf-8').read()
except Exception as e:
    print(f"  ❌ ファイル読み込みエラー: {e}")
    sys.exit(1)

total = len(manifest)
up = len(uploaded)

# ── 1. アップロード状況 ──
up_titles = {v['title'] for v in uploaded.values()}
pending = [m['title'].split('｜')[0] for m in manifest if m['title'] not in up_titles]
print(f"  アップロード: {up} / {total} 本", end="")
if pending:
    print(f"  ⏳ 未アップロード {len(pending)} 本: {', '.join(pending)}")
else:
    print("  ✅ 全動画アップロード済み")

# ── 2. アプリ反映状況 ──
# uploaded.json の各動画IDが index.html 内に存在するかで判定
not_reflected = [v for v in uploaded.values() if v['id'] not in html]
if not not_reflected:
    print(f"  アプリ反映  : ✅ アップロード済み {up} 本すべて反映済み")
else:
    print(f"  アプリ反映  : ⚠️  未反映 {len(not_reflected)} 本（index.html に youtubeId 追加が必要）")
    for v in not_reflected:
        print(f"      - {v['title'].split('｜')[0]}  ({v['url']})")

sys.exit(1 if not_reflected else 0)
PY
SYNC_STATUS=$?

if [ "$BRIEF" -eq 0 ]; then
    echo
    echo "── 直近の自動アップロードログ ──"
    if [ -f youtube/launchd.log ]; then
        tail -6 youtube/launchd.log | sed 's/^/  /'
    else
        echo "  （ログなし）"
    fi
    echo
    if [ $SYNC_STATUS -ne 0 ]; then
        echo "👉 未反映の動画があります。index.html の skills / trainings 配列に"
        echo "   youtubeId（または youtubeVariants）を追加してください。"
    else
        echo "✅ アップロード済みの動画はすべてアプリに反映されています。"
    fi
fi

exit $SYNC_STATUS
