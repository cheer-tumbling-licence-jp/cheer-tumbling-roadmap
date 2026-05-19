#!/bin/bash
# Cheer Tumbling Roadmap アプリ プロジェクト起動
# セッション開始時に Claude が読み込むコンテキストを生成する。
# - Cowork 同期チェック
# - 重要修正の保持確認
# - Git 状態
# - 公開URL

set -uo pipefail

APP_DIR="$HOME/cheer_tumbling_app"
SCRIPTS_DIR="$APP_DIR/scripts"

cat <<'HEAD'
╔══════════════════════════════════════════════════════════════╗
║  🎀 Cheer Tumbling Roadmap アプリ プロジェクト起動           ║
╚══════════════════════════════════════════════════════════════╝
HEAD

echo ""
echo "📂 ディレクトリ: $APP_DIR"
echo ""

# 1. Cowork 同期チェック
echo "── 1. Cowork 同期チェック ──"
bash "$SCRIPTS_DIR/sync_from_cowork.sh"
SYNC_STATUS=$?

echo ""
# 2. 重要修正の保持確認
echo "── 2. Phase 1 重要修正の保持確認 ──"
bash "$SCRIPTS_DIR/check_critical_fixes.sh"
FIXES_STATUS=$?

echo ""
# 3. Git 状態
echo "── 3. Git 状態 ──"
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR"
  echo "  ブランチ      : $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  echo "  最新コミット  : $(git log -1 --pretty=format:'%h %s' 2>/dev/null)"
  AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
  BEHIND=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)
  echo "  リモートとの差: 先行 $AHEAD コミット / 遅れ $BEHIND コミット"
  UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "  未コミット変更: $UNCOMMITTED ファイル"
else
  echo "  ⚠️ Git リポジトリではありません"
fi

echo ""
# 4. 動画アップロード & アプリ反映チェック
echo "── 4. 動画アップロード & アプリ反映チェック ──"
bash "$SCRIPTS_DIR/check_video_sync.sh" --brief
VIDEO_STATUS=$?

echo ""
# 5. 公開URL
echo "── 5. 公開サイト ──"
echo "  🌐 https://cheer-tumbling-licence-jp.github.io/cheer-tumbling-roadmap/"
echo "  📦 https://github.com/cheer-tumbling-licence-jp/cheer-tumbling-roadmap"

echo ""
# 6. アクションアイテム
if [ "$SYNC_STATUS" -ne 0 ] || [ "$FIXES_STATUS" -ne 0 ] || [ "$VIDEO_STATUS" -ne 0 ]; then
  cat <<EOF
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  要対応：上記のアラートを Claude に伝えてください       ║
╚══════════════════════════════════════════════════════════════╝
EOF
else
  cat <<EOF
╔══════════════════════════════════════════════════════════════╗
║  ✅ 異常なし：そのまま作業を継続できます                     ║
╚══════════════════════════════════════════════════════════════╝
EOF
fi
