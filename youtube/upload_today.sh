#!/bin/bash
# 毎朝 launchd（com.cheernic.yt-upload）から実行されるエントリスクリプト。
#
# パイプライン：
#   1. Drive → manifest 自動登録（auto_register_new_videos.py）
#      未登録動画を VIDEOS リストに自動追加し、video_manifest.json を再生成
#   2. YouTube 一括アップロード（upload_videos.py --limit 6）
#      Drive ストリーミングタイムアウト時は /tmp にステージングして再試行、
#      失敗動画は自動スキップして次へ進む
#
# 監督が Drive に動画を置くだけで、翌朝 YouTube アップロードまで自動で進む。
# 残るアプリ反映（youtubeId 紐付け）は CEO セッション側で実施。

set -u
cd "$(dirname "$0")"

FILTER='FutureWarning|NotOpenSSL|warnings.warn|best-effort|OpenSSL|google-auth past|google-api-core supporting|googleapis.com|/Users/don/Library/Python'

echo "==================== $(date '+%Y-%m-%d %H:%M:%S') 開始 ===================="

echo ""
echo "── 1/2. Drive → manifest 自動登録 ──"
python3 auto_register_new_videos.py 2>&1 | grep -v -E "$FILTER"

echo ""
echo "── 2/2. YouTube アップロード（6本上限） ──"
python3 upload_videos.py --limit 6 2>&1 | grep -v -E "$FILTER"

echo ""
echo "==================== $(date '+%Y-%m-%d %H:%M:%S') 終了 ===================="
