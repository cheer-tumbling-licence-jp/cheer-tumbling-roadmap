#!/bin/bash
# Cowork で作業された結果が、ローカル版より新しいか検出する。
# 上書きはしない（人間判断を必須にする）。Claude が報告内容を読んでマージ可否を決める。

set -uo pipefail

COWORK_DIR="$HOME/Library/Application Support/Claude/local-agent-mode-sessions"
APP_DIR="$HOME/cheer_tumbling_app"
LOCAL_HTML="$APP_DIR/index.html"
PENDING_DIR="$APP_DIR/.cowork_pending"

# Cowork セッションディレクトリの中で「直近30日以内に書き換えられた cheer_tumbling_roadmap*.html」を全部探し、
# mtime 降順で最新の1件を取得
LATEST_COWORK=$(find "$COWORK_DIR" \
    -name 'cheer_tumbling_roadmap*.html' \
    -type f \
    -mtime -30 \
    2>/dev/null \
  | xargs -I {} stat -f '%m %N' "{}" 2>/dev/null \
  | sort -rn \
  | head -1 \
  | sed 's/^[0-9]* //')

if [ -z "$LATEST_COWORK" ] || [ ! -f "$LATEST_COWORK" ]; then
  echo "✓ Cowork: 直近30日以内の出力なし（同期不要）"
  exit 0
fi

if [ ! -f "$LOCAL_HTML" ]; then
  echo "❌ ローカル版が存在しません: $LOCAL_HTML"
  exit 2
fi

LOCAL_MTIME=$(stat -f '%m' "$LOCAL_HTML")
COWORK_MTIME=$(stat -f '%m' "$LATEST_COWORK")

# Cowork 側の方が古ければ問題なし
if [ "$COWORK_MTIME" -le "$LOCAL_MTIME" ]; then
  echo "✓ Cowork: ローカル版の方が新しい（同期不要）"
  echo "  Local mtime  : $(date -r "$LOCAL_MTIME" '+%Y-%m-%d %H:%M:%S')"
  echo "  Cowork mtime : $(date -r "$COWORK_MTIME" '+%Y-%m-%d %H:%M:%S')"
  exit 0
fi

# Cowork の方が新しい場合：内容ハッシュも比較（mtime だけでは差分有無が分からない）
LOCAL_HASH=$(shasum -a 256 "$LOCAL_HTML" | cut -d' ' -f1)
COWORK_HASH=$(shasum -a 256 "$LATEST_COWORK" | cut -d' ' -f1)

if [ "$LOCAL_HASH" = "$COWORK_HASH" ]; then
  echo "✓ Cowork: mtime は新しいが内容は同一（同期不要）"
  exit 0
fi

# 差分あり：Pending 領域に退避してアラート
mkdir -p "$PENDING_DIR"
cp "$LATEST_COWORK" "$PENDING_DIR/cowork_latest.html"
echo "$LATEST_COWORK" > "$PENDING_DIR/source_path.txt"
date -r "$COWORK_MTIME" '+%Y-%m-%d %H:%M:%S' > "$PENDING_DIR/cowork_mtime.txt"

LOCAL_SIZE=$(stat -f '%z' "$LOCAL_HTML")
COWORK_SIZE=$(stat -f '%z' "$LATEST_COWORK")
LOCAL_LINES=$(wc -l < "$LOCAL_HTML" | tr -d ' ')
COWORK_LINES=$(wc -l < "$LATEST_COWORK" | tr -d ' ')

cat <<EOF

⚠️  COWORK_NEWER_DETECTED：Cowork に新しい版があります（要マージ）

  Cowork  : $LATEST_COWORK
  Local   : $LOCAL_HTML

  Cowork mtime: $(date -r "$COWORK_MTIME" '+%Y-%m-%d %H:%M:%S')
  Local  mtime: $(date -r "$LOCAL_MTIME" '+%Y-%m-%d %H:%M:%S')

  Cowork  : ${COWORK_LINES} 行 / ${COWORK_SIZE} bytes
  Local   : ${LOCAL_LINES} 行 / ${LOCAL_SIZE} bytes

  → Cowork 版を $PENDING_DIR/cowork_latest.html に退避しました（自動上書きはしません）
  → Claude にマージを依頼してください。Phase 1 重要修正は check_critical_fixes.sh で必ず保護します。

EOF
exit 1
