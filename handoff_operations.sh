#!/bin/bash
# チアタンブリングロードマップ 運用相談用の状況収集スクリプト
# 「アプリ運用相談：〜」トリガー時にアシスタントが自動実行する

cd /Users/don/cheer_tumbling_app 2>/dev/null || {
  echo "❌ /Users/don/cheer_tumbling_app が見つかりません"
  exit 1
}

echo "===================================================="
echo "🎯 チアタンブリング ロードマップ 運用相談モード"
echo "===================================================="
echo ""

echo "📅 現在時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo "🌐 本番 URL: https://roadmap.cheer-tumbling.jp/"
echo ""

echo "── 最新デプロイ ──"
git log -1 --pretty=format:"  %h  %ad  %s%n  by %an" --date=format:"%Y-%m-%d %H:%M" 2>/dev/null
echo ""
echo ""

echo "── 直近 7 日の主な変更（10 件） ──"
git log --since="7 days ago" --pretty=format:"  %h  %ad  %s" --date=format:"%m/%d %H:%M" -n 10 2>/dev/null
echo ""
echo ""

echo "── 未コミットの変更 ──"
CHANGES=$(git status --short 2>/dev/null | head -5)
if [ -z "$CHANGES" ]; then
  echo "  なし（クリーン）"
else
  echo "$CHANGES"
fi
echo ""

echo "── Firebase / Stripe / GitHub リンク ──"
echo "  Stripe Dashboard: https://dashboard.stripe.com/"
echo "  Firebase Console: https://console.firebase.google.com/project/cheer-tumbling-roadmap/"
echo "  GitHub Repo:      https://github.com/cheer-tumbling-licence-jp/cheer-tumbling-roadmap"
echo ""

echo "── OPERATIONS.md 参照 ──"
echo "  詳細な運用手順は /Users/don/cheer_tumbling_app/OPERATIONS.md"
echo ""

echo "===================================================="
echo "✅ 収集完了。監督の相談内容に対応可能な状態です。"
echo "===================================================="
